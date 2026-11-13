#!/usr/bin/env bash
# Replay 2 Msps CF32 IQ without opening SDR hardware. Optional arg 2: IF in Hz.
set -euo pipefail

if [[ $# -gt 2 ]]; then
    echo "Usage: bash scripts/run_offline_baseline.sh [IQ_FILE [IF_HZ]]" >&2
    exit 2
fi
PROJECT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
IQ_FILE=${1:-"$PROJECT_DIR/iq_captures/lime_l1/lime_baseline_no_10mhz_20260428_044448.dat"}
IF_HZ=${2:-0}
IQ_FILE=$(realpath -- "$IQ_FILE")
if [[ ! -s "$IQ_FILE" ]]; then
    echo "IQ file is missing or empty: $IQ_FILE" >&2
    exit 1
fi
command -v gnss-sdr >/dev/null
RUN_DIR=$(mktemp -d "$PROJECT_DIR/runs/offline_baseline_XXXXXXXX")
mkdir -p "$RUN_DIR/internal"

python3 - "$PROJECT_DIR/configs/lime_offline_baseline.conf" "$IQ_FILE" "$RUN_DIR" "$IF_HZ" <<'PY'
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

template, iq_file, run_dir = map(Path, sys.argv[1:4])
try:
    intermediate_frequency = int(sys.argv[4])
except ValueError:
    raise SystemExit("IF_HZ must be an integer frequency in Hz")
if abs(intermediate_frequency) >= 1000000:
    raise SystemExit("IF_HZ must lie strictly between -1000000 and +1000000 at 2 Msps")
size = iq_file.stat().st_size
if size % 8:
    raise SystemExit("IQ size must be a multiple of 8 bytes for CF32 samples")
text = template.read_text()
lines = text.splitlines()
lines = ["SignalSource.filename=" + str(iq_file) if line.startswith("SignalSource.filename=") else line for line in lines]
lines = [f"InputFilter.IF={intermediate_frequency}" if line.startswith("InputFilter.IF=") else line for line in lines]
(run_dir / "config_used.conf").write_text("\n".join(lines) + "\n")
(run_dir / "metadata.json").write_text(json.dumps({
    "started_utc": datetime.now(timezone.utc).isoformat(),
    "iq_file": str(iq_file), "iq_bytes": size,
    "assumed_sample_rate_sps": 2000000,
    "assumed_center_frequency_hz": 1575420000 - intermediate_frequency,
    "input_filter_if_hz": intermediate_frequency,
    "signal_duration_s": size / 8 / 2000000,
    "note": "RF metadata assumptions must match the capture; file has no embedded RF metadata."
}, indent=2) + "\n")
PY

echo "Offline run: $RUN_DIR"
cd -- "$RUN_DIR"
set +e
timeout --signal=INT --kill-after=10s 180s gnss-sdr \
    --config_file="$RUN_DIR/config_used.conf" --log_dir="$RUN_DIR/internal" \
    > "$RUN_DIR/run.log" 2>&1
RUN_STATUS=$?
set -e

python3 - "$RUN_DIR" "$RUN_STATUS" <<'PY'
import json
import re
import sys
from pathlib import Path

run_dir = Path(sys.argv[1])
log = (run_dir / "run.log").read_text(errors="replace")
internal = "\n".join(p.read_text(errors="replace") for p in (run_dir / "internal").glob("*.INFO.*") if p.is_file() and not p.is_symlink())
times = re.findall(r"Current receiver time: ([^\r\n]+)", log)
summary = {
    "exit_status": int(sys.argv[2]),
    "completed": ("GNSS-SDR program ended." in log and int(sys.argv[2]) == 0
                  and "Unable to connect flowgraph" not in log and bool(times)),
    "last_reported_receiver_time": times[-1] if times else None,
    "tracking_starts": log.count("Tracking of GPS"),
    "lock_losses": log.count("Loss of lock"),
    "bit_sync_events": log.count("tracking bit synchronization locked"),
    "nav_messages": log.count("New GPS NAV message received"),
    "position_messages": log.count("Position at"),
    "positive_acquisitions": internal.count("positive acquisition"),
    "cfar_enabled_seen_in_log": "use_CFAR_algorithm_flag: true" in internal,
    "nmea_bytes": sum(p.stat().st_size for p in run_dir.glob("*.nmea")),
}
(run_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
print("Full results:", run_dir)
if not summary["completed"]:
    raise SystemExit("Replay did not complete; inspect run.log and internal logs.")
PY
exit "$RUN_STATUS"
