# Repository structure

Run the commands below from the repository root. Frontend commands run inside `frontend/`.

```text
.
├── README.md
├── .gitignore
├── .gitlab-ci.yml
├── pytest.ini                     # Test discovery and root Python import path
├── gnss_sdr/                      # Reusable Python library
│   ├── __init__.py
│   ├── nmea_parser.py              # GGA/GSV parsing
│   ├── map_aid.py                  # Building masks and specular reflections
│   └── kaggle_adapter.py          # Google Smartphone Decimeter Challenge adapter
├── server/
│   ├── __init__.py
│   ├── main.py                     # FastAPI application
│   ├── requirements.txt
│   └── README.md
├── tools/
│   ├── __init__.py
│   ├── benchmark_gnss_sdr.py
│   ├── validate_multipath.py
│   └── README.md
├── tests/                          # Python tests
├── data/
│   ├── README.md
│   ├── CTTC_GPS/                   # Reference outputs/config plus local raw data
│   └── LimeSDR_GPS/                # Receiver config plus local raw data
├── frontend/
│   ├── src/                        # App, components, hooks, lib helpers, styles
│   ├── public/                     # Runtime Earth texture and asset attribution
│   ├── reference/                  # Optional GLB model, not bundled by Vite
│   ├── index.html
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.js
│   └── README.md
└── docs/
    ├── README.md
    ├── STRUCTURE.md
    └── gnss_sdr_experiments/        # Preserved experiment archive
        ├── configs_used/
        ├── scripts_used/
        ├── results/
        ├── old_handoffs/
        └── *.md
```

## Code boundaries

- `gnss_sdr/` contains importable parsing and analysis code. Import with `from gnss_sdr.nmea_parser import parse_nmea_file`, for example.
- `server/` exposes the application. Start it with `uvicorn server.main:app --reload`.
- `tools/` contains standalone workflows that reuse the library. Invoke them with `python -m tools.benchmark_gnss_sdr` and `python -m tools.validate_multipath`.
- `frontend/` owns browser UI and its own package dependencies. Its data/geometry tests live beside those helpers in `frontend/src/lib/`.
- `tests/` owns Python tests. `pytest.ini` adds the repository root to the import path, so source/test files do not need `sys.path` patches.

## File moves

| Previous location | Current location |
| --- | --- |
| `nmea_parser.py` | `gnss_sdr/nmea_parser.py` |
| `map_aid.py` | `gnss_sdr/map_aid.py` |
| `kaggle_adapter.py` | `gnss_sdr/kaggle_adapter.py` |
| `benchmark_gnss_sdr.py` | `tools/benchmark_gnss_sdr.py` |
| `validate_multipath.py` | `tools/validate_multipath.py` |
| `CTTC_GPS/` | `data/CTTC_GPS/` |
| `LimeSDR_GPS/` | `data/LimeSDR_GPS/` |
| `frontend/satellite.glb` | `frontend/reference/satellite.glb` |
| Root `conftest.py` import-path shim | `pythonpath = .` in `pytest.ini` |

Update external Python imports to use the `gnss_sdr` package and analysis commands to use `python -m tools.<name>`. Move any local ignored dataset files into the matching `data/` subdirectory. The recorded NMEA filename is listed in [data setup](../data/README.md); `gnss_pvt.nmea` at the root remains the live receiver output.

## Generated and historical files

`frontend/dist/`, `node_modules/`, `.venv/`, caches, downloaded raw recordings, and local `outputs/` are ignored. Use `outputs/` for newly generated benchmark/validation reports when supplying output flags.

The experiment archive is grouped by artifact type and keeps its existing relative paths. Its historical machine paths, config snapshots, recorded logs, and dated findings describe the runs that produced them; they are not generic setup instructions for a new checkout. Start current setup from the root README, data guide, and server guide.
