"""
tests/test_kaggle_adapter.py
Offline tests for kaggle_adapter.py using synthetic fixture files.
No network access, no real Kaggle data.
"""
from __future__ import annotations

import math
import os
import textwrap
from pathlib import Path

import pytest

from kaggle_adapter import KaggleGnssAdapter


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def _write(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(textwrap.dedent(content), encoding="utf-8")
    return str(p)


def _gnss_log(tmp_path: Path, extra_rows: str = "") -> str:
    """Minimal gnss_log.txt with 2 epochs, 3 satellites each."""
    header = "utcTimeMillis\tSvid\tConstellationType\tCn0DbHz\tAzimuthDegrees\tElevationDegrees\tRawPseudorangeMeters\n"
    rows = (
        "1000\t1\t1\t40.0\t90.0\t30.0\t23000000.0\n"   # epoch 1, PRN 1, GPS
        "1000\t3\t1\t38.0\t180.0\t45.0\t22000000.0\n"  # epoch 1, PRN 3, GPS
        "1000\t5\t5\t35.0\t270.0\t20.0\t24000000.0\n"  # epoch 1, PRN 5, Galileo
        "2000\t1\t1\t42.0\t95.0\t32.0\t23100000.0\n"   # epoch 2, PRN 1, GPS
        "2000\t7\t3\t30.0\t50.0\t15.0\t25000000.0\n"   # epoch 2, PRN 7, GLONASS
        "2000\t9\t6\t36.0\t300.0\t25.0\t23500000.0\n"  # epoch 2, PRN 9, BeiDou
    )
    return _write(tmp_path, "gnss_log.txt", "# comment line\n" + header + rows + extra_rows)


def _ground_truth(tmp_path: Path) -> str:
    content = (
        "utcTimeMillis,latDeg,lngDeg,altitudeMeters\n"
        "500,37.33000,-121.88000,10.0\n"
        "1500,37.33100,-121.87900,11.0\n"
        "2500,37.33200,-121.87800,12.0\n"
    )
    return _write(tmp_path, "ground_truth.csv", content)


def _device_gnss(tmp_path: Path) -> str:
    content = (
        "utcTimeMillis,latDeg,lngDeg,altitudeMeters\n"
        "1000,37.330123,-121.879876,10.5\n"
        "2000,37.331234,-121.878765,11.5\n"
    )
    return _write(tmp_path, "device_gnss.csv", content)


def _adapter(tmp_path: Path, extra_rows: str = "") -> KaggleGnssAdapter:
    return KaggleGnssAdapter(
        gnss_log_path=_gnss_log(tmp_path, extra_rows),
        ground_truth_path=_ground_truth(tmp_path),
        device_gnss_path=_device_gnss(tmp_path),
    )


# ---------------------------------------------------------------------------
# Parsing tests
# ---------------------------------------------------------------------------

def test_parse_gnss_log_basic(tmp_path):
    """2 epochs, 3 satellites each — verify counts."""
    adapter = _adapter(tmp_path)
    epochs = adapter.get_epochs()
    assert epochs == [1000, 2000]
    assert len(adapter.get_satellites(1000)) == 3
    assert len(adapter.get_satellites(2000)) == 3


def test_parse_ground_truth_interpolation(tmp_path):
    """Position at 1000 ms is midpoint between 500 and 1500 ms samples."""
    adapter = _adapter(tmp_path)
    pos = adapter.get_position(1000)
    assert pos is not None
    # Midpoint between (37.33000, -121.88000) and (37.33100, -121.87900)
    assert abs(pos["lat"] - 37.33050) < 1e-6
    assert abs(pos["lon"] - (-121.87950)) < 1e-6


def test_constellation_mapping(tmp_path):
    """ConstellationType 1/3/5/6 → GPS/GLONASS/Galileo/BeiDou."""
    adapter = _adapter(tmp_path)

    by_prn_ep1 = {s["prn"]: s for s in adapter.get_satellites(1000)}
    assert by_prn_ep1[1]["constellation"] == "GPS"
    assert by_prn_ep1[5]["constellation"] == "Galileo"

    by_prn_ep2 = {s["prn"]: s for s in adapter.get_satellites(2000)}
    assert by_prn_ep2[7]["constellation"] == "GLONASS"
    assert by_prn_ep2[9]["constellation"] == "BeiDou"


def test_filter_nan_elevation(tmp_path):
    """Row with NaN elevation is excluded from get_satellites()."""
    extra = "3000\t20\t1\t38.0\t180.0\tNaN\t22000000.0\n"
    adapter = _adapter(tmp_path, extra_rows=extra)
    sats = adapter.get_satellites(3000)
    assert len(sats) == 0


def test_filter_zero_cn0(tmp_path):
    """Row with Cn0DbHz = 0 is excluded from get_satellites()."""
    extra = "3000\t20\t1\t0.0\t180.0\t30.0\t22000000.0\n"
    adapter = _adapter(tmp_path, extra_rows=extra)
    sats = adapter.get_satellites(3000)
    assert len(sats) == 0


def test_filter_nan_pseudorange(tmp_path):
    """NaN pseudorange excluded from get_pseudoranges() but satellite still in get_satellites()."""
    extra = "3000\t20\t1\t38.0\t180.0\t30.0\tNaN\n"
    adapter = _adapter(tmp_path, extra_rows=extra)
    sats = adapter.get_satellites(3000)
    assert len(sats) == 1
    assert sats[0]["prn"] == 20
    prs = adapter.get_pseudoranges(3000)
    assert 20 not in prs


def test_device_positions_loaded(tmp_path):
    """Device positions are parsed when path is provided."""
    adapter = _adapter(tmp_path)
    device = adapter.get_device_positions()
    assert len(device) == 2
    assert abs(device[0]["lat"] - 37.330123) < 1e-6


def test_device_positions_empty_when_not_provided(tmp_path):
    """get_device_positions() returns [] when device_gnss_path is None."""
    adapter = KaggleGnssAdapter(
        gnss_log_path=_gnss_log(tmp_path),
        ground_truth_path=_ground_truth(tmp_path),
        device_gnss_path=None,
    )
    assert adapter.get_device_positions() == []


def test_get_position_out_of_range(tmp_path):
    """Epoch before all ground truth samples returns None."""
    adapter = _adapter(tmp_path)
    assert adapter.get_position(100) is None


def test_comment_lines_skipped(tmp_path):
    """Lines starting with # are not treated as data."""
    adapter = _adapter(tmp_path)
    # Fixture has one comment line; epochs should still be exactly 2
    assert len(adapter.get_epochs()) == 2


def test_pseudoranges_parsed(tmp_path):
    """Pseudoranges match fixture values for epoch 1000."""
    adapter = _adapter(tmp_path)
    prs = adapter.get_pseudoranges(1000)
    assert abs(prs[1] - 23_000_000.0) < 1.0
    assert abs(prs[3] - 22_000_000.0) < 1.0


# ---------------------------------------------------------------------------
# Math helpers (imported from validate_multipath after it exists)
# ---------------------------------------------------------------------------

# Import lazily so the test file can still be collected before validate_multipath exists
def _import_helpers():
    from validate_multipath import pearson_correlation, rmse  # noqa: PLC0415
    return pearson_correlation, rmse


def test_pearson_perfect_positive(tmp_path):
    pearson_correlation, _ = _import_helpers()
    r = pearson_correlation([1.0, 2.0, 3.0], [2.0, 4.0, 6.0])
    assert abs(r - 1.0) < 1e-9


def test_pearson_perfect_negative(tmp_path):
    pearson_correlation, _ = _import_helpers()
    r = pearson_correlation([1.0, 2.0, 3.0], [3.0, 2.0, 1.0])
    assert abs(r - (-1.0)) < 1e-9


def test_pearson_insufficient_data(tmp_path):
    pearson_correlation, _ = _import_helpers()
    r = pearson_correlation([1.0], [2.0])
    assert r == 0.0


def test_rmse(tmp_path):
    _, rmse = _import_helpers()
    result = rmse([3.0, 4.0])
    assert abs(result - math.sqrt((9.0 + 16.0) / 2.0)) < 1e-9
