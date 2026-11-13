#!/bin/bash
# =============================================================================
# gain_sweep.sh — LimeSDR gain sweep
# Based on lime_diagnostic_clean.conf which is confirmed working.
# Sweeps gain/if_gain combinations, runs each for RUN_DURATION seconds,
# scores by tracking quality. Results saved to CSV.
# =============================================================================

RUN_DURATION=180

LIME_SERIAL=0009061C01502715
EPHEMERIS=/home/rrama28/gnss/assist/gps_ephemeris.xml
IONO=/home/rrama28/gnss/assist/gps_iono.xml
UTC_MODEL=/home/rrama28/gnss/assist/gps_utc_model.xml

# Update these to match current visible PRNs from fresh ephemeris
PRNS=(31 26 1 10 16)

# Gain ranges — covers ~43 dB to 61 dB actual
# Based on empirical mapping:
#   gain=6,  if_gain=0  → ~18 dB
#   gain=10, if_gain=0  → ~22 dB
#   gain=10, if_gain=12 → ~39 dB
#   gain=15, if_gain=0  → ~27 dB
#   gain=15, if_gain=12 → ~51 dB
#   gain=20, if_gain=0  → ~58 dB
#   gain=20, if_gain=12 → ~61 dB (max)
GAIN_VALUES=(10 12 15 18 20)
IF_GAIN_VALUES=(0 3 6 9 12)

SWEEP_DIR=/home/rrama28/gnss/runs/gain_sweep_$(date -u +%Y%m%d_%H%M%S)
RESULTS_CSV="$SWEEP_DIR/results.csv"

