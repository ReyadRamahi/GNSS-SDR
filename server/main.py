"""
server/main.py
FastAPI server for the GNSS-SDR dashboard.

Loads parsed NMEA data at startup and exposes four REST endpoints:
  GET /api/positions          — list of PositionFix records
  GET /api/satellites         — dict of SatelliteInfo records keyed by PRN
  GET /api/satellite-history  — per-PRN CN0 time series for the details tab
  GET /api/raw                — last 50 raw NMEA sentences for the raw-data tab

Static frontend files are served from frontend/ at the project root.
"""
from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

# ---------------------------------------------------------------------------
# Resolve project root and add it to sys.path so nmea_parser is importable
# regardless of where uvicorn is launched from.
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from nmea_parser import (  # noqa: E402
    PositionFix,
    SatelliteInfo,
    parse_nmea_file,
    _parse_gpgga,   # private helpers – stable for internal use
    _parse_gpgsv,
)

NMEA_PATH = (
    ROOT
    / "CTTC_GPS"
    / "2013_04_04_GNSS_SIGNAL_at_CTTC_SPAIN"
    / "gnss_pvt.nmea"
)
FRONTEND_DIR = ROOT / "frontend"

# ---------------------------------------------------------------------------
# Application state — populated at startup
# ---------------------------------------------------------------------------
_fixes: list[PositionFix] = []
_satellites: dict[int, SatelliteInfo] = {}
_satellite_history: dict[int, list[dict]] = {}
_raw_sentences: list[str] = []


def _build_satellite_history(path: Path) -> dict[int, list[dict]]:
    """
    Walk the NMEA file epoch by epoch and build a CN0 time series per PRN.

    Each epoch is one GPGGA (with a UTC timestamp) followed by one or more
    GPGSV sentences.  The function associates the GSV satellite readings with
    the GGA timestamp and appends {"t": timestamp, "cn0": value} to each
    PRN's list.

    The result is subsampled to at most 300 points per PRN so the frontend
    chart remains snappy regardless of file length.
    """
    history: dict[int, list[dict]] = {}
    current_ts: str | None = None
    epoch_sats: dict[int, float] = {}

    def _flush() -> None:
        nonlocal epoch_sats
        if current_ts is not None and epoch_sats:
            for prn, cn0 in epoch_sats.items():
                history.setdefault(prn, []).append({"t": current_ts, "cn0": cn0})
        epoch_sats = {}

    with open(path, "r", errors="replace") as fh:
        for raw in fh:
            line = raw.strip()
            if not line:
                continue
            if line.startswith("$GPGGA"):
                _flush()
                fix = _parse_gpgga(line)
                if fix is not None:
                    current_ts = fix.timestamp
            elif line.startswith("$GPGSV"):
                for sat in _parse_gpgsv(line):
                    if sat.cn0 is not None:
                        epoch_sats[sat.prn] = sat.cn0
    _flush()

    # Subsample to ≤ 300 points per PRN
    for prn, data in history.items():
        if len(data) > 300:
            step = len(data) // 300
            history[prn] = data[::step]

    return history


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _fixes, _satellites, _satellite_history, _raw_sentences
    if NMEA_PATH.exists():
        _fixes, _satellites = parse_nmea_file(NMEA_PATH)
        _satellite_history = _build_satellite_history(NMEA_PATH)
        with open(NMEA_PATH, "r", errors="replace") as fh:
            _raw_sentences = [ln.strip() for ln in fh if ln.strip()]
        print(
            f"[startup] Loaded {len(_fixes)} position fixes, "
            f"{len(_satellites)} satellites, "
            f"{len(_raw_sentences)} raw sentences from {NMEA_PATH.name}"
        )
    else:
        print(
            f"[startup] WARNING: NMEA file not found at {NMEA_PATH}. "
            "Download the CTTC GPS dataset to enable full endpoints."
        )
    yield


app = FastAPI(title="GNSS-SDR Dashboard", version="0.1.0", lifespan=lifespan)


# ---------------------------------------------------------------------------
# REST endpoints  (must be defined before the static-file catch-all mount)
# ---------------------------------------------------------------------------

@app.get("/api/positions", summary="All position fixes from the NMEA file")
def get_positions() -> list[dict]:
    """
    Returns every PositionFix parsed from $GPGGA sentences, in file order.
    Each record contains: timestamp, latitude, longitude, altitude,
    fix_quality, num_satellites.
    """
    if not _fixes:
        raise HTTPException(status_code=503, detail="NMEA data not loaded")
    return [asdict(f) for f in _fixes]


@app.get("/api/satellites", summary="Latest satellite info keyed by PRN")
def get_satellites() -> dict[str, dict]:
    """
    Returns the latest SatelliteInfo per PRN parsed from $GPGSV sentences.
    Keys are PRN numbers (as strings, per JSON spec).
    Each record contains: prn, elevation, azimuth, cn0.
    """
    if not _satellites:
        raise HTTPException(status_code=503, detail="NMEA data not loaded")
    return {str(prn): asdict(sat) for prn, sat in sorted(_satellites.items())}


@app.get("/api/satellite-history", summary="Per-PRN CN0 time series for the details tab")
def get_satellite_history() -> dict[str, list[dict]]:
    """
    Returns a CN0 time series for each PRN, suitable for a multi-line chart.
    Each entry is {"t": "HHMMSS.ss", "cn0": float}.
    Already subsampled to ≤ 300 points per PRN.
    """
    if not _satellite_history:
        raise HTTPException(status_code=503, detail="NMEA data not loaded")
    return {str(prn): data for prn, data in sorted(_satellite_history.items())}


@app.get("/api/raw", summary="Last 50 raw NMEA sentences for the raw-data tab")
def get_raw() -> dict[str, list[str]]:
    """
    Returns the last 50 NMEA sentences exactly as they appear in the file.
    Used by the Raw Data tab to display a scrolling feed.
    """
    if not _raw_sentences:
        raise HTTPException(status_code=503, detail="NMEA data not loaded")
    return {"sentences": _raw_sentences[-50:]}


# ---------------------------------------------------------------------------
# Static frontend — catch-all, must come after API routes
# ---------------------------------------------------------------------------
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
