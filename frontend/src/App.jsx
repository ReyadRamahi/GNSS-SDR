import { useEffect, useMemo, useState } from "react";
import {
  Globe2,
  LayoutDashboard,
  Radio,
  Layers,
  Crosshair,
  Play,
  Pause,
  RotateCcw,
  ArrowUpRight,
  Activity,
  ChevronDown,
  Satellite,
  Terminal,
  Orbit,
} from "lucide-react";
import FeatureHub from "./components/FeatureHub.jsx";
import CloudStatus from "./components/CloudStatus.jsx";
import useClouds from "./hooks/useClouds.js";
import GlobeScene from "./components/GlobeScene.jsx";
import {
  SkyPlot,
  SignalBars,
  HistoryChart,
} from "./components/TelemetryPanels.jsx";
import useTelemetry from "./hooks/useTelemetry.js";
import usePlayback from "./hooks/usePlayback.js";
import { frameAt, clockLabel, signalColor } from "./lib/telemetry.js";

const tabs = [
  ["home", "Workspace", LayoutDashboard],
  ["overview", "Globe", Globe2],
  ["satellites", "Satellites", Satellite],
  ["skyplot", "Sky plot", Orbit],
  ["signals", "Signals", Activity],
  ["raw", "Raw feed", Terminal],
];
const coordinate = (value, positive, negative) =>
  value == null
    ? "—"
    : `${Math.abs(value).toFixed(5)}° ${value >= 0 ? positive : negative}`;
