#!/usr/bin/env bash
# run_doppler_aided.sh - end-to-end Doppler-aided LimeSDR GNSS-SDR run.
#
# 1. Refresh F9T ephemeris (XML)
# 2. Compute current per-PRN Doppler
# 3. Patch base config -> lime_doppler_aided.conf
# 4. Lock LimeSDR 10 MHz external reference
# 5. Launch gnss-sdr, logging to a fresh run dir
#
# Override BASE / OUT / LIME_SERIAL via env if needed.

set -euo pipefail

BASE=${BASE:-$HOME/gnss/configs/lime_diagnostic_clean.conf}
OUT=${OUT:-$HOME/gnss/configs/lime_doppler_aided.conf}
LIME_SERIAL=${LIME_SERIAL:-0009061C01502715}
RUN_DIR=$HOME/gnss/runs/doppler_$(date +%Y%m%d_%H%M%S)

mkdir -p "$RUN_DIR"

if pgrep -a gnss-sdr >/dev/null; then
    echo "ERR: gnss-sdr already running"; pgrep -a gnss-sdr; exit 1
fi

echo "[1/5] Refresh F9T ephemeris..."
python3 "$HOME/gnss/scripts/enable_f9t_ubx_uart1.py"
"$HOME/gnss/scripts/refresh_f9t_xml_local.sh" 300
cp "$HOME/gnss/assist/f9t_tcp_latest/gps_ephemeris.xml" "$HOME/gnss/assist/gps_ephemeris.xml"

echo "[2/5] Compute per-PRN Doppler..."
python3 "$HOME/gnss/scripts/compute_doppler.py" | tee "$RUN_DIR/doppler_table.txt"

echo "[3/5] Patch config..."
python3 "$HOME/gnss/scripts/compute_doppler.py" \
    --patch "$BASE" --out "$OUT" --snippet > "$RUN_DIR/snippet.conf"
cp "$OUT" "$RUN_DIR/config_used.conf"
echo "  -> $OUT"

echo "[4/5] Lock LimeSDR 10 MHz external reference..."
LimeUtil --refclk="serial=$LIME_SERIAL" --fref=10000000

echo "[5/5] Launch gnss-sdr in tmux session 'gps_doppler'..."
tmux kill-session -t gps_doppler 2>/dev/null || true
tmux new-session -d -s gps_doppler \
    "gnss-sdr --config_file='$OUT' 2>&1 | tee '$RUN_DIR/run.log'"
tmux pipe-pane -t gps_doppler -o "cat >> '$RUN_DIR/tmux.log'"

echo ""
echo "Run dir: $RUN_DIR"
echo "Attach:  tmux attach -t gps_doppler"
echo "Tail:    tail -f $RUN_DIR/run.log"
echo ""
echo "Watch for: 'tracking bit synchronization locked'"
