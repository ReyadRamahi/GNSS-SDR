# Learning React through the signal observatory

This is a React app. Three.js renders the 3D scene, and React Three Fiber lets you describe that scene with JSX. Drei supplies camera controls, lines, and labels. Vite runs development and builds the app. No Cesium or ion token is required.

## Start here

1. `src/main.jsx` mounts the app. StrictMode helps expose effects that do not clean up correctly.
2. `src/App.jsx` composes the workspace. `useState` stores selected satellite, active view, and beam visibility. Props pass these values and event handlers to children.
3. `src/components/TelemetryPanels.jsx` turns data into regular React UI and SVG charts.
4. `src/components/GlobeScene.jsx` describes the Three.js scene. A `<mesh>` combines geometry and material. `useFrame` moves the signal particles without updating React state every frame.
5. `src/hooks/useTelemetry.js` owns polling, WebSocket reconnection, and cleanup. `usePlayback.js` advances playback according to actual timestamp intervals.
6. `src/lib/` contains pure functions for parsing, coordinate conversion, and selecting a replay frame. These can be tested without a browser.
7. `src/styles.css` defines the visual system and responsive layout.

## Commands

- `npm run dev` — development server, backend proxy to port 8000.
- `npm run build` — production files in `dist/`.
- `npm run preview` — preview production files; use the backend-served build for real API data (preview has no proxy).
- `npm test` — data parsing, replay, and geometry checks.

Use **Explore demo**, or `?demo=1`, to explore with explicitly simulated data. **Connect receiver** returns to the real backend. You can run the demo without Python.

## Try these small changes

- Change the accent color in `styles.css`.
- Add a label to a selected satellite in `GlobeScene.jsx`.
- Add a checkbox in `App.jsx` and pass its state to a child component.
- Change the satellite solar panel material to learn how geometry and lighting interact.

## Display conventions

Earth has radius 2 in scene units. `geographic()` maps latitude/longitude to a Y-up sphere. `satellitePosition()` constructs east/north/up vectors at the receiver and projects azimuth/elevation at the original 3,500 km compressed distance. It omits satellites with unknown geometry rather than inventing positions.

Satellite geometry is schematic. The API exposes the latest azimuth/elevation, not an orbit history. CN₀ replay uses only observations available at or before the selected timestamp. Raw NMEA uses the backend's latest snapshot. Propagation classifications are used only when present in the data. Valid live data replaces replay state, and stale telemetry falls back to polling; demo data is never automatic.

## Visual assets

`public/ASSETS.md` records the Earth texture source. Satellite meshes are built from boxes so you can edit them in React. The old `satellite.glb` is retained as a possible future exercise in loading GLTF models.
