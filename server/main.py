"""
server/main.py
FastAPI server for the GNSS-SDR dashboard.

Loads parsed NMEA data at startup and exposes two REST endpoints:
  GET /api/positions  — list of PositionFix records
  GET /api/satellites — dict of SatelliteInfo records keyed by PRN

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

from nmea_parser import PositionFix, SatelliteInfo, parse_nmea_file  # noqa: E402

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


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _fixes, _satellites
    if NMEA_PATH.exists():
        _fixes, _satellites = parse_nmea_file(NMEA_PATH)
        print(
            f"[startup] Loaded {len(_fixes)} position fixes and "
            f"{len(_satellites)} satellites from {NMEA_PATH.name}"
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


# ---------------------------------------------------------------------------
# Static frontend — catch-all, must come after API routes
# ---------------------------------------------------------------------------
app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