export default function App() {
  const [demo, setDemo] = useState(
    new URLSearchParams(location.search).get("demo") === "1",
  );
  const { data, status, error } = useTelemetry(demo);
  const live = status === "live";
  const playback = usePlayback(data, live, `${demo}-${live}`);
  const { receiver, satellites } = useMemo(
    () =>
      live
        ? { receiver: data.positions.at(-1), satellites: data.satellites }
        : frameAt(data, playback.stamps, playback.index),
    [data, live, playback.stamps, playback.index],
  );
  const [selection, setSelection] = useState(null);
  const [tab, setTab] = useState("home");
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [tab]);
  const [clouds, setClouds] = useState(true);
  const cloudLayer = useClouds(clouds);
  const [beams, setBeams] = useState(true);
  const [reset, setReset] = useState(0);
  const sats = Object.values(satellites).sort((a, b) => a.prn - b.prn);
  const selected =
    satellites[selection] ||
    sats.find((s) => s.azimuth != null && s.elevation != null) ||
    sats[0];
  const observed = sats.filter((s) => s.cn0 != null);
  const mean = observed.length
    ? observed.reduce((n, s) => n + s.cn0, 0) / observed.length
    : null;
  const timestamp = live
    ? receiver?.timestamp
    : playback.stamps[playback.index];
  return (
    <div className="app-shell">
      <header className="topbar">
        <a
          className="brand"
          href="#"
          onClick={() => setTab("home")}
          aria-label="GNSS workspace"
        >
          <span className="brand-mark">
            <Orbit size={23} />
          </span>
          <strong>
            GNSS<span className="brand-slash"> / </span>
            <span className="brand-sub">Signal Observatory</span>
          </strong>
        </a>
        <div className={`connection ${status}`}>
          <i />
          {
            {
              connecting: "Connecting",
              offline: "Offline",
              replay: "Recording",
              live: "Live receiver",
              demo: "Simulated demo",
            }[status]
          }
        </div>
        <button className="source-button" onClick={() => setDemo((v) => !v)}>
          {demo ? "Connect receiver" : "Explore demo"}
          <ArrowUpRight size={14} />
        </button>
      </header>
      <div className="workspace">
        <nav className="nav-rail" aria-label="Main navigation">
          {tabs.map(([key, label, Icon]) => (
            <button
              key={key}
              className={tab === key ? "active" : ""}
              aria-label={label}
              title={label}
              aria-current={tab === key ? "page" : undefined}
              onClick={() => setTab(key)}
            >
              <Icon size={19} />
              <span>{label}</span>
            </button>
          ))}
          <span className="rail-footer">L1 / C/A</span>
        </nav>
        <main
          className={`main-workspace ${tab === "home" ? "home-workspace" : ""}`}
        >
          {tab !== "home" && (
            <div className="workspace-heading">
              <div>
                <p className="eyebrow">
                  RECEIVER WORKSPACE <span>/</span> GPS L1 C/A
                </p>
                <h1>
                  {tabs.find(([key]) => key === tab)?.[1] === "Globe"
                    ? "Satellite overview"
                    : tabs.find(([key]) => key === tab)?.[1]}
                </h1>
              </div>
              <div className="session-meta">
                <Radio size={14} />
                <span>
                  {demo
                    ? "Demo session"
                    : live
                      ? "Receiver stream"
                      : status === "replay"
                        ? "Recorded session"
                        : "Awaiting data"}
                </span>
              </div>
            </div>
          )}
          {error && (
            <div className="notice" role="status">
              {error}
              <button onClick={() => setDemo(true)}>
                Open demo <ArrowUpRight size={13} />
              </button>
            </div>
          )}
          {demo && (
            <div className="demo-note">
              SIMULATED DATA{" "}
              <span>Interface preview · not a receiver recording</span>
            </div>
          )}
          {tab === "home" ? (
            <FeatureHub
              scene={
                <GlobeScene
                  compact
                  positions={
                    live
                      ? data.positions
                      : data.positions.slice(
                          0,
                          data.positions.indexOf(receiver) + 1,
                        )
                  }
                  {...{ receiver, satellites, beams, reset }}
                  cloudTexture={clouds ? cloudLayer.texture : null}
                  selected={selected?.prn}
                  onSelect={setSelection}
                />
              }
              {...{ satellites, mean, status, clouds, cloudLayer }}
              fixes={data.positions.length}
              selected={selected?.prn}
              onSelect={setSelection}
              onNavigate={setTab}
              onToggleClouds={() => setClouds((v) => !v)}
            />
          ) : (
            <>
              <section
                className={`visual-workspace ${tab !== "overview" ? "alternate" : ""}`}
              >
                <div
                  className="globe-stage"
                  style={{ display: tab === "overview" ? "block" : "none" }}
                >
                  {tab === "overview" && (
                    <GlobeScene
                      cloudTexture={clouds ? cloudLayer.texture : null}
                      positions={
                        live
                          ? data.positions
                          : data.positions.slice(
                              0,
                              data.positions.indexOf(receiver) + 1,
                            )
                      }
                      {...{ receiver, satellites, beams, reset }}
                      selected={selected?.prn}
                      onSelect={setSelection}
                    />
                  )}
                  <div className="globe-caption">
                    <span className="eyebrow">EARTH / SATELLITE GEOMETRY</span>
                    <div>
                      <i className="status-dot" />
                      {sats.length} satellites in view
                    </div>
                  </div>
                  <div className="globe-toolbar">
                    <button
                      title="Reset camera"
                      aria-label="Reset camera"
                      onClick={() => setReset((v) => v + 1)}
                    >
                      <Crosshair size={17} />
                    </button>
                    <button
                      title="Toggle signal beams"
                      aria-label="Toggle signal beams"
                      aria-pressed={beams}
                      className={beams ? "active" : ""}
                      onClick={() => setBeams((v) => !v)}
                    >
                      <Layers size={17} />
                    </button>
                  </div>
                  <div className="globe-cloud-controls">
                    <CloudStatus
                      enabled={clouds}
                      layer={cloudLayer}
                      onToggle={() => setClouds((v) => !v)}
                    />
                  </div>
                  <div className="globe-footnote">
                    <span>Drag to orbit · Scroll to zoom</span>
                    <span>Satellite distances compressed for display</span>
                  </div>
                </div>
                {tab !== "overview" && (
                  <div className="expanded-panel">
                    <div className="section-heading">
                      <h2>
                        {tab === "satellites"
                          ? "Signal history"
                          : tab === "raw"
                            ? "NMEA stream"
                            : tab === "signals"
                              ? "Carrier-to-noise density"
                              : "Sky visibility"}
                      </h2>
                      {tab === "satellites" && (
                        <button
                          className="text-button"
                          onClick={() => setSelection(null)}
                        >
                          All satellites
                        </button>
                      )}
                    </div>
                    {tab === "satellites" && (
                      <HistoryChart
                        history={data.history}
                        selected={selection}
                      />
                    )}
                    {tab === "signals" && (
                      <>
                        <div className="bar-labels">
                          <span>Satellite</span>
                          <span>CN₀ · dB-Hz</span>
                        </div>
                        <SignalBars
                          {...{ satellites }}
                          selected={selected?.prn}
                          onSelect={setSelection}
                        />
                        <p className="muted">
                          Display scale: 0–60 dB-Hz. Color indicates signal
                          level or an available propagation classification.
                        </p>
                      </>
                    )}
                    {tab === "skyplot" && (
                      <SkyPlot
                        {...{ satellites }}
                        selected={selected?.prn}
                        onSelect={setSelection}
                      />
                    )}
                    {tab === "raw" && (
                      <>
                        <p className="muted">
                          Last 50 sentences ·{" "}
                          {live ? "live stream" : "recording snapshot"}
                        </p>
                        <pre className="raw-feed">
                          {data.raw.length
                            ? data.raw.join("\n")
                            : "Waiting for NMEA sentences…"}
                        </pre>
                      </>
                    )}
                  </div>
                )}
                <aside className="inspector">
                  <div className="inspector-top">
                    <span className="eyebrow">SIGNAL INTELLIGENCE</span>
                    <Activity size={16} />
                  </div>
                  <div className="summary-stats">
                    <div>
                      <span>Satellites observed</span>
                      <strong>{sats.length.toString().padStart(2, "0")}</strong>
                    </div>
                    <div>
                      <span>Mean CN₀</span>
                      <strong>
                        {mean?.toFixed(1) ?? "—"}
                        <small>dB-Hz</small>
                      </strong>
                    </div>
                  </div>
                  <div className="section-heading">
                    <h2>Constellation</h2>
                    <span className="muted">GPS</span>
                  </div>
                  <div className="bar-labels">
                    <span>Satellite</span>
                    <span>CN₀ · dB-Hz</span>
                  </div>
                  <SignalBars
                    {...{ satellites }}
                    selected={selected?.prn}
                    onSelect={setSelection}
                  />
                  <div className="selected-satellite">
                    <div className="section-heading">
                      <h2>
                        {selected
                          ? `GPS ${String(selected.prn).padStart(2, "0")}`
                          : "Select a satellite"}
                      </h2>
                      <i
                        className="status-dot"
                        style={{
                          background: selected
                            ? signalColor(selected)
                            : "#748793",
                        }}
                      />
                    </div>
                    <dl>
                      <div>
                        <dt>Elevation</dt>
                        <dd>
                          {selected?.elevation == null
                            ? "—"
                            : `${selected.elevation.toFixed(0)}°`}
                        </dd>
                      </div>
                      <div>
                        <dt>Azimuth</dt>
                        <dd>
                          {selected?.azimuth == null
                            ? "—"
                            : `${selected.azimuth.toFixed(0)}°`}
                        </dd>
                      </div>
                    </dl>
                    {selected?.predicted_los === false && (
                      <p className="muted">Predicted non-line-of-sight</p>
                    )}
                    {selected?.has_reflection && (
                      <p className="muted">Multipath reflection detected</p>
                    )}
                  </div>
                  <details className="sky-details">
                    <summary>
                      Sky plot <ChevronDown size={14} />
                    </summary>
                    <SkyPlot
                      {...{ satellites }}
                      selected={selected?.prn}
                      onSelect={setSelection}
                    />
                  </details>
                </aside>
              </section>
              <section
                className="playback-dock"
                aria-label="Recording playback"
              >
                <button
                  className="play-button"
                  aria-label={
                    playback.playing ? "Pause playback" : "Play recording"
                  }
                  disabled={live || !playback.duration}
                  onClick={() => playback.setPlaying((v) => !v)}
                >
                  {playback.playing && !live ? (
                    <Pause size={17} />
                  ) : (
                    <Play size={17} />
                  )}
                </button>
                <div className="playback-time">
                  <strong className="mono">
                    {clockLabel(timestamp)}
                    <small>UTC</small>
                  </strong>
                  <span>
                    {live
                      ? "Live receiver"
                      : demo
                        ? "Demo playback"
                        : "Recording playback"}
                  </span>
                </div>
                <div className="scrubber-wrap">
                  <input
                    aria-label="Playback position"
                    type="range"
                    min="0"
                    max={playback.duration || 1}
                    step="0.1"
                    value={
                      live
                        ? playback.duration
                        : Math.min(playback.cursor, playback.duration)
                    }
                    disabled={live || !playback.duration}
                    onChange={(e) => playback.seek(Number(e.target.value))}
                  />
                  <div>
                    <span>{clockLabel(playback.stamps[0])}</span>
                    <span>{clockLabel(playback.stamps.at(-1))}</span>
                  </div>
                </div>
                <label className="speed-select">
                  <span className="sr-only">Playback speed</span>
                  <select
                    value={playback.speed}
                    onChange={(e) => playback.setSpeed(Number(e.target.value))}
                    disabled={live}
                  >
                    {[0.5, 1, 2, 5, 10].map((v) => (
                      <option key={v} value={v}>
                        {v}×
                      </option>
                    ))}
                  </select>
                </label>
                <button
                  className="icon-button"
                  aria-label="Restart recording"
                  disabled={live || !playback.duration}
                  onClick={() => playback.seek(0)}
                >
                  <RotateCcw size={15} />
                </button>
              </section>
            </>
          )}
          <footer className="receiver-strip">
            <span>
              <i
                className={`status-dot ${receiver?.fix_quality ? "" : "dim"}`}
              />
              {receiver?.fix_quality ? "Position fix" : "No position fix"}
            </span>
            <span className="mono">
              {coordinate(receiver?.latitude, "N", "S")} <b>/</b>{" "}
              {coordinate(receiver?.longitude, "E", "W")}
            </span>
            <span className="mono">
              ALT {receiver?.altitude?.toFixed(1) ?? "—"} m
            </span>
            <span className="record-count">
              {data.positions.length.toLocaleString()} fixes
            </span>
          </footer>
        </main>
      </div>
    </div>
  );
}
