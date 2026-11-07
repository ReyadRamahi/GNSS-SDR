import { Cloud, CloudOff } from "lucide-react";
export default function CloudStatus({
  enabled,
  onToggle,
  layer,
  compact = false,
}) {
  const available = layer.status === "ready" || layer.status === "cached";
  const time = layer.retrievedAt?.toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
  });
  return (
    <div className={`cloud-status ${compact ? "compact" : ""}`}>
      <button
        className={enabled ? "on" : ""}
        onClick={onToggle}
        role="switch"
        aria-checked={enabled}
        aria-label="Cloud layer"
      >
        {enabled ? <Cloud size={14} /> : <CloudOff size={14} />}
        <span>{enabled ? "Clouds on" : "Clouds off"}</span>
        <i className={`cloud-indicator ${layer.status}`} />
      </button>
      {enabled && (
        <div className="cloud-meta" role="status">
          {layer.status === "loading"
            ? "Loading satellite clouds…"
            : layer.status === "unavailable"
              ? "Cloud feed unavailable · globe remains usable"
              : `${layer.status === "cached" ? "Cached · refresh failed · " : ""}Retrieved ${time} UTC · source updates ~3h`}
          {!compact && (
            <span>
              Current composite, independent of receiver replay. Observation
              timestamp unavailable.
            </span>
          )}
        </div>
      )}
      {enabled && available && (
        <a
          className="cloud-attribution"
          href="https://github.com/matteason/live-cloud-maps"
          target="_blank"
          rel="noreferrer"
        >
          Contains modified EUMETSAT data · Live Cloud Maps
        </a>
      )}
    </div>
  );
}
