#!/usr/bin/env bash
# Default is passive. --run is the explicitly approved live operation.
set -euo pipefail
PROJECT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
RUN_LIVE=false
CAPTURE_SECONDS=30
while [[ $# -gt 0 ]]; do
    case "$1" in
        --run) RUN_LIVE=true; shift ;;
        --seconds)
            [[ $# -ge 2 && ( "$2" == 30 || "$2" == 90 ) ]] || { echo "--seconds must be 30 or 90" >&2; exit 2; }
            CAPTURE_SECONDS=$2
            shift 2
            ;;
        *) echo "Usage: bash scripts/run_rx1h_baseline.sh [--run] [--seconds 30|90]" >&2; exit 2 ;;
    esac
done
if [[ "$RUN_LIVE" == false ]]; then
    exec python3 "$PROJECT_DIR/scripts/capture_rx1h_baseline.py" --seconds "$CAPTURE_SECONDS"
fi

# Refuse to proceed if device ownership cannot be checked or another owner exists.
USB_NODE=/dev/bus/usb/002/007
[[ -c "$USB_NODE" ]] || { echo "Lime USB node absent: recheck bus/device number before running." >&2; exit 1; }
command -v lsof >/dev/null
if pgrep -x gnss-sdr >/dev/null; then
    echo "gnss-sdr is running; do not contend for the SDR." >&2
    exit 1
fi
set +e
OWNERS=$(lsof -t -- "$USB_NODE" 2>&1)
OWNER_STATUS=$?
set -e
if [[ $OWNER_STATUS != 1 || -n "$OWNERS" ]]; then
    echo "USB ownership check found an owner or could not establish availability:" >&2
    echo "$OWNERS" >&2
    exit 1
fi

RUN_DIR=$(mktemp -d "$PROJECT_DIR/runs/rx1h_baseline_$(date -u +%Y%m%d_%H%M%S)_XXXXXX")
mkdir "$RUN_DIR/soapy_root"
cp "$PROJECT_DIR/scripts/capture_rx1h_baseline.py" "$RUN_DIR/capture_used.py"
cp "$PROJECT_DIR/scripts/run_rx1h_baseline.sh" "$RUN_DIR/launch_used.sh"
cp "$PROJECT_DIR/configs/limesdr_focused.conf" "$RUN_DIR/historical_config_current_copy.conf"
df -h "$RUN_DIR" > "$RUN_DIR/disk_space.txt"
FREE_BYTES=$(df -B1 --output=avail "$RUN_DIR" | tail -1 | tr -d ' ')
REQUIRED_BYTES=$(( CAPTURE_SECONDS * 2000000 * 8 + 520000000 ))
[[ "$FREE_BYTES" -ge "$REQUIRED_BYTES" ]] || { echo "At least $REQUIRED_BYTES free bytes are required." >&2; exit 1; }

# This root/path combination was checked with SoapySDRUtil --info: only system
# modules are searched. It changes lookup for this process, not installations.
export SOAPY_SDR_ROOT="$RUN_DIR/soapy_root"
export SOAPY_SDR_PLUGIN_PATH=/usr/lib/x86_64-linux-gnu/SoapySDR/modules0.8
SoapySDRUtil --info > "$RUN_DIR/module_info.txt" 2>&1
echo "Live RX1_H baseline; output: $RUN_DIR"
TIMEOUT_SECONDS=$(( CAPTURE_SECONDS + 30 ))
echo "$CAPTURE_SECONDS s IQ after 1 s discard; timeout $TIMEOUT_SECONDS s plus at most 5 s forced cleanup."
set +e
timeout --signal=INT --kill-after=5s "${TIMEOUT_SECONDS}s" python3 -u "$RUN_DIR/capture_used.py" \
    --run --seconds "$CAPTURE_SECONDS" --output "$RUN_DIR" > "$RUN_DIR/run.log" 2>&1
RUN_STATUS=$?
set -e
echo "$RUN_STATUS" > "$RUN_DIR/exit_status.txt"
cat "$RUN_DIR/run.log"
echo "Results: $RUN_DIR"
exit "$RUN_STATUS"
