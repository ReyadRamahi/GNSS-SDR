"""
test_map_aid.py
pytest suite for map_aid.BuildingMask — no internet required.
All Overpass API calls are mocked.
"""
from __future__ import annotations

import math
from unittest.mock import MagicMock, patch

import pytest

import numpy as np
from shapely.geometry import Polygon

from map_aid import (
    DEFAULT_FLOOR_HEIGHT_M,
    BuildingMask,
    _estimate_height,
    _latlon_to_enu,
    get_wall_segments,
    mirror_point_across_line,
    wall_normal_2d,
)

# Reference receiver position (Chicago area)
REF_LAT, REF_LON = 41.878, -87.629


# ---------------------------------------------------------------------------
# Helper utilities
# ---------------------------------------------------------------------------

def _enu_building(north_m: float, width_m: float = 20.0, height_str: str = "30") -> dict:
    """
    Build a fake Overpass element representing a square building centred
    at (east=0, north=north_m) in ENU metres, converted back to lat/lon so
    the BuildingMask constructor's _parse_buildings path can reconstruct it.
    """
    lat_per_m = 1.0 / 111_000
    cos_lat   = math.cos(math.radians(REF_LAT))
    lon_per_m = 1.0 / (111_000 * cos_lat)
    hw        = width_m / 2

    corners_enu = [
        (-hw, north_m - hw),
        ( hw, north_m - hw),
        ( hw, north_m + hw),
        (-hw, north_m + hw),
        (-hw, north_m - hw),  # closed ring
    ]
    nodes = [
        {"lat": REF_LAT + n * lat_per_m, "lon": REF_LON + e * lon_per_m}
        for e, n in corners_enu
    ]
    return {
        "type": "way",
        "tags": {"building": "yes", "height": height_str},
        "geometry": nodes,
    }


def _mask_with(north_m: float, width_m: float = 20.0, height_str: str = "30") -> BuildingMask:
    """Return a BuildingMask with one synthetic building, no network call."""
    fake_resp = MagicMock()
    fake_resp.raise_for_status = MagicMock()
    fake_resp.json.return_value = {
        "elements": [_enu_building(north_m, width_m, height_str)]
    }
    with patch("map_aid.requests.post", return_value=fake_resp):
        return BuildingMask(REF_LAT, REF_LON)


# ---------------------------------------------------------------------------
# _latlon_to_enu
# ---------------------------------------------------------------------------

def test_latlon_to_enu_north():
    """1 degree north ≈ 111 000 m; east offset should be near zero."""
    east, north = _latlon_to_enu(42.0, -87.629, 41.0, -87.629)
    assert abs(east) < 1.0
    assert abs(north - 111_000) / 111_000 < 0.01


def test_latlon_to_enu_east():
    """1 degree east at REF_LAT should scale by cos(lat)."""
    east, north = _latlon_to_enu(41.878, -86.629, 41.878, -87.629)
    expected = math.radians(1.0) * 6_371_000 * math.cos(math.radians(41.878))
    assert abs(north) < 1.0
    assert abs(east - expected) / expected < 0.01


# ---------------------------------------------------------------------------
# _estimate_height
# ---------------------------------------------------------------------------

def test_height_explicit():
    assert _estimate_height({"height": "15 m"}) == 15.0


def test_height_levels():
    assert _estimate_height({"building:levels": "4"}) == pytest.approx(
        4 * DEFAULT_FLOOR_HEIGHT_M
    )


def test_height_default():
    assert _estimate_height({}) == 10.0


# ---------------------------------------------------------------------------
# High-elevation satellite: always LOS
# ---------------------------------------------------------------------------

def test_high_elevation_always_los():
    mask = _mask_with(north_m=50)
    result = mask.classify_satellites(
        [{"prn": 1, "elevation_deg": 80.0, "azimuth_deg": 0.0, "cn0": 40.0}]
    )
    assert result[0]["predicted_los"] is True
    assert result[0]["blocking_building"] is None


