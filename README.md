# GNSS-SDR Signal Observatory

React + Three.js dashboard and Python analysis tools for GNSS-SDR recordings and live NMEA telemetry. The project includes the IE 421 Group 16 receiver experiments and reference results.

## Repository layout

```text
frontend/       React app, globe, charts, and browser data hooks
server/         FastAPI REST endpoints, WebSocket stream, and dependencies
gnss_sdr/       Shared Python parsers, dataset adapter, and propagation model
tools/          Command-line benchmark and multipath validation tools
tests/          Python unit and integration tests
data/           CTTC/LimeSDR reference files and local dataset locations
docs/           Repository guide and GNSS-SDR experiment archive
```

See [the repository map](docs/STRUCTURE.md) for the detailed tree, file moves, and path conventions. Start with [the documentation index](docs/README.md) or [the frontend learning guide](frontend/README.md).

## Requirements

- Python 3.10+ for the server and analysis tools.
- Node.js 20.19+ or 22.12+ for the Vite 7 frontend.
- GNSS-SDR and receiver hardware are needed only for actual receiver runs; the frontend has an explicitly labeled simulated demo.

Run Python commands from the repository root, where this README lives.

## Local development

Install the backend dependencies in a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r server/requirements.txt
uvicorn server.main:app --reload
```

On Windows, activate with `.venv\Scripts\activate` instead.

In another terminal:

```bash
cd frontend
npm ci
npm run dev
```

Open [http://127.0.0.1:5173](http://127.0.0.1:5173). Vite forwards `/api/*` and `/ws` to FastAPI on port 8000. Choose **Explore demo** to use simulated data without a recording.

For a production build served entirely by FastAPI:

```bash
cd frontend
npm ci
npm run build
cd ..
uvicorn server.main:app
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000). FastAPI serves `frontend/dist/`; restart the server after the first build. The API can run and be tested before building the frontend.

## Recordings and live data

The large raw files are local downloads, excluded from Git. See [data setup](data/README.md) for download links and the exact expected paths.

- Replay NMEA: `data/CTTC_GPS/2013_04_04_GNSS_SIGNAL_at_CTTC_SPAIN/2013_04_04_GNSS_SIGNAL_at_CTTC_SPAIN.nmea`.
- Live NMEA: `gnss_pvt.nmea` at the repository root, matching the receiver configs' output path. The backend tails this file and broadcasts new sentences on `/ws`.
- Original LimeSDR IQ data: `data/LimeSDR_GPS/LimeSDR_Bands-L1.int16`.

The default CTTC and LimeSDR file-source configs use repository-relative input paths. Launch those GNSS-SDR configs from the repository root. The dated experiment archive also contains historical configs for specific machines; consult its workflow notes before running them.

## Dashboard behavior

The app opens to a full-page overview with a globe, sky plot, signal summary, and shortcuts to all tools. Opening a tool reveals the sidebar; the header can show or hide it. The light/dark toggle remembers your choice. Both themes give the globe a subtle star-and-nebula background.

Features include satellite selection, CN₀ bars and history, sky visibility, raw NMEA, receiver track, camera reset, beam/cloud visibility, and timestamp-based replay with speed controls. Valid incoming GGA/GSV sentences switch the frontend to live mode; an idle WebSocket alone does not. Replay polling resumes after six seconds without valid telemetry. The raw feed is the latest 50-sentence snapshot.

Satellite positions are schematic azimuth/elevation projections at a compressed 3,500 km distance, not ephemeris-derived orbits. Replay CN₀ uses recorded samples, while geometry uses the latest angles exposed by the API.

Clouds use the public Live Cloud Maps feed, with modified EUMETSAT data. The app checks every 30 minutes; the source publishes about every three hours. Retrieval time is shown because observation time is unavailable. Clouds represent current weather context, independent of receiver replay. Source details and attribution are in [the asset notes](frontend/public/ASSETS.md).

## Analysis tools

Both tools run as Python modules from the repository root:

```bash
python -m tools.benchmark_gnss_sdr --help
python -m tools.validate_multipath --help
```

See [the tools guide](tools/README.md) for examples and inputs. Shared code lives in `gnss_sdr/`, including the NMEA parser, building-mask/multipath model, and Kaggle dataset adapter.

## Tests

```bash
python -m pip install -r server/requirements.txt pytest
python -m pytest -q
```

Python tests live in `tests/`. Dataset integration tests skip when the replay recording is unavailable; parser/model tests use synthetic data and mocked network requests.

Frontend data and geometry checks:

```bash
cd frontend
npm ci
npm test
npm run build
```

The existing [GitLab CI configuration](.gitlab-ci.yml) remains available for the original mirror.

## Receiver experiments

[The experiment archive](docs/gnss_sdr_experiments/README.md) contains receiver configuration families, capture/refresh/MATLAB scripts, run logs, assistance data, and handoffs. Start with its [workflow](docs/gnss_sdr_experiments/WORKFLOW.md) and [project summary](docs/gnss_sdr_experiments/GNSS_SDR_PROJECT_SUMMARY.md).

The work includes an external Si5386A 10 MHz reference for LimeSDR clock stability, alongside antenna, gain, filtering, IQ correction, and assisted-GNSS experiments. Historical paths in captured logs refer to the machines used for those runs; the current checkout layout is documented in [STRUCTURE.md](docs/STRUCTURE.md).
