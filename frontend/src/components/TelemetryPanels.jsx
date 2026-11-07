import { signalColor, clockLabel, timeline } from "../lib/telemetry.js";
export function SkyPlot({ satellites, selected, onSelect }) {
  return (
    <svg
      viewBox="0 0 260 250"
      className="skyplot"
      role="img"
      aria-label="Satellite sky plot; choose satellites from the list"
    >
      {[32, 64, 96].map((r) => (
        <circle
          key={r}
          cx="130"
          cy="125"
          r={r}
          fill="none"
          stroke="var(--chart-grid)"
          strokeDasharray="3 5"
        />
      ))}
      <path d="M130 29V221 M34 125H226" stroke="var(--chart-grid)" />
      {[
        [130, 16, "N"],
        [242, 129, "E"],
        [130, 242, "S"],
        [18, 129, "W"],
      ].map(([x, y, t]) => (
        <text
          key={t}
          x={x}
          y={y}
          textAnchor="middle"
          fill="var(--muted)"
          fontSize="10"
        >
          {t}
        </text>
      ))}
      <circle cx="130" cy="125" r="2" fill="#83dec5" />
      {Object.values(satellites)
        .filter((s) => s.azimuth != null && s.elevation != null)
        .map((sat) => {
          const a = ((sat.azimuth - 90) * Math.PI) / 180,
            r = (1 - sat.elevation / 90) * 96,
            x = 130 + Math.cos(a) * r,
            y = 125 + Math.sin(a) * r;
          return (
            <g
              key={sat.prn}
              onClick={() => onSelect(sat.prn)}
              style={{ cursor: "pointer" }}
            >
              <circle
                cx={x}
                cy={y}
                r={selected === sat.prn ? 13 : 10}
                fill={signalColor(sat)}
                fillOpacity={0.12}
                stroke={signalColor(sat)}
              />
              <text
                x={x}
                y={y + 3}
                textAnchor="middle"
                fill={signalColor(sat)}
                fontSize="8"
              >
                {sat.prn}
              </text>
            </g>
          );
        })}
    </svg>
  );
}
export function SignalBars({ satellites, selected, onSelect }) {
  const sats = Object.values(satellites).sort((a, b) => a.prn - b.prn);
  return (
    <div className="signal-list">
      {sats.length ? (
        sats.map((sat) => (
          <button
            className={`signal-row ${selected === sat.prn ? "active" : ""}`}
            key={sat.prn}
            onClick={() => onSelect(sat.prn)}
          >
            <span className="mono">G{String(sat.prn).padStart(2, "0")}</span>
            <span className="bar-track">
              <span
                style={{
                  width: `${Math.min(100, Math.max(0, ((sat.cn0 || 0) / 60) * 100))}%`,
                  background: signalColor(sat),
                }}
              />
            </span>
            <span className="mono">{sat.cn0?.toFixed(1) ?? "—"}</span>
          </button>
        ))
      ) : (
        <p className="muted empty-copy">No satellite observations available.</p>
      )}
    </div>
  );
}
export function HistoryChart({ history, selected }) {
  const entries = Object.entries(history).filter(
    ([key]) => !selected || Number(key) === selected,
  );
  const stamps = timeline({
    positions: [],
    history: Object.fromEntries(entries),
  });
  if (!entries.length)
    return <p className="empty-copy muted">No signal history available.</p>;
  return (
    <div className="history-chart">
      <svg
        viewBox="0 0 800 280"
        role="img"
        aria-label="Signal strength history in dB-Hz"
      >
        {[0, 15, 30, 45, 60].map((v) => (
          <g key={v}>
            <line
              x1="38"
              y1={240 - v * 3.5}
              x2="780"
              y2={240 - v * 3.5}
              stroke="var(--chart-grid)"
              strokeDasharray="3 5"
            />
            <text
              x="24"
              y={244 - v * 3.5}
              textAnchor="end"
              fill="var(--muted)"
              fontSize="10"
            >
              {v}
            </text>
          </g>
        ))}
        {entries.map(([key, points], i) => (
          <polyline
            key={key}
            fill="none"
            stroke={["#83dec5", "#e9b86c", "#9baef1", "#f17c6c"][i % 4]}
            strokeWidth="2"
            points={points
              .filter((p) => p.cn0 != null)
              .map(
                (p) =>
                  `${38 + (stamps.indexOf(p.t) / Math.max(1, stamps.length - 1)) * 742},${240 - p.cn0 * 3.5}`,
              )
              .join(" ")}
          />
        ))}
        <text x="38" y="270" fill="var(--muted)" fontSize="11">
          {clockLabel(stamps[0])} UTC
        </text>
        <text
          x="780"
          y="270"
          textAnchor="end"
          fill="var(--muted)"
          fontSize="11"
        >
          {clockLabel(stamps.at(-1))} UTC
        </text>
      </svg>
      <div className="chart-legend">
        {entries.map(([key], i) => (
          <span key={key}>
            <i
              style={{
                background: ["#83dec5", "#e9b86c", "#9baef1", "#f17c6c"][i % 4],
              }}
            />
            G{String(key).padStart(2, "0")}
          </span>
        ))}
      </div>
    </div>
  );
}
