"""
nmea_parser.py
Parses $GPGGA and $GPGSV sentences from a GNSS-SDR NMEA output file.

Importable by a FastAPI server — no I/O side-effects at module level.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# Public data classes
# ---------------------------------------------------------------------------

@dataclass
class PositionFix:
    """One position solution, derived from a $GPGGA sentence."""
    timestamp: str          # UTC time of the fix in HHMMSS.ss — when the receiver computed this position
    latitude: float         # how far north or south of the equator you are; positive = North, negative = South
    longitude: float        # how far east or west of the prime meridian you are; positive = East, negative = West
    altitude: float         # height above mean sea level in metres — how high up you are, not above ground
    fix_quality: int        # how the position was computed: 0 = no fix, 1 = standard GPS, 2 = corrected (DGPS)
    num_satellites: int     # how many satellites the receiver used to calculate this position; more = more accurate


@dataclass
class SatelliteInfo:
    """Signal-level data for one satellite, derived from $GPGSV sentences."""
    prn: int                        # the satellite's unique ID number within the GPS constellation (1–32)
    elevation: Optional[float]      # how high the satellite is in the sky in degrees; 0° = on the horizon, 90° = directly overhead
    azimuth: Optional[float]        # which compass direction the satellite is in, in degrees clockwise from true North
    cn0: Optional[float]            # signal strength in dB-Hz; higher is better — below ~25 is unusable, above ~45 is strong


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _strip_checksum(sentence: str) -> str:
    """Return the sentence body without the leading '$' and trailing '*XX'."""
    s = sentence.lstrip("$")
    star = s.rfind("*")
    if star != -1:
        s = s[:star]
    return s


def _nmea_lat(raw: str, hemi: str) -> float:
    """Convert NMEA 'ddmm.mmmmm' + hemisphere to signed decimal degrees."""
    if not raw:
        raise ValueError("empty latitude field")
    deg = float(raw[:2])
    minutes = float(raw[2:])
    dd = deg + minutes / 60.0
    return dd if hemi.upper() == "N" else -dd


def _nmea_lon(raw: str, hemi: str) -> float:
    """Convert NMEA 'dddmm.mmmmm' + hemisphere to signed decimal degrees."""
    if not raw:
        raise ValueError("empty longitude field")
    deg = float(raw[:3])
    minutes = float(raw[3:])
    dd = deg + minutes / 60.0
    return dd if hemi.upper() == "E" else -dd


def _parse_gpgga(sentence: str) -> Optional[PositionFix]:
    """
    Parse one $GPGGA sentence.
    Returns None for any malformed or incomplete sentence.
    """
    try:
        fields = _strip_checksum(sentence).split(",")
        # Minimum required: GPGGA + 9 data fields (up through altitude)
        if len(fields) < 10:
            return None
        timestamp    = fields[1]
        latitude     = _nmea_lat(fields[2], fields[3])
        longitude    = _nmea_lon(fields[4], fields[5])
        fix_quality  = int(fields[6])
        num_sats     = int(fields[7])
        altitude     = float(fields[9])
        return PositionFix(
            timestamp=timestamp,
            latitude=latitude,
            longitude=longitude,
            altitude=altitude,
            fix_quality=fix_quality,
            num_satellites=num_sats,
        )
    except Exception:
        return None


def _parse_gpgsv(sentence: str) -> list[SatelliteInfo]:
    """
    Parse one $GPGSV sentence and return all SatelliteInfo records it contains.

    GNSS-SDR appends a signal-ID field before the checksum, so each message
    ends with an extra field that is NOT part of a satellite group.  The loop
    advances in steps of 4 and stops as soon as fewer than 4 fields remain,
    so the signal-ID (and any other trailing non-satellite fields) are ignored
    safely.  Empty PRN fields (padding in the last message) are also skipped.
    """
    sats: list[SatelliteInfo] = []
    try:
        fields = _strip_checksum(sentence).split(",")
        # fields[0]=GPGSV, [1]=total_msgs, [2]=msg_num, [3]=total_sats_in_view
        # fields[4..] = groups of 4: prn, elevation, azimuth, cn0
        i = 4
        while i + 3 < len(fields):
            prn_raw = fields[i]
            el_raw  = fields[i + 1]
            az_raw  = fields[i + 2]
            cn0_raw = fields[i + 3]

            if prn_raw:  # skip empty padding slots
                sats.append(SatelliteInfo(
                    prn=int(prn_raw),
                    elevation=float(el_raw)  if el_raw  else None,
                    azimuth=float(az_raw)    if az_raw  else None,
                    cn0=float(cn0_raw)       if cn0_raw else None,
                ))
            i += 4
    except Exception:
        pass
    return sats


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_nmea_file(
    path: str | Path,
) -> tuple[list[PositionFix], dict[int, SatelliteInfo]]:
    """
    Read an NMEA file and return:

    - ``fixes``: list of PositionFix in file order (one per valid $GPGGA line)
    - ``satellites``: dict mapping PRN → SatelliteInfo with the *latest*
      observation seen for each satellite across all $GPGSV sentences

    Malformed, incomplete, or unrecognised sentences are silently skipped.
    The file is opened with ``errors='replace'`` so binary noise never raises.
    """
    fixes: list[PositionFix] = []
    satellites: dict[int, SatelliteInfo] = {}

    with open(path, "r", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue

            if line.startswith("$GPGGA"):
                fix = _parse_gpgga(line)
                if fix is not None:
                    fixes.append(fix)

            elif line.startswith("$GPGSV"):
                for sat in _parse_gpgsv(line):
                    satellites[sat.prn] = sat

    return fixes, satellites
