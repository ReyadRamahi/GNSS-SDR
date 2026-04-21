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
    └── index.html          # Single-file SPA (vanilla JS, no build step)
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

### Frontend — CDN (no install needed)

All frontend libraries are loaded from public CDNs. No `npm install` or build step required — open `frontend/index.html` via the FastAPI static server.

| Library | Version | CDN | Purpose |
|---|---|---|---|
| **CesiumJS** | 1.117 | `cesium.com/downloads/…` | 3-D globe, satellite entity rendering |
| **D3** | 7 | `cdn.jsdelivr.net/npm/d3@7` | Sky-plot polar chart (SVG) |
| **Chart.js** | 4 | `cdn.jsdelivr.net/npm/chart.js@4` | CN0 bar chart + history line chart |
| **chartjs-plugin-annotation** | 3 | `cdn.jsdelivr.net/npm/chartjs-plugin-annotation@3` | Threshold lines on CN0 chart |

> **Cesium Ion token (optional):** The globe renders without a token using OpenStreetMap tiles. A free token from [cesium.com/ion/tokens](https://cesium.com/ion/tokens) can be pasted into the `CESIUM_ION_TOKEN` constant at the top of `frontend/index.html` to enable Cesium World Imagery.

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
