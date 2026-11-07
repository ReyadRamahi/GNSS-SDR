# IE 421 Group 16 Project

GNSS-SDR post-processing dashboard. Parses a GNSS-SDR NMEA output file, exposes it over a FastAPI REST server, and renders an interactive 3-D globe with satellite visualization in a single-page browser frontend.

---

## Project structure

```
.
├── nmea_parser.py          # NMEA sentence parser (GGA + GSV)
├── test_nmea_parser.py     # pytest suite (41 tests)
├── server/
│   ├── main.py             # FastAPI server — REST endpoints + static file serving
│   └── requirements.txt    # Python dependencies
└── frontend/
    ├── src/                # React components, hooks, and telemetry helpers
    ├── public/             # Earth texture
    └── package.json        # Vite dev server and build scripts
```

---

## Dependencies

### Backend — Python

Requires **Python 3.10+**.

| Package | Version | Purpose |
|---|---|---|
| `fastapi` | ≥ 0.110.0 | REST API framework |
| `uvicorn[standard]` | ≥ 0.29.0 | ASGI server |

Install with:

```bash
pip install -r server/requirements.txt
```

### Frontend — React + Three.js

Requires Node.js 20.19+ or 22.12+ (Vite 7 requirements).

```bash
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173. Vite proxies `/api` and `/ws` to FastAPI on port 8000. Run the backend in a second terminal. Use **Explore demo** to try the interface without a recording; demo data is explicitly simulated. The app never substitutes demo data for missing receiver data.

For one-server deployment:

```bash
cd frontend
npm ci
npm run build
cd ..
uvicorn server.main:app --reload
```

FastAPI serves `frontend/dist/`. Restart the server after the first build. `/api/*` and `/ws` are unchanged. A connected but idle WebSocket does not mark the interface as live; valid incoming GGA/GSV sentences do. Replay polling resumes after six seconds without valid telemetry.

The dashboard includes satellite selection, per-satellite CN₀ bars and history, sky plot, raw NMEA feed, camera reset, beam visibility, and timestamp-based replay with speed controls. Sky plot and beams require azimuth/elevation. Satellite locations are schematic projections from azimuth/elevation at a compressed 3,500 km display distance, not ephemeris-derived orbits. Replay history supplies CN₀; recorded azimuth/elevation are the latest available values because the API has no geometry history. Raw data is the endpoint's latest 50-sentence snapshot.

#### Learning the React code

Read [the frontend guide](frontend/README.md) for the component map and suggested learning exercises.

### Dev / testing

| Package | Purpose |
|---|---|
| `pytest` | Test runner |

---

## Running the server

```bash
# from the repo root
uvicorn server.main:app --reload
```

Then open [http://localhost:8000](http://localhost:8000) in a browser.

---

## Large Dataset Setup

This repo does not store the GNSS data files in Git because they are too large for GitLab. Each teammate needs to download them locally before running the parser integration tests.

Datasets:

- CTTC Spain GPS L1 C/A: https://sourceforge.net/projects/gnss-sdr/files/data/2013_04_04_GNSS_SIGNAL_at_CTTC_SPAIN.tar.gz/download
- LimeSDR GPS L1: https://sdr.ion.org/LimeSDR/LimeSDR_Bands-L1.int16

Expected local paths after download and extraction:

- `CTTC_GPS/2013_04_04_GNSS_SIGNAL_at_CTTC_SPAIN/gnss_pvt.nmea`
- `LimeSDR_GPS/LimeSDR_Bands-L1.int16`

The `.gitignore` intentionally excludes `.nmea`, `.dat`, `.int16`, and archive files so these datasets stay local.

---

## Parser Tests

The NMEA parser lives in `nmea_parser.py`.

Run the test suite with:

```bash
pytest -q
```

Test behavior:

- Unit tests for coordinate conversion and sentence parsing always run.
- Full-file integration tests run only if `CTTC_GPS/2013_04_04_GNSS_SIGNAL_at_CTTC_SPAIN/gnss_pvt.nmea` exists locally.
- If that file is missing, pytest skips the integration tests with a clear message instead of failing.

---

## Repository Notes

- Large raw GNSS data files are local-only dependencies.
- Generated Python cache files should not be committed.

## GitLab Reference

For the standard GitLab starter README/checklist, see:

- https://docs.gitlab.com/user/project/repository/files/gitlab_readme/

## External Clock Progress

We also began testing an external 10 MHz clock reference for the LimeSDR setup. The goal is to improve clock stability during GNSS-SDR runs, since frequency drift can make GPS acquisition, tracking, and navigation decoding less reliable.

For this setup, we used a Silicon Labs / Skyworks Si5386A clock generator board configured through ClockBuilder Pro. The board was configured to provide a 10 MHz reference output for the LimeSDR. This gives us a way to test whether a cleaner external clock improves LimeSDR GNSS performance compared to relying only on the LimeSDR’s onboard clock.

The main outcome is that the external clock generator board is now connected and usable again, so we can include external-clock testing in our GNSS-SDR experiment workflow. This gives us another variable to compare alongside antenna placement, gain settings, filtering, and assisted-GNSS ephemeris data.

Reference documentation for the LimeSDR-USB hardware is here:

```text
https://wiki.myriadrf.org/LimeSDR-USB_hardware_description
