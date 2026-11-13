
#!/usr/bin/env bash

set -euo pipefail



WORK_DIR="$HOME/gnss/agnss/magicephem"

OUT_DIR="$HOME/gnss/assist/f9t_tcp_latest"

STAMP=$(date -u +%Y%m%d_%H%MZ)

URL="https://magicgnss.gmv.com/magicephem/GMV.RNX_1D_only_gps"



mkdir -p "$WORK_DIR" "$OUT_DIR"



echo "[$(date -u)] Downloading magicEphem GPS-only RINEX nav..."

wget -q -O "$WORK_DIR/magicephem_${STAMP}.nav" "$URL"



echo "[$(date -u)] Converting to GNSS-SDR XML..."

cd "$WORK_DIR"

rinex2assist "magicephem_${STAMP}.nav"



echo "[$(date -u)] Deploying XMLs to $OUT_DIR..."

cp "$WORK_DIR/gps_ephemeris.xml" "$OUT_DIR/gps_ephemeris.xml"

cp "$WORK_DIR/gps_utc_model.xml" "$OUT_DIR/gps_utc_model.xml"



ls -t "$WORK_DIR"/magicephem_*.nav 2>/dev/null | tail -n +6 | xargs rm -f



echo "[$(date -u)] Done. Ephemeris source: magicEphem (${STAMP})"

ls -lh "$OUT_DIR"

