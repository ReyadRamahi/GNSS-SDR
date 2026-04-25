"""
kaggle_adapter.py
Parses the Google Smartphone Decimeter Challenge 2022 dataset files into
data structures compatible with the rest of the GNSS-SDR dashboard.

No pandas — stdlib csv module only.
"""
from __future__ import annotations

import csv
import math
from datetime import datetime, timezone
from typing import TypedDict


# ---------------------------------------------------------------------------
# Public data structures (mirror nmea_parser.py conventions)
# ---------------------------------------------------------------------------

class PositionFix(TypedDict):
    lat: float
    lon: float
    alt: float
    time: str           # ISO 8601
    quality: int        # 2 = DGPS / ground-truth grade
    num_satellites: int


class Satellite(TypedDict):
    prn: int
    elevation_deg: float
    azimuth_deg: float
    cn0: float
    constellation: str  # 'GPS', 'GLONASS', 'Galileo', 'BeiDou'


CONSTELLATION_MAP: dict[int, str] = {
    1: "GPS",
    3: "GLONASS",
    5: "Galileo",
    6: "BeiDou",
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _is_nan(value: str) -> bool:
    """Return True for empty strings and IEEE 'NaN' / 'nan' literals."""
    v = value.strip()
    return v == "" or v.lower() == "nan"


def _ms_to_iso(ms: int) -> str:
    """Convert Unix millisecond timestamp to ISO 8601 UTC string."""
    dt = datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def _lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between a and b at fraction t ∈ [0, 1]."""
    return a + (b - a) * t


# ---------------------------------------------------------------------------
# KaggleGnssAdapter
# ---------------------------------------------------------------------------

class KaggleGnssAdapter:
    """
    Parses Kaggle GSDC-2022 dataset files and exposes them through an
    interface compatible with the GNSS-SDR dashboard's data models.
    """

    def __init__(
        self,
        gnss_log_path: str,
        ground_truth_path: str,
        device_gnss_path: str | None = None,
    ) -> None:
        """Parse dataset files. Raises FileNotFoundError if required files are missing."""
        self._gnss_log_path     = gnss_log_path
        self._ground_truth_path = ground_truth_path
        self._device_gnss_path  = device_gnss_path

        # {epoch_ms: [Satellite, ...]}
        self._satellites_by_epoch: dict[int, list[Satellite]] = {}
        # {epoch_ms: {prn: pseudorange_m}}
        self._pseudoranges_by_epoch: dict[int, dict[int, float]] = {}

        self._ground_truth: list[tuple[int, float, float, float]] = []  # (ms, lat, lon, alt)
        self._device_positions: list[PositionFix] = []

        self._parse_gnss_log(gnss_log_path)
        self._parse_position_csv(ground_truth_path, dest="ground_truth")
        if device_gnss_path:
            self._parse_position_csv(device_gnss_path, dest="device")

    # ------------------------------------------------------------------
    # Private parsers
    # ------------------------------------------------------------------

    def _parse_gnss_log(self, path: str) -> None:
        """Parse gnss_log.txt — tab-separated, skip comment lines."""
        with open(path, "r", newline="", errors="replace") as fh:
            header_found = False
            reader = csv.reader(fh, delimiter="\t")
            col: dict[str, int] = {}

            for row in reader:
                if not row:
                    continue
                line = row[0].strip()

                # Skip comment lines
                if line.startswith("#"):
                    continue

                # First non-comment row is the header
                if not header_found:
                    col = {name.strip(): i for i, name in enumerate(row)}
                    header_found = True
                    continue

                # Data row — silently skip if too short
                if len(row) <= max(col.values(), default=0):
                    continue

                self._process_gnss_row(row, col)

    def _process_gnss_row(self, row: list[str], col: dict[str, int]) -> None:
        """Validate and store one gnss_log row."""
        try:
            epoch_ms = int(row[col["utcTimeMillis"]].strip())
        except (KeyError, ValueError):
            return

        # Constellation filter
        try:
            ctype = int(row[col["ConstellationType"]].strip())
        except (KeyError, ValueError):
            return
        constellation = CONSTELLATION_MAP.get(ctype)
        if constellation is None:
            return

        try:
            prn = int(row[col["Svid"]].strip())
        except (KeyError, ValueError):
            return

        # Elevation filter
        el_str = row[col["ElevationDegrees"]].strip() if "ElevationDegrees" in col else ""
        if _is_nan(el_str):
            return
        try:
            elevation = float(el_str)
        except ValueError:
            return
        if elevation < 0:
            return

        # Azimuth
        az_str = row[col["AzimuthDegrees"]].strip() if "AzimuthDegrees" in col else ""
        if _is_nan(az_str):
            azimuth = 0.0
        else:
            try:
                azimuth = float(az_str)
            except ValueError:
                azimuth = 0.0

        # CN0 filter
        cn0_str = row[col["Cn0DbHz"]].strip() if "Cn0DbHz" in col else ""
        if _is_nan(cn0_str):
            return
        try:
            cn0 = float(cn0_str)
        except ValueError:
            return
        if cn0 <= 0:
            return

        sat: Satellite = {
            "prn":           prn,
            "elevation_deg": elevation,
            "azimuth_deg":   azimuth,
            "cn0":           cn0,
            "constellation": constellation,
        }
        self._satellites_by_epoch.setdefault(epoch_ms, []).append(sat)

        # Pseudorange — optional field; NaN means skip
        pr_str = row[col["RawPseudorangeMeters"]].strip() if "RawPseudorangeMeters" in col else ""
        if not _is_nan(pr_str):
            try:
                pr = float(pr_str)
                if math.isfinite(pr):
                    self._pseudoranges_by_epoch.setdefault(epoch_ms, {})[prn] = pr
            except ValueError:
                pass

    def _parse_position_csv(self, path: str, dest: str) -> None:
        """Parse ground_truth.csv or device_gnss.csv (comma-separated)."""
        with open(path, "r", newline="", errors="replace") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                try:
                    ms  = int(row["utcTimeMillis"].strip())
                    lat = float(row["latDeg"].strip())
                    lon = float(row["lngDeg"].strip())
                    alt = float(row["altitudeMeters"].strip()) if "altitudeMeters" in row else 0.0
                except (KeyError, ValueError):
                    continue

                if dest == "ground_truth":
                    self._ground_truth.append((ms, lat, lon, alt))
                else:
                    fix: PositionFix = {
                        "lat":            lat,
                        "lon":            lon,
                        "alt":            alt,
                        "time":           _ms_to_iso(ms),
                        "quality":        1,
                        "num_satellites": 0,
                    }
                    self._device_positions.append(fix)

        if dest == "ground_truth":
            self._ground_truth.sort(key=lambda t: t[0])

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def get_epochs(self) -> list[int]:
        """Sorted list of unique utcTimeMillis values present in gnss_log.txt."""
        return sorted(self._satellites_by_epoch.keys())

    def get_position(self, epoch_ms: int) -> PositionFix | None:
        """
        Ground truth position, linearly interpolated between the two nearest
        ground-truth samples.  Returns None if out of range.
        """
        gt = self._ground_truth
        if not gt:
            return None

        # Exact match
        for ms, lat, lon, alt in gt:
            if ms == epoch_ms:
                return {
                    "lat":            lat,
                    "lon":            lon,
                    "alt":            alt,
                    "time":           _ms_to_iso(epoch_ms),
                    "quality":        2,
                    "num_satellites": 0,
                }

        # Find surrounding samples
        lo_idx = None
        for i, (ms, *_) in enumerate(gt):
            if ms <= epoch_ms:
                lo_idx = i

        if lo_idx is None or lo_idx >= len(gt) - 1:
            return None  # out of range

        hi_idx = lo_idx + 1
        t0, lat0, lon0, alt0 = gt[lo_idx]
        t1, lat1, lon1, alt1 = gt[hi_idx]

        frac = (epoch_ms - t0) / (t1 - t0) if t1 != t0 else 0.0
        return {
            "lat":            _lerp(lat0, lat1, frac),
            "lon":            _lerp(lon0, lon1, frac),
            "alt":            _lerp(alt0, alt1, frac),
            "time":           _ms_to_iso(epoch_ms),
            "quality":        2,
            "num_satellites": 0,
        }

    def get_satellites(self, epoch_ms: int) -> list[Satellite]:
        """All valid satellite measurements for this epoch."""
        return list(self._satellites_by_epoch.get(epoch_ms, []))

    def get_pseudoranges(self, epoch_ms: int) -> dict[int, float]:
        """{prn: pseudorange_metres}. NaN rows are excluded at parse time."""
        return dict(self._pseudoranges_by_epoch.get(epoch_ms, {}))

    def get_ground_truth_positions(self) -> list[PositionFix]:
        """All ground truth positions in chronological order."""
        return [
            {
                "lat":            lat,
                "lon":            lon,
                "alt":            alt,
                "time":           _ms_to_iso(ms),
                "quality":        2,
                "num_satellites": 0,
            }
            for ms, lat, lon, alt in self._ground_truth
        ]

    def get_device_positions(self) -> list[PositionFix]:
        """Phone-reported positions. Empty list if device_gnss_path was not provided."""
        return list(self._device_positions)
