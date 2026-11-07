# Dashboard server

Run from the repository root:

```bash
python -m pip install -r server/requirements.txt
uvicorn server.main:app --reload
```

The application imports shared models/parsers from `gnss_sdr/`. Data paths are resolved from the checkout location, not from hardcoded user directories.

| Path | Purpose |
| --- | --- |
| `data/CTTC_GPS/2013_04_04_GNSS_SIGNAL_at_CTTC_SPAIN/2013_04_04_GNSS_SIGNAL_at_CTTC_SPAIN.nmea` | Default recorded NMEA input |
| `gnss_pvt.nmea` at the repository root | Live receiver file, tailed and broadcast over WebSocket |
| `frontend/dist/` | Built static frontend; create it with `npm run build` inside `frontend/` |

The API starts without a frontend build; `/` gives build instructions until the build exists and the server restarts. Missing recorded data returns 503 from the affected REST endpoints, while the WebSocket can still accept live receiver data.

## Endpoints

- `GET /api/positions`: recorded position fixes.
- `GET /api/satellites`: latest recorded satellite observations, with building-mask classification when available.
- `GET /api/satellite-history`: recorded per-PRN CN₀ history.
- `GET /api/raw`: last 50 recorded NMEA sentences.
- `GET /api/building_mask`: receiver-area LOS/NLOS classification when ready.
- `WS /ws`: new sentences appended to the live receiver file.

Vite's development server forwards `/api/*` and `/ws` to port 8000. See [the project README](../README.md) for the two-terminal workflow and production build, [dataset setup](../data/README.md) for inputs, and [the repository map](../docs/STRUCTURE.md) for code locations.
