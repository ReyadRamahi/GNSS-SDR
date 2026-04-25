"""
tests/test_websocket.py
WebSocket endpoint and tail_nmea background task tests.
"""
import asyncio
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent / "server"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from server.main import app, manager, tail_nmea  # noqa: E402


# ---------------------------------------------------------------------------
# tail_nmea unit test — write to a temp file and verify broadcast
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_tail_nmea_reads_new_lines(tmp_path, monkeypatch):
    """tail_nmea must broadcast each new line appended to gnss_pvt.nmea."""
    nmea_file = tmp_path / "gnss_pvt.nmea"

    # Point the module-level LIVE_NMEA_PATH at our temp file
    import server.main as main_module
    monkeypatch.setattr(main_module, "LIVE_NMEA_PATH", nmea_file)

    received: list[str] = []

    # Inject a fake WebSocket that records broadcasts
    class FakeWS:
        async def send_text(self, text: str) -> None:
            received.append(text)

    fake_ws = FakeWS()
    manager.active.add(fake_ws)  # type: ignore[arg-type]

    try:
        # Start the tailer as a background task
        task = asyncio.create_task(tail_nmea())

        # Let the tailer start (one sleep cycle)
        await asyncio.sleep(0.15)

        # Write a GGA sentence to the file
        gga = "$GPGGA,092725.00,4124.8963,N,00204.7961,W,1,08,1.01,100.0,M,0.0,M,,*49"
        nmea_file.write_text(gga + "\n")

        # Give the tailer two cycles to pick it up
        await asyncio.sleep(0.3)

        task.cancel()
        await asyncio.wait_for(asyncio.shield(task), timeout=1.0)

    finally:
        manager.active.discard(fake_ws)  # type: ignore[arg-type]

    assert gga in received, f"Expected GGA line to be broadcast; got: {received}"


@pytest.mark.asyncio
async def test_tail_nmea_handles_missing_file(tmp_path, monkeypatch):
    """tail_nmea must not raise when gnss_pvt.nmea does not yet exist."""
    import server.main as main_module
    monkeypatch.setattr(main_module, "LIVE_NMEA_PATH", tmp_path / "nonexistent.nmea")

    task = asyncio.create_task(tail_nmea())
    await asyncio.sleep(0.25)  # several sleep cycles — no exception should surface
    task.cancel()
    await asyncio.wait_for(asyncio.shield(task), timeout=1.0)


# ---------------------------------------------------------------------------
# WebSocket endpoint integration test
# ---------------------------------------------------------------------------

def test_websocket_connect_disconnect():
    """Browser client must be able to connect to /ws and then cleanly close."""
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            # Connection accepted — manager should have exactly one active socket
            assert len(manager.active) == 1
        # After close, manager should have cleaned up
        assert len(manager.active) == 0


def test_websocket_broadcast(tmp_path, monkeypatch):
    """A sentence appended to gnss_pvt.nmea while a client is connected must arrive."""
    import server.main as main_module

    nmea_file = tmp_path / "gnss_pvt.nmea"
    monkeypatch.setattr(main_module, "LIVE_NMEA_PATH", nmea_file)

    sentence = "$GPGGA,120000.00,4124.8963,N,00204.7961,W,1,08,1.01,100.0,M,0.0,M,,*41"

    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            # Write the sentence — the tail_nmea task (started in lifespan) should pick it up
            nmea_file.write_text(sentence + "\n")
            data = ws.receive_text()
            assert data == sentence