mkdir -p "$SWEEP_DIR"
TOTAL=$(( ${#GAIN_VALUES[@]} * ${#IF_GAIN_VALUES[@]} ))
EST_MIN=$(( TOTAL * RUN_DURATION / 60 ))
N_PRNS=${#PRNS[@]}

echo "============================================================"
echo "GAIN SWEEP — $SWEEP_DIR"
echo "Total combos: $TOTAL  |  Duration: ${RUN_DURATION}s each  |  Est: ${EST_MIN} min"
echo "PRNs: ${PRNS[*]}"
echo "============================================================"

# Lock external clock
echo "=== Locking ADF4002 ==="
for attempt in 1 2 3; do
    LOCK=$(LimeUtil --refclk="serial=$LIME_SERIAL" --fref=10000000 2>&1 | grep "Lock State" || true)
    echo "Attempt $attempt: $LOCK"
    if echo "$LOCK" | grep -q "Lock State: 1"; then
        echo "Locked."
        break
    fi
    sleep 2
done
echo ""

# CSV header
echo "gain,if_gain,actual_rx_gain_db,tracking_starts,losses_of_lock,bit_sync,nav_messages,position_fixes,score" > "$RESULTS_CSV"

COMBO=0
START_TIME=$(date +%s)

for GAIN in "${GAIN_VALUES[@]}"; do
for IF_GAIN in "${IF_GAIN_VALUES[@]}"; do

    COMBO=$(( COMBO + 1 ))
    ELAPSED=$(( $(date +%s) - START_TIME ))
    REMAINING=$(( (TOTAL - COMBO + 1) * RUN_DURATION ))
    COMBO_NAME="g${GAIN}_if${IF_GAIN}"
    COMBO_DIR="$SWEEP_DIR/$COMBO_NAME"
    COMBO_CONF="$COMBO_DIR/run.conf"
    COMBO_LOG="$COMBO_DIR/run.log"
    mkdir -p "$COMBO_DIR"

    echo "============================================"
    echo "Run $COMBO / $TOTAL — $COMBO_NAME"
    echo "Elapsed: ${ELAPSED}s   Remaining: ~${REMAINING}s"
    echo "Started: $(date -u +%H:%M:%S)"
    echo "============================================"

    # Build channel lines
    CHANNEL_LINES=""
    for i in $(seq 0 $(( N_PRNS - 1 ))); do
        CHANNEL_LINES="${CHANNEL_LINES}Channel${i}.satellite=${PRNS[$i]}"$'\n'
    done

    # Write config — based directly on lime_diagnostic_clean.conf structure
    cat > "$COMBO_CONF" << CONF
[GNSS-SDR]

GNSS-SDR.internal_fs_sps=2000000
GNSS-SDR.AGNSS_XML_enabled=true
GNSS-SDR.AGNSS_ref_location=41.880662482,-87.643929543
GNSS-SDR.AGNSS_gps_ephemeris_xml=$EPHEMERIS
GNSS-SDR.AGNSS_gps_iono_xml=$IONO
GNSS-SDR.AGNSS_gps_utc_model_xml=$UTC_MODEL

SignalSource.implementation=Osmosdr_Signal_Source
SignalSource.item_type=gr_complex
SignalSource.sampling_frequency=2000000
SignalSource.freq=1575420000
SignalSource.gain=$GAIN
SignalSource.if_gain=$IF_GAIN
SignalSource.AGC_enabled=false
SignalSource.samples=240000000
SignalSource.repeat=false
SignalSource.enable_throttle_control=false
SignalSource.dump=false
SignalSource.osmosdr_args=soapy=0,driver=lime,serial=$LIME_SERIAL,antenna=LNAW

SignalConditioner.implementation=Signal_Conditioner
DataTypeAdapter.implementation=Pass_Through

InputFilter.implementation=Freq_Xlating_Fir_Filter
InputFilter.input_item_type=gr_complex
InputFilter.output_item_type=gr_complex
InputFilter.taps_item_type=float
InputFilter.number_of_taps=101
InputFilter.number_of_bands=2
InputFilter.band1_begin=0.0
InputFilter.band1_end=0.45
InputFilter.band2_begin=0.55
InputFilter.band2_end=1.0
InputFilter.ampl1_begin=1.0
InputFilter.ampl1_end=1.0
InputFilter.ampl2_begin=0.0
InputFilter.ampl2_end=0.0
InputFilter.band1_error=1.0
InputFilter.band2_error=1.0
InputFilter.filter_type=bandpass
InputFilter.grid_density=16
InputFilter.sampling_frequency=2000000
InputFilter.IF=0
InputFilter.decimation_factor=1
InputFilter.dump=false

Resampler.implementation=Pass_Through

Channels_1C.count=$N_PRNS
Channels.in_acquisition=$N_PRNS
Channel.signal=1C
$CHANNEL_LINES
Acquisition_1C.implementation=GPS_L1_CA_PCPS_Acquisition
Acquisition_1C.item_type=gr_complex
Acquisition_1C.coherent_integration_time_ms=1
Acquisition_1C.threshold=2.6
Acquisition_1C.doppler_max=5000
Acquisition_1C.doppler_step=250
Acquisition_1C.bit_transition_flag=false
Acquisition_1C.max_dwells=2
Acquisition_1C.dump=false

Tracking_1C.implementation=GPS_L1_CA_DLL_PLL_Tracking
Tracking_1C.item_type=gr_complex
Tracking_1C.pll_bw_hz=40.0
Tracking_1C.dll_bw_hz=2.0
Tracking_1C.pll_bw_narrow_hz=2.0
Tracking_1C.dll_bw_narrow_hz=0.25
Tracking_1C.fll_bw_hz=10.0
Tracking_1C.enable_fll_pull_in=true
Tracking_1C.early_late_space_chips=0.5
Tracking_1C.dump=false

TelemetryDecoder_1C.implementation=GPS_L1_CA_Telemetry_Decoder
TelemetryDecoder_1C.dump=false

Observables.implementation=Hybrid_Observables
Observables.dump=false

PVT.implementation=RTKLIB_PVT
PVT.positioning_mode=Single
PVT.iono_model=Broadcast
PVT.trop_model=Saastamoinen
PVT.output_rate_ms=100
PVT.display_rate_ms=500
PVT.elevation_mask=10
PVT.dump=false
PVT.flag_nmea_tty_port=false
PVT.nmea_dump_filename=./sweep.nmea
PVT.flag_rtcm_server=false
PVT.flag_rtcm_tty_port=false
PVT.rinex_version=2
CONF

    cd "$COMBO_DIR"
    gnss-sdr --config_file="$COMBO_CONF" > "$COMBO_LOG" 2>&1 &
    GNSS_PID=$!
    ELAPSED_RUN=0
    while kill -0 $GNSS_PID 2>/dev/null; do
        sleep 1
        ELAPSED_RUN=$(( ELAPSED_RUN + 1 ))
        echo -ne "  Running: ${ELAPSED_RUN}s\r"
    done
    echo ""
    wait $GNSS_PID 2>/dev/null || true
    cd ~

    # Parse metrics
    ACTUAL_GAIN=$(grep "Actual RX Gain" "$COMBO_LOG" 2>/dev/null | head -1 | grep -oE '[0-9]+' | head -1)
    ACTUAL_GAIN=${ACTUAL_GAIN:-0}
    TRACKING_STARTS=$(grep -c "Tracking of GPS" "$COMBO_LOG" 2>/dev/null) || TRACKING_STARTS=0
    LOSSES=$(grep -c "Loss of lock" "$COMBO_LOG" 2>/dev/null) || LOSSES=0
    BIT_SYNC=$(grep -c "tracking bit synchronization locked" "$COMBO_LOG" 2>/dev/null) || BIT_SYNC=0
    NAV_MSGS=$(grep -c "New GPS NAV message received" "$COMBO_LOG" 2>/dev/null) || NAV_MSGS=0
    POS_FIXES=$(grep -c "Position at" "$COMBO_LOG" 2>/dev/null) || POS_FIXES=0
    SCORE=$(( POS_FIXES * 10000 + NAV_MSGS * 1000 + BIT_SYNC * 100 + TRACKING_STARTS - LOSSES ))

    echo "$GAIN,$IF_GAIN,$ACTUAL_GAIN,$TRACKING_STARTS,$LOSSES,$BIT_SYNC,$NAV_MSGS,$POS_FIXES,$SCORE" >> "$RESULTS_CSV"
    echo "  Actual gain: ${ACTUAL_GAIN} dB | Tracking: $TRACKING_STARTS | Losses: $LOSSES | BitSync: $BIT_SYNC | NAV: $NAV_MSGS | Fix: $POS_FIXES | Score: $SCORE"
    echo ""

done
done

echo "============================================================"
echo "SWEEP COMPLETE"
echo "============================================================"
echo ""
echo "Top 10 results:"
(head -1 "$RESULTS_CSV"; tail -n +2 "$RESULTS_CSV" | sort -t, -k9 -nr | head -10) | column -t -s,
echo ""
echo "Results: $RESULTS_CSV"
