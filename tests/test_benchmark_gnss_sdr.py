"""
tests/test_benchmark_gnss_sdr.py
Offline tests for tools/benchmark_gnss_sdr.py — uses synthetic log + NMEA fixtures.
"""
from __future__ import annotations

import argparse
import textwrap
from pathlib import Path

import pytest

from tools.benchmark_gnss_sdr import (
    BenchmarkRow,
    _scan_logs,
    _scan_nmea,
    append_csv,
    append_markdown,
    build_row,
)


# ---------------------------------------------------------------------------
# Log scanning
# ---------------------------------------------------------------------------

def _write(p: Path, content: str) -> Path:
    p.write_text(textwrap.dedent(content), encoding="utf-8")
    return p


def test_scan_log_counts_lost_samples(tmp_path):
    log = _write(tmp_path / "g.log", """
        I0426 04:26:18.100000 12345 file.cc:1] starting
        I0426 04:26:19.000000 12345 file.cc:2] 1234 samples lost in buffer
        I0426 04:26:20.000000 12345 file.cc:3] 567 samples dropped
        I0426 04:26:21.000000 12345 file.cc:4] lost_samples=89
    """)
    d = _scan_logs([log])
    assert d["lost_samples"] == 1234 + 567 + 89


def test_scan_log_counts_osmo_overflows(tmp_path):
    log = _write(tmp_path / "g.log", """
        I0426 04:26:18.100000 12345 file.cc:1] starting
        O
        O
        O
    """)
    d = _scan_logs([log])
    assert d["osmo_overflows"] == 3
    assert d["lost_samples"] == 0  # numeric extractor must not double-count


def test_scan_log_tracking_and_prns(tmp_path):
    log = _write(tmp_path / "g.log", """
        I0426 04:26:18.100000 12345 trk.cc:1] starting
        I0426 04:26:19.000000 12345 trk.cc:1] Tracking of GPS L1 C/A signal started on channel 0 for satellite GPS PRN 28
        I0426 04:26:19.500000 12345 trk.cc:1] Tracking of GPS L1 C/A signal started on channel 1 for satellite GPS PRN 31
        I0426 04:26:20.000000 12345 trk.cc:1] Tracking of GPS L1 C/A signal started on channel 2 for satellite GPS PRN 28
        I0426 04:26:21.000000 12345 trk.cc:1] loss of lock in channel 0
    """)
    d = _scan_logs([log])
    assert d["tracking_starts"] == 3
    assert d["tracked_prns"] == {28, 31}
    assert d["loss_of_lock"] == 1


def test_scan_log_ttff(tmp_path):
    log = _write(tmp_path / "g.log", """
        I0426 04:26:18.100000 12345 main.cc:1] GNSS-SDR initializing
        I0426 04:26:20.000000 12345 trk.cc:1] Tracking of GPS L1 C/A signal started on channel 0 for satellite GPS PRN 28
        I0426 04:27:05.350000 12345 pvt.cc:1] Position at 2026-Apr-26 04:27:05.350000 UTC
        I0426 04:27:06.000000 12345 pvt.cc:1] Position at 2026-Apr-26 04:27:06.000000 UTC
    """)
    d = _scan_logs([log])
    # 04:27:05.35 - 04:26:18.10 = 47.25 s
    assert d["ttff_s"] == pytest.approx(47.25, abs=0.01)
    assert d["fixes_in_log"] == 2


def test_scan_log_no_fix_means_ttff_none(tmp_path):
    log = _write(tmp_path / "g.log", """
        I0426 04:26:18.100000 12345 main.cc:1] GNSS-SDR initializing
        I0426 04:26:20.000000 12345 trk.cc:1] Tracking of GPS L1 C/A signal started on channel 0 for satellite GPS PRN 28
    """)
    d = _scan_logs([log])
    assert d["ttff_s"] is None
    assert d["fixes_in_log"] == 0


def test_scan_log_merges_multiple_files(tmp_path):
    a = _write(tmp_path / "a.log", "I0426 04:26:18.100000 1 x:1] 100 samples lost\n")
    b = _write(tmp_path / "b.log", "I0426 04:26:19.000000 1 x:1] 50 samples dropped\n")
    d = _scan_logs([a, b])
    assert d["lost_samples"] == 150