# ---------------------------------------------------------------------------
# Below-horizon satellite: always NLOS
# ---------------------------------------------------------------------------

def test_below_horizon_always_nlos():
    mask = _mask_with(north_m=50)
    result = mask.classify_satellites(
        [{"prn": 2, "elevation_deg": 3.0, "azimuth_deg": 0.0, "cn0": 28.0}]
    )
    assert result[0]["predicted_los"] is False


# ---------------------------------------------------------------------------
# Blocked by tall building
# ---------------------------------------------------------------------------

def test_blocked_by_tall_building_north():
    """30 m building 50 m due north; az=0 el=10 → blocked."""
    # el_needed = atan(30/50) ≈ 31° — satellite at 10° is well below that
    mask = _mask_with(north_m=50, height_str="30")
    result = mask.classify_satellites(
        [{"prn": 3, "elevation_deg": 10.0, "azimuth_deg": 0.0, "cn0": 35.0}]
    )
    assert result[0]["predicted_los"] is False
    assert result[0]["blocking_building"] is not None


def test_not_blocked_opposite_direction():
    """Same building is north; satellite az=180 el=10 looks south → not blocked."""
    mask = _mask_with(north_m=50, height_str="30")
    result = mask.classify_satellites(
        [{"prn": 4, "elevation_deg": 10.0, "azimuth_deg": 180.0, "cn0": 35.0}]
    )
    assert result[0]["predicted_los"] is True


# ---------------------------------------------------------------------------
# Short building: satellite clears it
# ---------------------------------------------------------------------------

def test_passes_over_short_building():
    """5 m building 50 m north; el=30 clears it (el_needed ≈ 5.7°)."""
    mask = _mask_with(north_m=50, height_str="5")
    result = mask.classify_satellites(
        [{"prn": 5, "elevation_deg": 30.0, "azimuth_deg": 0.0, "cn0": 42.0}]
    )
    assert result[0]["predicted_los"] is True


# ---------------------------------------------------------------------------
# Overpass API unavailable
# ---------------------------------------------------------------------------

def test_overpass_unavailable():
    """ConnectionError → all satellites LOS with 'building data unavailable' note."""
    with patch("map_aid.requests.post", side_effect=ConnectionError("timeout")):
        mask = BuildingMask(REF_LAT, REF_LON)

    sats = [
        {"prn": 1, "elevation_deg": 20.0, "azimuth_deg": 45.0, "cn0": 38.0},
        {"prn": 2, "elevation_deg": 35.0, "azimuth_deg": 90.0, "cn0": 42.0},
    ]
    result = mask.classify_satellites(sats)
    for sat in result:
        assert sat["predicted_los"] is True
        assert "building data unavailable" in sat["nlos_note"]


# ---------------------------------------------------------------------------
# Specular multipath helper unit tests
# ---------------------------------------------------------------------------

def test_mirror_point_across_line_xaxis():
    """Mirror (0, 1) across the x-axis → (0, -1)."""
    pt = mirror_point_across_line((0.0, 1.0), (0.0, 0.0), (1.0, 0.0))
    assert abs(pt[0] - 0.0) < 1e-9
    assert abs(pt[1] - (-1.0)) < 1e-9


def test_mirror_point_across_line_vertical():
    """Mirror (3, 0) across the line x=1 → (-1, 0)."""
    # Line x=1 passes through (1,0) and (1,1)
    pt = mirror_point_across_line((3.0, 0.0), (1.0, 0.0), (1.0, 1.0))
    assert abs(pt[0] - (-1.0)) < 1e-9
    assert abs(pt[1] - 0.0) < 1e-9


