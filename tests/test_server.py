"""Startup and REST smoke checks using a local synthetic recording."""
from fastapi.testclient import TestClient

from server import main


def test_recording_startup_exposes_rest_data(tmp_path, monkeypatch):
    recording = tmp_path / "recording.nmea"
    recording.write_text(
        "$GPGGA,120000.00,4116.5000,N,00159.2200,E,1,08,1.0,24.3,M,0,M,,\n"
        "$GPGSV,1,1,2,03,62,024,46,19,73,230,49\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(main, "NMEA_PATH", recording)
    monkeypatch.setattr(main, "LIVE_NMEA_PATH", tmp_path / "not-running.nmea")
    for name in ("_fixes", "_satellites", "_satellite_history", "_raw_sentences"):
        monkeypatch.setattr(main, name, [] if name in {"_fixes", "_raw_sentences"} else {})
    monkeypatch.setattr(main, "building_mask", None)

    async def no_external_building_lookup(lat, lon):
        pass

    monkeypatch.setattr(main, "_init_building_mask", no_external_building_lookup)
    with TestClient(main.app) as client:
        positions = client.get("/api/positions")
        assert positions.status_code == 200
        assert positions.json()[0]["latitude"] == 41.275
        satellites = client.get("/api/satellites")
        assert satellites.status_code == 200
        assert satellites.json()["3"]["cn0"] == 46.0
        history = client.get("/api/satellite-history")
        assert history.status_code == 200
        assert history.json()["19"] == [{"t": "120000.00", "cn0": 49.0}]
        raw = client.get("/api/raw")
        assert raw.status_code == 200
        assert len(raw.json()["sentences"]) == 2
