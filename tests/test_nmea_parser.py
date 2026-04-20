"""
tests/test_nmea_parser.py
Unit tests for nmea_parser.py, run against the real gnss_pvt.nmea file.
"""
import math
from pathlib import Path

import pytest

from nmea_parser import (
    PositionFix,
    SatelliteInfo,
    _nmea_lat,
    _nmea_lon,
    _parse_gpgga,
    _parse_gpgsv,
    parse_nmea_file,
)

# ---------------------------------------------------------------------------
# Resolve the real data file relative to this test file
# ---------------------------------------------------------------------------
NMEA_FILE = (
    Path(__file__).parent.parent
    / "CTTC_GPS"
    / "2013_04_04_GNSS_SIGNAL_at_CTTC_SPAIN"
    / "gnss_pvt.nmea"
)

# First $GPGGA line in the file (line 2):
# $GPGGA,062331.39,4116.4861665,N,00159.2586972,E,1,05,1.0,77.071,M,0.000,M,0.0,*4B
FIRST_GGA = "$GPGGA,062331.39,4116.4861665,N,00159.2586972,E,1,05,1.0,77.071,M,0.000,M,0.0,*4B"

# First pair of $GPGSV lines (lines 4–5):
GSV_MSG1 = "$GPGSV,2,1,05,01,65,104,50,11,44,137,48,17,39,300,48,20,76,333,46,1*68"
GSV_MSG2 = "$GPGSV,2,2,05,32,58,047,48,,,,,,,,,,,,,1*52"


# ---------------------------------------------------------------------------
# Coordinate-conversion helpers
# ---------------------------------------------------------------------------

class TestNmeaCoordinates:
    def test_lat_north(self):
        # 41°16.4861665' N → 41 + 16.4861665/60
        result = _nmea_lat("4116.4861665", "N")
        assert math.isclose(result, 41 + 16.4861665 / 60, rel_tol=1e-9)

    def test_lat_south(self):
        result = _nmea_lat("3300.0000", "S")
        assert result < 0

    def test_lon_east(self):
        # 001°59.2586972' E → 1 + 59.2586972/60
        result = _nmea_lon("00159.2586972", "E")
        assert math.isclose(result, 1 + 59.2586972 / 60, rel_tol=1e-9)

    def test_lon_west(self):
        result = _nmea_lon("08730.0000", "W")
        assert result < 0

    def test_lat_empty_raises(self):
        with pytest.raises(ValueError):
            _nmea_lat("", "N")

    def test_lon_empty_raises(self):
        with pytest.raises(ValueError):
            _nmea_lon("", "E")


# ---------------------------------------------------------------------------
# $GPGGA sentence parsing
# ---------------------------------------------------------------------------

class TestParseGpgga:
    def test_returns_position_fix(self):
        fix = _parse_gpgga(FIRST_GGA)
        assert isinstance(fix, PositionFix)

    def test_timestamp(self):
        fix = _parse_gpgga(FIRST_GGA)
        assert fix.timestamp == "062331.39"

    def test_latitude(self):
        fix = _parse_gpgga(FIRST_GGA)
        expected = 41 + 16.4861665 / 60
        assert math.isclose(fix.latitude, expected, rel_tol=1e-9)

    def test_longitude(self):
        fix = _parse_gpgga(FIRST_GGA)
        expected = 1 + 59.2586972 / 60
        assert math.isclose(fix.longitude, expected, rel_tol=1e-9)

    def test_altitude(self):
        fix = _parse_gpgga(FIRST_GGA)
        assert math.isclose(fix.altitude, 77.071)

    def test_fix_quality(self):
        fix = _parse_gpgga(FIRST_GGA)
        assert fix.fix_quality == 1

    def test_num_satellites(self):
        fix = _parse_gpgga(FIRST_GGA)
        assert fix.num_satellites == 5

    def test_malformed_returns_none(self):
        assert _parse_gpgga("$GPGGA,bad,data") is None

    def test_empty_sentence_returns_none(self):
        assert _parse_gpgga("$GPGGA") is None

    def test_truncated_returns_none(self):
        assert _parse_gpgga("$GPGGA,062331.39,4116.4861665,N") is None


# ---------------------------------------------------------------------------
# $GPGSV sentence parsing
# ---------------------------------------------------------------------------