def test_wall_normal_outward():
    """Wall normals for a unit square must all point away from the centroid."""
    # Unit square centred at origin
    sq = Polygon([(-1, -1), (1, -1), (1, 1), (-1, 1), (-1, -1)])
    cx, cy = sq.centroid.x, sq.centroid.y
    centroid = (cx, cy)

    for ws, we in get_wall_segments(sq):
        normal = wall_normal_2d(ws, we, centroid)
        mx = (ws[0] + we[0]) / 2.0
        my = (ws[1] + we[1]) / 2.0
        # Normal must point away from centroid
        to_centroid = np.array([cx - mx, cy - my])
        assert np.dot(normal, to_centroid) <= 0.0, (
            f"Normal {normal} points toward centroid for wall {ws}-{we}"
        )


def _mask_east(east_start: float = 50.0, width: float = 20.0) -> BuildingMask:
    """
    BuildingMask with one 30 m building placed east of receiver.
    Building spans x=[east_start, east_start+width], y=[-10, 10].
    """
    lat_per_m = 1.0 / 111_000
    cos_lat   = math.cos(math.radians(REF_LAT))
    lon_per_m = 1.0 / (111_000 * cos_lat)

    x0, x1 = east_start, east_start + width
    y0, y1 = -10.0, 10.0
    corners_enu = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
    nodes = [
        {"lat": REF_LAT + n * lat_per_m, "lon": REF_LON + e * lon_per_m}
        for e, n in corners_enu
    ]
    element = {
        "type": "way",
        "tags": {"building": "yes", "height": "30"},
        "geometry": nodes,
    }
    fake_resp = MagicMock()
    fake_resp.raise_for_status = MagicMock()
    fake_resp.json.return_value = {"elements": [element]}
    with patch("map_aid.requests.post", return_value=fake_resp):
        return BuildingMask(REF_LAT, REF_LON)


def test_specular_reflection_found():
    """Building east of receiver + satellite from east → at least one reflection."""
    mask = _mask_east()
    reflections = mask.find_specular_reflections(elevation_deg=20.0, azimuth_deg=90.0)
    assert len(reflections) >= 1
    assert reflections[0].extra_path_m > 0.0


def test_no_reflection_clear_sky():
    """Building north of receiver + satellite from south → no reflections (wrong facing)."""
    mask = _mask_with(north_m=50.0)
    reflections = mask.find_specular_reflections(elevation_deg=45.0, azimuth_deg=180.0)
    assert len(reflections) == 0


def test_reflection_path_blocked():
    """
    Reflecting building east, blocking building between it and receiver
    → reflection is suppressed because path from wall to receiver is blocked.
    """
    lat_per_m = 1.0 / 111_000
    cos_lat   = math.cos(math.radians(REF_LAT))
    lon_per_m = 1.0 / (111_000 * cos_lat)

    def _nodes(x0: float, x1: float, y0: float, y1: float) -> list[dict]:
        corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
        return [
            {"lat": REF_LAT + n * lat_per_m, "lon": REF_LON + e * lon_per_m}
            for e, n in corners
        ]

    elements = [
        # Blocker between receiver and reflecting building
        {
            "type": "way",
            "tags": {"building": "yes", "height": "30"},
            "geometry": _nodes(10.0, 30.0, -10.0, 10.0),
        },
        # Reflecting building further east
        {
            "type": "way",
            "tags": {"building": "yes", "height": "30"},
            "geometry": _nodes(60.0, 80.0, -10.0, 10.0),
        },
    ]
    fake_resp = MagicMock()
    fake_resp.raise_for_status = MagicMock()
    fake_resp.json.return_value = {"elements": elements}
    with patch("map_aid.requests.post", return_value=fake_resp):
        mask = BuildingMask(REF_LAT, REF_LON)

    reflections = mask.find_specular_reflections(elevation_deg=20.0, azimuth_deg=90.0)
    # The far-east reflecting building (idx=1) must produce no reflection — its
    # reflected path to the receiver is blocked by the closer building (idx=0).
    assert not any(r.building_idx == 1 for r in reflections)
