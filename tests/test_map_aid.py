"""
test_map_aid.py
pytest suite for map_aid.BuildingMask — no internet required.
All Overpass API calls are mocked.
"""
from __future__ import annotations

import math
from unittest.mock import MagicMock, patch

import pytest

from map_aid import (
    DEFAULT_FLOOR_HEIGHT_M,
    BuildingMask,
    _estimate_height,
    _latlon_to_enu,
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
