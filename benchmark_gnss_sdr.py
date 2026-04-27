"""
benchmark_gnss_sdr.py
Parse a GNSS-SDR run log (and optionally its NMEA output) and append one row
to a benchmark table comparing sample-rate / transport configurations.

Usage:
    py -3 benchmark_gnss_sdr.py \\
        --label     "10Msps_usb3" \\
        --rate-msps 10 \\
        --transport usb3 \\
        --log       logs/gnss_sdr_10msps.log \\
        --nmea      logs/lime_balanced_10msps.nmea \\
        --duration  180 \\
        --output    benchmark_results.md \\
        --csv       benchmark_results.csv

Append-mode: re-running with a new --label adds a row; the same --label is
not deduplicated (intentional — re-runs are meaningful data points).
"""
from __future__ import annotations

import argparse
import csv
import re
import statistics
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent))

from nmea_parser import parse_nmea_file


# Glog default format: I0426 04:26:18.123456 ...
_GLOG_TS_RE = re.compile(r"^[IWEF]\d{4}\s+(\d{2}:\d{2}:\d{2}\.\d+)")

# "Lost samples", "samples lost", "samples dropped", "samples overflow"
_LOST_SAMPLES_NUMERIC_RE = re.compile(
    r"(\d+)\s*samples?\s+(?:lost|dropped|overflow)", re.I
)
_LOST_SAMPLES_KW_RE = re.compile(r"\blost[_\s]*samples?\D*(\d+)", re.I)

# Standalone "O" line — gr-osmosdr buffer overflow marker (one event, no count)
_OSMO_OVERFLOW_RE = re.compile(r"^\s*O\s*$")

_TRACKING_STARTED_RE = re.compile(r"tracking.*?started", re.I)
_PRN_TOKEN_RE        = re.compile(r"\bPRN\s*(\d+)", re.I)
_LOSS_OF_LOCK_RE     = re.compile(r"loss\s+of\s+lock", re.I)

# RTKLIB_PVT prints "Position at <utc>"; some builds print
# "Current position" or "RTKLIB Status" instead.
_POSITION_FIX_RE = re.compile(
    r"\bposition\s+at\b|\bcurrent\s+position\b|\bRTKLIB.*?Status\b", re.I
)


@dataclass
class BenchmarkRow:
    label:           str
    rate_msps:       float
    transport:       str
    duration_s:      Optional[float]
    lost_samples:    int
    osmo_overflows:  int
    tracking_starts: int
    loss_of_lock:    int
    sats_acquired:   int
    mean_cn0:        Optional[float]
    median_cn0:      Optional[float]
    ttff_s:          Optional[float]
    position_fixes:  int


def _glog_seconds(ts: str) -> float:
    h, m, rest = ts.split(":")
    return int(h) * 3600 + int(m) * 60 + float(rest)


def _scan_logs(paths: list[Path]) -> dict:
    lost           = 0
    overflows      = 0
    track_starts   = 0
    tracked_prns: set[int] = set()
    lol            = 0
    fixes_in_log   = 0
    first_ts:        Optional[float] = None
    first_fix_ts:    Optional[float] = None

    for p in paths:
        with open(p, "r", errors="replace") as fh:
            for line in fh:
                tsm = _GLOG_TS_RE.match(line)
                line_ts: Optional[float] = (
                    _glog_seconds(tsm.group(1)) if tsm else None
                )
                if line_ts is not None and first_ts is None:
                    first_ts = line_ts

                # Lost samples — pick whichever pattern matches; don't double count
                m = _LOST_SAMPLES_NUMERIC_RE.search(line) or _LOST_SAMPLES_KW_RE.search(line)
                if m:
                    try:
                        lost += int(m.group(1))
                    except ValueError:
                        pass
                elif _OSMO_OVERFLOW_RE.match(line):
                    overflows += 1

                if _TRACKING_STARTED_RE.search(line):
                    track_starts += 1
                    pm = _PRN_TOKEN_RE.search(line)
                    if pm:
                        try:
                            tracked_prns.add(int(pm.group(1)))
                        except ValueError:
                            pass

                if _LOSS_OF_LOCK_RE.search(line):
                    lol += 1

                if _POSITION_FIX_RE.search(line):
                    fixes_in_log += 1
                    if first_fix_ts is None and line_ts is not None:
                        first_fix_ts = line_ts

    ttff = None
    if first_ts is not None and first_fix_ts is not None:
        ttff = max(0.0, first_fix_ts - first_ts)

    return {
        "lost_samples":   lost,
        "osmo_overflows": overflows,
        "tracking_starts": track_starts,
        "tracked_prns":   tracked_prns,
        "loss_of_lock":   lol,
        "fixes_in_log":   fixes_in_log,
        "ttff_s":         ttff,
    }


def _scan_nmea(path: Path) -> dict:
    fixes, sats = parse_nmea_file(path)
    cn0_vals = [s.cn0 for s in sats.values() if s.cn0 is not None]
    prns_with_cn0 = {s.prn for s in sats.values() if s.cn0 is not None and s.cn0 > 0}
    return {
        "fixes":          len(fixes),
        "sats_with_cn0":  prns_with_cn0,
        "mean_cn0":       statistics.mean(cn0_vals) if cn0_vals else None,
        "median_cn0":     statistics.median(cn0_vals) if cn0_vals else None,
    }