class TestParseGpgsv:
    def test_first_message_returns_four_sats(self):
        sats = _parse_gpgsv(GSV_MSG1)
        assert len(sats) == 4

    def test_second_message_returns_one_sat(self):
        # Only PRN 32 has data; the remaining 12 fields are empty padding
        sats = _parse_gpgsv(GSV_MSG2)
        assert len(sats) == 1

    def test_prns_from_first_message(self):
        sats = _parse_gpgsv(GSV_MSG1)
        prns = {s.prn for s in sats}
        assert prns == {1, 11, 17, 20}

    def test_prn_from_second_message(self):
        sats = _parse_gpgsv(GSV_MSG2)
        assert sats[0].prn == 32

    def test_satellite_values_prn1(self):
        # PRN 1: el=65, az=104, cn0=50
        sats = {s.prn: s for s in _parse_gpgsv(GSV_MSG1)}
        s = sats[1]
        assert s.elevation == 65.0
        assert s.azimuth == 104.0
        assert s.cn0 == 50.0

    def test_satellite_values_prn32(self):
        sats = _parse_gpgsv(GSV_MSG2)
        s = sats[0]
        assert s.prn == 32
        assert s.elevation == 58.0
        assert s.azimuth == 47.0
        assert s.cn0 == 48.0

    def test_malformed_returns_empty(self):
        assert _parse_gpgsv("$GPGSV,garbage") == []

    def test_empty_sentence_returns_empty(self):
        assert _parse_gpgsv("$GPGSV") == []

    def test_returns_satellite_info_instances(self):
        sats = _parse_gpgsv(GSV_MSG1)
        assert all(isinstance(s, SatelliteInfo) for s in sats)


# ---------------------------------------------------------------------------
# Full-file integration tests (real gnss_pvt.nmea)
# ---------------------------------------------------------------------------

class TestParseNmeaFile:
    @pytest.fixture(scope="class")
    def parsed(self):
        if not NMEA_FILE.exists():
            pytest.skip(
                f"Integration dataset not found at {NMEA_FILE}. "
                "Download the CTTC GPS dataset locally to run full-file parser tests."
            )
        return parse_nmea_file(NMEA_FILE)

    def test_returns_tuple(self, parsed):
        fixes, satellites = parsed
        assert isinstance(fixes, list)
        assert isinstance(satellites, dict)

    def test_fixes_non_empty(self, parsed):
        fixes, _ = parsed
        assert len(fixes) > 0

    def test_satellites_non_empty(self, parsed):
        _, satellites = parsed
        assert len(satellites) > 0

    def test_expected_prns_present(self, parsed):
        # The file consistently tracks PRNs 1, 11, 17, 20, 32
        _, satellites = parsed
        assert {1, 11, 17, 20, 32}.issubset(satellites.keys())

    def test_all_fixes_are_position_fix(self, parsed):
        fixes, _ = parsed
        assert all(isinstance(f, PositionFix) for f in fixes)

    def test_all_satellites_are_satellite_info(self, parsed):
        _, satellites = parsed
        assert all(isinstance(s, SatelliteInfo) for s in satellites.values())

    def test_first_fix_timestamp(self, parsed):
        fixes, _ = parsed
        assert fixes[0].timestamp == "062331.39"

    def test_first_fix_latitude_in_spain(self, parsed):
        # CTTC is in Castelldefels, Spain (~41.3°N, ~1.99°E)
        fixes, _ = parsed
        assert 41.0 < fixes[0].latitude < 42.0

    def test_first_fix_longitude_in_spain(self, parsed):
        fixes, _ = parsed
        assert 1.0 < fixes[0].longitude < 3.0

    def test_altitudes_plausible(self, parsed):
        fixes, _ = parsed
        for fix in fixes:
            assert -100 < fix.altitude < 5000

    def test_fix_quality_always_valid(self, parsed):
        fixes, _ = parsed
        for fix in fixes:
            assert fix.fix_quality in range(9)

    def test_num_satellites_always_positive(self, parsed):
        fixes, _ = parsed
        for fix in fixes:
            assert fix.num_satellites > 0

    def test_cn0_values_plausible(self, parsed):
        # Typical GNSS CN0 range is 20–55 dB-Hz
        _, satellites = parsed
        for sat in satellites.values():
            if sat.cn0 is not None:
                assert 0 < sat.cn0 < 70, f"PRN {sat.prn} CN0={sat.cn0} out of range"

    def test_elevations_in_range(self, parsed):
        _, satellites = parsed
        for sat in satellites.values():
            if sat.elevation is not None:
                assert 0 <= sat.elevation <= 90

    def test_azimuths_in_range(self, parsed):
        _, satellites = parsed
        for sat in satellites.values():
            if sat.azimuth is not None:
                assert 0 <= sat.azimuth < 360

    def test_fix_count_matches_line_count(self, parsed):
        # Every $GPGGA line in the file should produce exactly one fix
        fixes, _ = parsed
        gpgga_count = sum(
            1 for line in NMEA_FILE.read_text(errors="replace").splitlines()
            if line.startswith("$GPGGA")
        )
        assert len(fixes) == gpgga_count
