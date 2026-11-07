import {
  ArrowUpRight,
  Cloud,
  Globe2,
  Satellite,
  Orbit,
  Activity,
  Terminal,
} from "lucide-react";
import { SkyPlot, SignalBars } from "./TelemetryPanels.jsx";
import CloudStatus from "./CloudStatus.jsx";
const features = [
  [
    "overview",
    "Globe & clouds",
    "Orbit Earth, follow satellites, and inspect current cloud cover.",
    Globe2,
    "teal",
  ],
  [
    "satellites",
    "Satellite history",
    "Compare carrier-to-noise readings across your recording.",
    Satellite,
    "blue",
  ],
  [
    "skyplot",
    "Sky visibility",
    "See satellite azimuth and elevation around the receiver.",
    Orbit,
    "violet",
  ],
  [
    "signals",
    "Signal strength",
    "Inspect current CN₀ levels for every satellite.",
    Activity,
    "amber",
  ],
  [
    "raw",
    "NMEA feed",
    "Read the latest receiver sentences as they arrive.",
    Terminal,
    "slate",
  ],
];
export default function FeatureHub({
  scene,
  satellites,
  selected,
  onSelect,
  onNavigate,
  clouds,
  cloudLayer,
  onToggleClouds,
  mean,
  fixes,
}) {
  return (
    <section className="feature-hub" aria-label="Feature overview">
      <div className="hub-content">
        <div className="hub-intro">
          <div>
            <p className="eyebrow">RECEIVER WORKSPACE / GPS L1 C/A</p>
            <h1>Workspace overview</h1>
            <p className="hub-description">
              Check the receiver, then open a tool to explore.
            </p>
          </div>
          <div className="hub-counters">
            <div>
              <strong>
                {Object.keys(satellites).length.toString().padStart(2, "0")}
              </strong>
              <span>satellites</span>
            </div>
            <div>
              <strong>
                {mean?.toFixed(1) ?? "—"}
                <small>dB-Hz</small>
              </strong>
              <span>mean CN₀</span>
            </div>
            <div>
              <strong>{fixes.toLocaleString()}</strong>
              <span>position fixes</span>
            </div>
          </div>
        </div>
        <div className="hub-preview-grid">
          <section className="hub-globe">
            <div className="hub-panel-heading">
              <h2>
                <Globe2 size={14} />
                Globe & atmosphere
              </h2>
              <button
                onClick={() => onNavigate("overview")}
                aria-label="Expand globe"
              >
                <ArrowUpRight size={15} />
              </button>
            </div>
            <div className="hub-scene">{scene}</div>
            <CloudStatus
              enabled={clouds}
              onToggle={onToggleClouds}
              layer={cloudLayer}
              compact
            />
          </section>
          <section className="hub-sky">
            <div className="hub-panel-heading">
              <h2>
                <Orbit size={14} />
                Sky visibility
              </h2>
              <button
                onClick={() => onNavigate("skyplot")}
                aria-label="Expand sky plot"
              >
                <ArrowUpRight size={15} />
              </button>
            </div>
            <SkyPlot {...{ satellites, selected, onSelect }} />
            <div className="hub-panel-foot">
              Azimuth / elevation at receiver
            </div>
          </section>
          <section className="hub-signals">
            <div className="hub-panel-heading">
              <h2>
                <Activity size={14} />
                Signal strength
              </h2>
              <button
                onClick={() => onNavigate("signals")}
                aria-label="Expand signal strength"
              >
                <ArrowUpRight size={15} />
              </button>
            </div>
            <SignalBars {...{ satellites, selected, onSelect }} />
            <div className="hub-panel-foot">
              CN₀ · dB-Hz <span>0 — 60</span>
            </div>
          </section>
        </div>
        <div className="hub-tools-heading">
          <h2>Explore your workspace</h2>
          <span>5 tools</span>
        </div>
        <div className="feature-links">
          {features.map(([id, name, description, Icon, color]) => (
            <button
              key={id}
              className={`feature-link ${color}`}
              onClick={() => onNavigate(id)}
            >
              <div className="feature-icon">
                <Icon size={18} />
              </div>
              <div>
                <strong>{name}</strong>
                <p>{description}</p>
              </div>
              <ArrowUpRight size={14} />
            </button>
          ))}
        </div>
      </div>
      <div className="hub-bottom">
        <span>
          <Cloud size={13} /> Clouds use a current satellite composite;
          telemetry follows your selected session.
        </span>
        <button onClick={() => onNavigate("overview")}>
          Open full globe <ArrowUpRight size={13} />
        </button>
      </div>
    </section>
  );
}