def build_row(args: argparse.Namespace, log_d: dict, nmea_d: Optional[dict]) -> BenchmarkRow:
    sats = log_d["tracked_prns"] | (nmea_d["sats_with_cn0"] if nmea_d else set())
    fixes = max(log_d["fixes_in_log"], nmea_d["fixes"] if nmea_d else 0)
    return BenchmarkRow(
        label           = args.label,
        rate_msps       = args.rate_msps,
        transport       = args.transport,
        duration_s      = args.duration,
        lost_samples    = log_d["lost_samples"],
        osmo_overflows  = log_d["osmo_overflows"],
        tracking_starts = log_d["tracking_starts"],
        loss_of_lock    = log_d["loss_of_lock"],
        sats_acquired   = len(sats),
        mean_cn0        = round(nmea_d["mean_cn0"], 2)   if nmea_d and nmea_d["mean_cn0"]   is not None else None,
        median_cn0      = round(nmea_d["median_cn0"], 2) if nmea_d and nmea_d["median_cn0"] is not None else None,
        ttff_s          = round(log_d["ttff_s"], 2)      if log_d["ttff_s"]                 is not None else None,
        position_fixes  = fixes,
    )


_COLUMNS: list[tuple[str, str]] = [
    ("label",           "Label"),
    ("rate_msps",       "Rate (Msps)"),
    ("transport",       "Transport"),
    ("duration_s",      "Run dur (s)"),
    ("lost_samples",    "Lost samples"),
    ("osmo_overflows",  "Osmo overflows"),
    ("tracking_starts", "Tracking starts"),
    ("loss_of_lock",    "Loss of lock"),
    ("sats_acquired",   "Sats acq"),
    ("mean_cn0",        "Mean CN0"),
    ("median_cn0",      "Median CN0"),
    ("ttff_s",          "TTFF (s)"),
    ("position_fixes",  "Fixes"),
]


def _fmt(v: object) -> str:
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:g}"
    return str(v)


def append_markdown(path: Path, row: BenchmarkRow) -> None:
    keys    = [k for k, _ in _COLUMNS]
    headers = [h for _, h in _COLUMNS]
    new_line = "| " + " | ".join(_fmt(getattr(row, k)) for k in keys) + " |"

    if path.exists() and path.stat().st_size > 0:
        existing = path.read_text(encoding="utf-8").rstrip()
        path.write_text(existing + "\n" + new_line + "\n", encoding="utf-8")
    else:
        header_line = "| " + " | ".join(headers) + " |"
        sep_line    = "|" + "|".join(["---"] * len(headers)) + "|"
        path.write_text(
            header_line + "\n" + sep_line + "\n" + new_line + "\n",
            encoding="utf-8",
        )


def append_csv(path: Path, row: BenchmarkRow) -> None:
    keys = [k for k, _ in _COLUMNS]
    write_header = not path.exists() or path.stat().st_size == 0
    with open(path, "a", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        if write_header:
            w.writerow(keys)
        w.writerow([_fmt(getattr(row, k)) for k in keys])


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Append one row to the GNSS-SDR sample-rate / transport benchmark table."
    )
    p.add_argument("--label",     required=True,
                   help='Run label, e.g. "10Msps_usb3_baseline"')
    p.add_argument("--rate-msps", type=float, required=True)
    p.add_argument("--transport", default="usb3",
                   help='Transport identifier: "usb3" / "ethernet" / etc. (default: usb3)')
    p.add_argument("--log",       required=True, action="append", default=[], type=Path,
                   help="GNSS-SDR stdout/stderr log path (repeat to merge several files)")
    p.add_argument("--nmea",      type=Path, default=None,
                   help="Optional gnss_pvt.nmea path — used for CN0 stats and fix count")
    p.add_argument("--duration",  type=float, default=None,
                   help="Run duration in seconds (informational)")
    p.add_argument("--output",    type=Path, default=Path("benchmark_results.md"))
    p.add_argument("--csv",       type=Path, default=None)
    return p.parse_args()


def main() -> None:
    args = _parse_args()

    for p in args.log:
        if not p.exists():
            print(f"ERROR: log file not found: {p}", file=sys.stderr)
            sys.exit(2)
    if args.nmea is not None and not args.nmea.exists():
        print(f"WARNING: NMEA file not found, skipping CN0 stats: {args.nmea}",
              file=sys.stderr)

    log_d  = _scan_logs(args.log)
    nmea_d = _scan_nmea(args.nmea) if args.nmea and args.nmea.exists() else None
    row    = build_row(args, log_d, nmea_d)

    append_markdown(args.output, row)
    if args.csv:
        append_csv(args.csv, row)

    print(f"Appended row to {args.output}:")
    for k, v in asdict(row).items():
        print(f"  {k:<16} {v}")


if __name__ == "__main__":
    main()
