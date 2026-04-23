"""
map_aid.py
3-D map-aided GNSS: predicts LOS/NLOS satellite visibility using
OpenStreetMap building footprints fetched from the Overpass API.
"""
from __future__ import annotations

import logging
import math
from typing import Optional

import urllib.parse

import requests
from shapely.geometry import LineString, Point, Polygon

log = logging.getLogger(__name__)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
DEFAULT_FLOOR_HEIGHT_M = 3.5

_EL_CUTOFF_LOW  = 5.0   # always NLOS regardless of buildings
_EL_CUTOFF_HIGH = 75.0  # always LOS — buildings rarely block this high
_RAY_LENGTH_M   = 800.0 # horizontal ray extent for intersection checks


# ---------------------------------------------------------------------------
# Public helpers (also imported by test_map_aid)
# ---------------------------------------------------------------------------

def _estimate_height(tags: dict) -> float:
    if "height" in tags:
        try:
            return float(tags["height"].split()[0])
        except Exception:
            pass
    if "building:levels" in tags:
        try:
            return float(tags["building:levels"]) * DEFAULT_FLOOR_HEIGHT_M
        except Exception:
            pass
    return 10.0


def _latlon_to_enu(lat: float, lon: float, ref_lat: float, ref_lon: float) -> tuple[float, float]:
    """Flat-earth approximation, accurate to <1% within 10 km."""
    d_lat = math.radians(lat - ref_lat)
    d_lon = math.radians(lon - ref_lon)
    ref_lat_r = math.radians(ref_lat)
    north = d_lat * 6_371_000
    east  = d_lon * 6_371_000 * math.cos(ref_lat_r)
    return east, north


# ---------------------------------------------------------------------------
# Internal building footprint loader
# ---------------------------------------------------------------------------

def _parse_buildings(elements: list[dict], ref_lat: float, ref_lon: float) -> list[dict]:
    """Convert OSM elements into local ENU Polygon + height dicts."""
    buildings: list[dict] = []

    for el in elements:
        tags   = el.get("tags", {})
        height = _estimate_height(tags)
        el_type = el.get("type")

        if el_type == "way":
            geom = el.get("geometry", [])
            _append_polygon(geom, height, ref_lat, ref_lon, buildings)

        elif el_type == "relation":
            for member in el.get("members", []):
                if member.get("role") == "outer" and member.get("type") == "way":
                    _append_polygon(
                        member.get("geometry", []), height, ref_lat, ref_lon, buildings
                    )

    return buildings


def _append_polygon(
    geom: list[dict],
    height: float,
    ref_lat: float,
    ref_lon: float,
    out: list[dict],
) -> None:
    if len(geom) < 3:
        return
    coords = [_latlon_to_enu(n["lat"], n["lon"], ref_lat, ref_lon) for n in geom]
    try:
        poly = Polygon(coords)
        if not poly.is_valid:
            poly = poly.buffer(0)  # repair self-intersections
        if not poly.is_empty:
            out.append({"polygon": poly, "height": height})
    except Exception:
        pass


# ---------------------------------------------------------------------------
# BuildingMask
# ---------------------------------------------------------------------------

class BuildingMask:
    def __init__(self, lat: float, lon: float, radius_m: int = 400):
        """
        Fetches buildings within radius_m metres of (lat, lon) from the
        OpenStreetMap Overpass API.  Converts building footprints to local
        ENU coordinates (metres from receiver position).
        Caches the result — only fetches once per instance.
        """
        self._lat       = lat
        self._lon       = lon
        self._buildings: list[dict] = []
        self._available = True

        query = (
            "[out:json];\n"
            "(\n"
            f'  way["building"](around:{radius_m},{lat},{lon});\n'
            f'  relation["building"](around:{radius_m},{lat},{lon});\n'
            ");\n"
            "out body geom;\n"
        )
        try:
            # Use quote (not quote_plus) so spaces encode as %20 — Overpass rejects + encoding.
            # Explicit User-Agent required: Overpass blocks the default python-requests UA.
            body = ("data=" + urllib.parse.quote(query)).encode()
            resp = requests.post(
                OVERPASS_URL,
                data=body,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "User-Agent": "gnss-sdr-dashboard/1.0",
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            self._buildings = _parse_buildings(data.get("elements", []), lat, lon)
            log.info("[map_aid] Loaded %d building footprints", len(self._buildings))
        except Exception as exc:
            log.warning("[map_aid] Overpass API unavailable: %s", exc)
            self._available = False

    @property
    def building_count(self) -> int:
        return len(self._buildings)

    def classify_satellites(self, satellites: list[dict]) -> list[dict]:
        """
        Input:  list of dicts with keys: prn, elevation_deg, azimuth_deg
        Output: same list with three new keys added per satellite:
                  predicted_los        (bool)
                  blocking_building    (int index or None)
                  nlos_note            (str)
        """
        result: list[dict] = []

        for sat in satellites:
            sat = dict(sat)  # shallow copy — don't mutate caller's data

            if not self._available:
                sat["predicted_los"]     = True
                sat["blocking_building"] = None
                sat["nlos_note"]         = "building data unavailable"
                result.append(sat)
                continue

            el: Optional[float] = sat.get("elevation_deg")
            az: Optional[float] = sat.get("azimuth_deg")

            if el is None or az is None:
                sat["predicted_los"]     = True
                sat["blocking_building"] = None
                sat["nlos_note"]         = "no elevation/azimuth data"
                result.append(sat)
                continue

            if el < _EL_CUTOFF_LOW:
                sat["predicted_los"]     = False
                sat["blocking_building"] = None
                sat["nlos_note"]         = (
                    f"below minimum elevation ({el:.1f}° < {_EL_CUTOFF_LOW}°)"
                )
                result.append(sat)
                continue

            if el > _EL_CUTOFF_HIGH:
                sat["predicted_los"]     = True
                sat["blocking_building"] = None
                sat["nlos_note"]         = ""
                result.append(sat)
                continue

            # Ray-trace in the horizontal ENU plane.
            # Build a ray from (0, 0) toward the satellite azimuth.
            az_rad = math.radians(az)
            dx = math.sin(az_rad) * _RAY_LENGTH_M   # east component
            dy = math.cos(az_rad) * _RAY_LENGTH_M   # north component
            ray = LineString([(0.0, 0.0), (dx, dy)])

            blocked_by: Optional[int] = None

            for idx, bld in enumerate(self._buildings):
                poly: Polygon = bld["polygon"]
                h: float      = bld["height"]

                # Check if receiver is inside the building
                if poly.contains(Point(0.0, 0.0)):
                    blocked_by = idx
                    break

                inter = ray.intersection(poly.boundary)
                if inter.is_empty:
                    continue

                # Collect intersection points
                if inter.geom_type == "Point":
                    pts = [inter]
                elif inter.geom_type == "MultiPoint":
                    pts = list(inter.geoms)
                else:
                    # LineString / GeometryCollection — use centroid
                    pts = [inter.centroid]

                for pt in pts:
                    d_horiz = math.hypot(pt.x, pt.y)
                    if d_horiz < 0.5:
                        continue  # numerical noise near origin
                    # Elevation angle needed to clear the building at this distance
                    el_needed = math.degrees(math.atan2(h, d_horiz))
                    if el < el_needed:
                        blocked_by = idx
                        break

                if blocked_by is not None:
                    break

            sat["predicted_los"]     = blocked_by is None
            sat["blocking_building"] = blocked_by
            sat["nlos_note"]         = (
                f"blocked by building {blocked_by}" if blocked_by is not None else ""
            )
            result.append(sat)

        return result