# ---------------------------------------------------------------------------
# NMEA scanning — reuses real nmea_parser
# ---------------------------------------------------------------------------

def test_scan_nmea_extracts_cn0_and_fixes(tmp_path):
    nmea = tmp_path / "out.nmea"
    nmea.write_text(
        "$GPGGA,062331.39,4116.4861665,N,00159.2586972,E,1,05,1.0,77.071,M,0.000,M,0.0,*4B\n"
        "$GPGSV,2,1,05,01,65,104,50,11,44,137,48,17,39,300,48,20,76,333,46,1*68\n"
        "$GPGSV,2,2,05,32,58,047,48,,,,,,,,,,,,,1*52\n",
        encoding="utf-8",
    )
    d = _scan_nmea(nmea)
    assert d["fixes"] == 1
    assert d["sats_with_cn0"] == {1, 11, 17, 20, 32}
    # CN0 values: 50, 48, 48, 46, 48 — mean 48.0, median 48.0
    assert d["mean_cn0"] == pytest.approx(48.0, abs=0.01)
    assert d["median_cn0"] == pytest.approx(48.0, abs=0.01)


# ---------------------------------------------------------------------------
# Row building
# ---------------------------------------------------------------------------

def _args(**overrides) -> argparse.Namespace:
    base = dict(
        label="t", rate_msps=10.0, transport="usb3",
        log=[], nmea=None, duration=120.0,
        output=None, csv=None,
    )
    base.update(overrides)
    return argparse.Namespace(**base)


def test_build_row_combines_log_and_nmea_sat_sets():
    log_d = {
        "lost_samples": 5, "osmo_overflows": 0, "tracking_starts": 3,
        "tracked_prns": {1, 11}, "loss_of_lock": 1,
        "fixes_in_log": 4, "ttff_s": 47.25,
    }
    nmea_d = {
        "fixes": 7, "sats_with_cn0": {11, 17, 20},
        "mean_cn0": 42.5, "median_cn0": 43.0,
    }
    row = build_row(_args(), log_d, nmea_d)
    assert row.sats_acquired == 4   # union {1,11} | {11,17,20}
    assert row.position_fixes == 7  # max of log/nmea
    assert row.mean_cn0 == 42.5
    assert row.ttff_s == 47.25


def test_build_row_no_nmea():
    log_d = {
        "lost_samples": 0, "osmo_overflows": 2, "tracking_starts": 0,
        "tracked_prns": set(), "loss_of_lock": 0,
        "fixes_in_log": 0, "ttff_s": None,
    }
    row = build_row(_args(), log_d, None)
    assert row.sats_acquired == 0
    assert row.mean_cn0 is None
    assert row.ttff_s is None
    assert row.osmo_overflows == 2


# ---------------------------------------------------------------------------
# Output writers
# ---------------------------------------------------------------------------

def _row(**overrides) -> BenchmarkRow:
    base = dict(
        label="r", rate_msps=10.0, transport="usb3", duration_s=120.0,
        lost_samples=0, osmo_overflows=0, tracking_starts=0, loss_of_lock=0,
        sats_acquired=0, mean_cn0=None, median_cn0=None,
        ttff_s=None, position_fixes=0,
    )
    base.update(overrides)
    return BenchmarkRow(**base)


def test_append_markdown_creates_header_then_appends(tmp_path):
    out = tmp_path / "b.md"
    append_markdown(out, _row(label="first", rate_msps=10))
    txt1 = out.read_text(encoding="utf-8")
    assert txt1.count("\n") >= 3  # header + sep + row + trailing newline
    assert "Label" in txt1.splitlines()[0]
    assert "first" in txt1

    append_markdown(out, _row(label="second", rate_msps=20))
    txt2 = out.read_text(encoding="utf-8")
    # Header line still appears exactly once
    assert txt2.count("| Label |") == 1
    assert "second" in txt2
    assert txt2.splitlines()[-1].startswith("| second")


def test_append_csv_writes_header_once(tmp_path):
    out = tmp_path / "b.csv"
    append_csv(out, _row(label="a"))
    append_csv(out, _row(label="b"))
    lines = out.read_text(encoding="utf-8").strip().splitlines()
    assert lines[0].startswith("label,rate_msps")
    assert len(lines) == 3   # header + 2 data rows
    assert lines[1].startswith("a,")
    assert lines[2].startswith("b,")
