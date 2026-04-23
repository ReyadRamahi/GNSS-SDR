"""
map_aid.py
3-D map-aided GNSS: predicts LOS/NLOS satellite visibility using
OpenStreetMap building footprints fetched from the Overpass API.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Optional

import urllib.parse

import numpy as np
import requests
from shapely.geometry import LineString, Point, Polygon

log = logging.getLogger(__name__)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
DEFAULT_FLOOR_HEIGHT_M = 3.5

_EL_CUTOFF_LOW  = 5.0   # always NLOS regardless of buildings
_EL_CUTOFF_HIGH = 75.0  # always LOS — buildings rarely block this high
_RAY_LENGTH_M   = 800.0 # horizontal ray extent for intersection checks
_SAT_DIST_M     = 20_000_000.0  # plane-wave approximation source distance

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

Point2D   = tuple[float, float]
Segment2D = tuple[Point2D, Point2D]


# ---------------------------------------------------------------------------
# Specular multipath result
# ---------------------------------------------------------------------------

@dataclass
class ReflectionResult:
    building_idx: int
    wall_start: Point2D
    wall_end: Point2D
    reflection_point: Point2D   # ENU metres (x east, y north)
    extra_path_m: float         # pseudorange error estimate


# ---------------------------------------------------------------------------
# Specular geometry helpers
# ---------------------------------------------------------------------------

def get_wall_segments(polygon: Polygon) -> list[Segment2D]:
    """Return exterior wall segments as (start, end) pairs, skipping degenerate edges."""
    coords = list(polygon.exterior.coords)
    segments: list[Segment2D] = []
    for i in range(len(coords) - 1):
        dx = coords[i + 1][0] - coords[i][0]
        dy = coords[i + 1][1] - coords[i][1]
        if math.hypot(dx, dy) == 0.0:
            continue
        segments.append(
            ((coords[i][0], coords[i][1]), (coords[i + 1][0], coords[i + 1][1]))
        )
    return segments


def wall_normal_2d(
    wall_start: Point2D,
    wall_end: Point2D,
    centroid: Point2D,
) -> np.ndarray:
    """Return the 2-D unit outward normal for a wall segment (away from centroid)."""
    dx = wall_end[0] - wall_start[0]
    dy = wall_end[1] - wall_start[1]
    length = math.hypot(dx, dy)
    if length == 0.0:
        return np.array([0.0, 0.0])
    n1 = np.array([-dy / length,  dx / length])
    n2 = np.array([ dy / length, -dx / length])
    mx = (wall_start[0] + wall_end[0]) / 2.0
    my = (wall_start[1] + wall_end[1]) / 2.0
    to_centroid = np.array([centroid[0] - mx, centroid[1] - my])
    return n1 if np.dot(n1, to_centroid) < 0.0 else n2


def mirror_point_across_line(
    point: Point2D,
    line_start: Point2D,
    line_end: Point2D,
) -> Point2D:
    """Reflect point across the infinite line through line_start and line_end."""
    px = point[0] - line_start[0]
    py = point[1] - line_start[1]
    dx = line_end[0] - line_start[0]
    dy = line_end[1] - line_start[1]
    length_sq = dx * dx + dy * dy
    if length_sq == 0.0:
        return point
    dot = px * dx + py * dy
    fx = line_start[0] + dot * dx / length_sq
    fy = line_start[1] + dot * dy / length_sq
    return (2.0 * fx - point[0], 2.0 * fy - point[1])


def segment_intersection(
    p1: Point2D,
    p2: Point2D,
    p3: Point2D,
    p4: Point2D,
) -> Point2D | None:
    """
    Intersection of segment p1-p2 with segment p3-p4.
    Returns the intersection point or None if parallel / outside segment bounds.
    """
    d1x, d1y = p2[0] - p1[0], p2[1] - p1[1]
    d2x, d2y = p4[0] - p3[0], p4[1] - p3[1]
    denom = d1x * d2y - d1y * d2x
    eps = 1e-9 * (abs(d1x) + abs(d1y) + abs(d2x) + abs(d2y))
    if abs(denom) < eps:
        return None  # parallel or near-parallel
    dx = p3[0] - p1[0]
    dy = p3[1] - p1[1]
    t = (dx * d2y - dy * d2x) / denom
    u = (dx * d1y - dy * d1x) / denom
    if 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0:
        return (p1[0] + t * d1x, p1[1] + t * d1y)
    return None


def path_clear(
    start_enu: Point2D,
    end_enu: Point2D,
    buildings: list[dict],
    exclude_idx: int,
) -> bool:
    """Return True if the straight line from start to end does not cross through any building."""
    line = LineString([start_enu, end_enu])
    for idx, bld in enumerate(buildings):
        if idx == exclude_idx:
            continue
        if line.crosses(bld["polygon"]) or line.within(bld["polygon"]):
            return False
    return True


def is_valid_reflection(
    tx_pos: Point2D,
    reflection_point: Point2D,
    wall_start: Point2D,
    wall_end: Point2D,
    centroid: Point2D,
) -> bool:
    """Return True if the signal approaches the wall from the front (outward-facing) side."""
    normal = wall_normal_2d(wall_start, wall_end, centroid)
    incident = np.array([reflection_point[0] - tx_pos[0], reflection_point[1] - tx_pos[1]])
    return bool(np.dot(incident, normal) < 0.0)


def compute_extra_path_length(
    tx: Point2D,
    rx: Point2D,
    reflection: Point2D,
) -> float:
    """Return the extra path length (metres) of a reflected route vs the direct path."""
    return float(
        np.linalg.norm(np.array(tx) - np.array(reflection))
        + np.linalg.norm(np.array(reflection) - np.array(rx))
        - np.linalg.norm(np.array(tx) - np.array(rx))
    )


def reflection_in_front_of_receiver(
    reflection_point: Point2D,
    sat_horizontal_dir: Point2D,
) -> bool:
    """
    Return True if the reflection point is on the same side as the satellite
    relative to the receiver (ENU origin).  Prevents reflections that would
    require the signal to pass through the receiver or the ground.
    """
    rx_vec  = np.array(reflection_point)
    sat_dir = np.array(sat_horizontal_dir)
    return bool(np.dot(rx_vec, sat_dir) > 0.0)


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

    def find_specular_reflections(
        self,
        elevation_deg: float,
        azimuth_deg: float,
        max_reflection_dist_m: float = 300.0,
    ) -> list[ReflectionResult]:
        """
        Find all specular reflection paths from satellite → building wall → receiver.

        Uses the plane-wave approximation: the satellite source point is placed
        _SAT_DIST_M metres in the satellite's horizontal direction from the receiver.
        The receiver sits at the ENU origin (0, 0).

        For each wall of each building within max_reflection_dist_m:
          1. Skip walls facing away from the satellite (outward normal dot check).
          2. Intersect the satellite ray with the wall segment.
          3. Verify the reflection is physically valid (incident-side check).
          4. Verify the reflection point is in front of the receiver.
          5. Verify the reflected path (wall → receiver) is unobstructed.
          6. Compute and record the extra path length.
        """
        az_rad = math.radians(azimuth_deg)
        el_rad = math.radians(elevation_deg)
        cos_el = math.cos(el_rad)
        sin_el = math.sin(el_rad)
        sat_dir_h: Point2D = (math.sin(az_rad), math.cos(az_rad))

        # 2-D satellite source used for wall intersection geometry
        tx: Point2D  = (sat_dir_h[0] * _SAT_DIST_M, sat_dir_h[1] * _SAT_DIST_M)
        rx: Point2D  = (0.0, 0.0)
        # Far end of the incoming ray (direction from satellite toward receiver)
        ray_end: Point2D = (-sat_dir_h[0] * _RAY_LENGTH_M, -sat_dir_h[1] * _RAY_LENGTH_M)

        # 3-D satellite source: horizontal components scaled by cos(el), vertical by sin(el).
        # Used only for extra_path_m so the result is non-zero even when tx, P, rx are
        # 2-D collinear (e.g. satellite directly behind the reflecting wall).
        tx_3d = np.array([sat_dir_h[0] * cos_el * _SAT_DIST_M,
                           sat_dir_h[1] * cos_el * _SAT_DIST_M,
                           sin_el * _SAT_DIST_M])

        results: list[ReflectionResult] = []

        for idx, bld in enumerate(self._buildings):
            poly: Polygon = bld["polygon"]

            # Skip buildings whose boundary is farther than the search radius
            if poly.exterior.distance(Point(0.0, 0.0)) > max_reflection_dist_m:
                continue

            cx, cy = poly.centroid.x, poly.centroid.y
            centroid: Point2D = (cx, cy)

            for ws, we in get_wall_segments(poly):
                # 1. Skip walls facing away from the satellite (dot < 0 → facing away)
                normal = wall_normal_2d(ws, we, centroid)
                if np.dot(normal, np.array(sat_dir_h)) < 0.0:
                    continue

                # 2. Intersect the incoming ray with this wall segment
                pt = segment_intersection(tx, ray_end, ws, we)
                if pt is None:
                    continue

                # 3. Physical validity: signal must approach from the outward side
                if not is_valid_reflection(tx, pt, ws, we, centroid):
                    continue

                # 4. Reflection point must be on the same side as the satellite
                if not reflection_in_front_of_receiver(pt, sat_dir_h):
                    continue

                # 5. Reflected path from wall point back to receiver must be clear
                if not path_clear(pt, rx, self._buildings, exclude_idx=idx):
                    continue

                # 6. Record the valid reflection — use 3-D tx to get non-zero extra path
                #    even when tx, pt, rx are 2-D collinear (plane-wave / normal-incidence).
                P_3d  = np.array([pt[0], pt[1], 0.0])
                rx_3d = np.zeros(3)
                extra = float(
                    np.linalg.norm(tx_3d - P_3d)
                    + np.linalg.norm(P_3d - rx_3d)
                    - np.linalg.norm(tx_3d - rx_3d)
                )
                results.append(ReflectionResult(
                    building_idx=idx,
                    wall_start=ws,
                    wall_end=we,
                    reflection_point=pt,
                    extra_path_m=extra,
                ))

        return results

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

            # Specular multipath — only meaningful for satellites that are LOS
            if blocked_by is None and el is not None and az is not None:
                reflections = self.find_specular_reflections(el, az)
                sat["has_reflection"]     = len(reflections) > 0
                sat["reflection_delay_m"] = max(
                    (r.extra_path_m for r in reflections), default=0.0
                )
                sat["reflection_count"]   = len(reflections)
            else:
                sat["has_reflection"]     = False
                sat["reflection_delay_m"] = 0.0
                sat["reflection_count"]   = 0

            result.append(sat)

        return result
