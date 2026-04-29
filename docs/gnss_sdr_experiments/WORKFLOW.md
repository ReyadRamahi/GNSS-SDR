# GNSS-SDR Workflow

## Purpose

This is the current operator workflow for the GNSS-SDR GPS L1 C/A experiments. The active path is:

```text
local F9T on hft02
→ refresh assistance XML
→ load XML into GNSS-SDR
→ run LimeSDR-USB on GPS L1 C/A
→ watch acquisition, tracking, bit sync, NAV decode, and fix
```

The older `hft09` TCP F9T path is kept only as a reference workflow now.

## Step 1: Refresh Local F9T XML

Current helper scripts:

- `scripts_used/f9t_lime_current/enable_f9t_ubx_uart1.py`
- `scripts_used/f9t_lime_current/refresh_f9t_xml_local.sh`
- `scripts_used/f9t_lime_current/start_f9t_refresh_local_tmux.sh`

Typical long refresh:

```bash
DUR=900
SESSION=f9t_xml_refresh_$(date -u +%Y%m%d_%H%M%S)
tmux new-session -d -s "$SESSION" "/home/rrama28/gnss/scripts/refresh_f9t_xml_local.sh $DUR"
tmux attach -t "$SESSION"
```

Important operational notes:

- the local F9T is on `/dev/ttyUSB0`
- the fix for stale NMEA-only output was enabling UBX on UART1
- `UBX-RXM-SFRBX` is required for ephemeris extraction
- `UBX-RXM-RAWX` is also enabled for raw measurements
- failed refreshes should not overwrite known-good XML

## Step 2: Verify The XML Before Running Lime

**Important:** the current hft02 workflow does not use `/home/rrama28/gnss/assist/f9t_latest/`.
That folder may appear in older docs, but it does not exist in the current runtime directory.

The active/current XML files are usually in:

```bash
/home/rrama28/gnss/assist/

**Important:** always verify against `f9t_latest/`, not `f9t_tcp_latest/`. The TCP path is the old unreliable source. Older configs (pre-2026-04-28) may still point to the wrong directory — check before using them.

Useful checks:

```bash
ls -lh /home/rrama28/gnss/assist/f9t_latest/
grep -o '<count>[0-9]*</count>' /home/rrama28/gnss/assist/gps_ephemeris.xml
grep -o 'G[0-9][0-9]' /home/rrama28/gnss/assist/gps_ephemeris.xml | sort -u
```

Repo-side reference artifacts:

- current local snapshot: `results/assist/f9t_latest/`
- metadata for the current snapshot: `results/assist/f9t_latest/README_CURRENT_XML.txt`
- older TCP reference snapshot: `results/assist/f9t_tcp_reference/`

Good signs:

- XML count is nonzero
- expected PRNs are present
- GNSS-SDR later prints the usual XML-load messages

## Step 3: Pick The Right Config

Most relevant config groups:

- current focused Lime work: `configs_used/f9t_lime_current/`
- older baseline Lime configs: `configs_used/baseline/`
- AGNSS-oriented Lime configs: `configs_used/agnss/`
- RTL reference configs: `configs_used/rtl_reference/`
- sweep config families: `configs_used/sweeps/` and `results/logs/lime_sweeps/`

Current best starting point for new Lime tracking tests:

- `configs_used/f9t_lime_current/lime_gain20_noclockini_ephem_6ch_t26.conf`

Note: the older `t26_clean` config has the wrong XML path (`f9t_tcp_latest/`). Use the `noclockini` version as the new base — it has the correct path and LOAD_CONFIG has been confirmed neutral.

## Step 4: Set Focused PRNs Correctly

When testing only the current ephemeris satellites, all of these settings matter together:

- `Channels_1C.count`
- `Channel.signal`
- `Channels.in_acquisition`
- each `ChannelN.satellite`

Example shape:

```ini
Channels_1C.count=6
Channel.signal=1C
Channels.in_acquisition=6
Channel0.satellite=16
Channel1.satellite=3
Channel2.satellite=9
Channel3.satellite=27
Channel4.satellite=7
Channel5.satellite=8
```

That PRN restriction is now known to work when all four pieces are set together.

## Step 5: Run GNSS-SDR In A Clean Run Folder

Typical pattern:

```bash
RUN_ID=$(date -u +%Y%m%d_%H%M%S)
RUN_DIR=/home/alexgu2/gnss/runs/example_${RUN_ID}
SESSION=example_${RUN_ID}
CONF=/path/to/config.conf

echo "RUN_ID:  $RUN_ID"
echo "RUN_DIR: $RUN_DIR"
echo "SESSION: $SESSION"
echo "CONF:    $CONF"

mkdir -p "$RUN_DIR"
tmux new-session -d -s "$SESSION" "cd '$RUN_DIR' && timeout --signal=INT 30m gnss-sdr --config_file='$CONF'"
tmux pipe-pane -o -t "$SESSION" "cat >> '$RUN_DIR/run.log'"
tmux attach -t "$SESSION"
```

Run rules:

- print all four variables before launching so you have the exact RUN_DIR for monitoring
- keep `SignalSource.dump=false` during position attempts
- use a fresh run directory every time
- do not launch GNSS-SDR from the home directory — it will dump GSDR*, pvt_dat_*, GPX, KML, and NMEA files there

## Step 6: Monitor From A Second SSH Session

Set LOG explicitly using the printed RUN_DIR — do not rely on shell variables from the launch session:

```bash
LOG=/home/alexgu2/gnss/runs/example_YYYYMMDD_HHMMSS/run.log

watch -n 30 "
echo 'receiver time:' && grep -c 'Current receiver time' $LOG
echo 'tracking starts:' && grep -c 'Tracking of GPS' $LOG
echo 'losses of lock:' && grep -c 'Loss of lock' $LOG
echo 'bit sync:' && grep -c 'tracking bit synchronization locked' $LOG
echo 'NAV messages:' && grep -c 'New GPS NAV message received' $LOG
"
```

Early kill guidance:

- if bit sync is still zero at 10 minutes with active tracking starts and losses, the run has enough data — kill it and move to the next experiment
- if tracking starts are zero at 2 minutes, something is wrong — check the log tail for errors

## Step 7: Check The Right Signals In The Log

Useful commands:

```bash
LOG=/path/to/run.log
grep -c "Current receiver time" "$LOG"
grep -c "Tracking of GPS" "$LOG"
grep -c "Loss of lock" "$LOG"
grep -c "tracking bit synchronization locked" "$LOG"
grep -c "New GPS NAV message received" "$LOG"
grep -c "Position at" "$LOG"
grep "Actual RX Gain" "$LOG" | head -3
grep "Tracking of GPS" "$LOG" | sed -E 's/.*PRN ([0-9]+).*/PRN \1/' | sort | uniq -c | sort -nr
```

Interpretation:

- assistance loaded: XML path is working
- receiver time advancing: GNSS-SDR entered live processing
- tracking starts: acquisition is producing candidates
- repeated loss of lock with zero bit sync: current blocker is tracking stability
- bit sync locked: first real breakthrough — let the run continue to full 30 minutes
- NAV messages or a fix: the main Lime problem is finally breaking


## Step 8: Raw IQ Capture And MATLAB Analysis

Use this workflow to bypass GNSS-SDR and analyze what the LimeSDR is actually receiving at the sample level. All scripts and saved figures are in `scripts_used/matlab_analysis/`.

### Capture IQ On hft02

```bash
RUN_ID=$(date -u +%Y%m%d_%H%M%S)
RUN_DIR=/home/alexgu2/gnss/runs/iq_capture_${RUN_ID}
mkdir -p "$RUN_DIR"
cd "$RUN_DIR"
gnss-sdr --config_file=/home/alexgu2/gnss/configs/lime_iq_capture.conf
```

Config: `configs_used/f9t_lime_current/lime_iq_capture.conf`

GNSS-SDR runs for 10 seconds and exits automatically. Output: `lime_iq_capture.dat` (~160 MB, gr_complex, 2 Msps). The 2026-04-29 capture is committed to the repo at `results/IQ_pairs/lime_iq_capture.dat`. Future captures should be downloaded locally — do not commit large `.dat` files.

### Run MATLAB Scripts In Order

Put all four `.m` files and `lime_iq_capture.dat` in the same folder:

| Step | Script | What to do |
| --- | --- | --- |
| 1 | `spectrum.m` | Run as-is. Check DC spike dB above floor and any narrowband spikes inside ±511 kHz. |
| 2 | `prn_correlation.m` | Update `PRNS_TO_TEST` to match current ephemeris PRNs. Note best PRN and its Doppler. |
| 3 | `tracking_sim.m` | Update `PRN` and `DOPPLER_HZ` from step 2 results before running. |
| 4 | `rtl_vs_lime.m` | Requires a separate RTL capture. Run only if RTL `.dat` is available. |

### Saved Figures From 2026-04-29 Analysis

In `scripts_used/matlab_analysis/figures/`:

| Figure | Key finding |
| --- | --- |
| `PowerSpectrum.fig` | Noise floor -102.4 dB, DC spike and -365 kHz interferer both visible inside GPS band |
| `DCSpike.fig` | DC spike 32 dB above noise floor — severe zero-IF contamination |
| `PRNCorrelationMaps.fig` | All 6 PRNs show horizontal stripe pattern — interference corrupting code delay axis |
| `CN0Summary.fig` | G03–G27 C/N₀ range 33.7–37.6 dB-Hz — all marginal, G27 best |
| `TrackingLoopSim.fig` | G27 lock fraction 25.6% — PLL discriminator saturated, loop never achieved coherent lock |

### What To Look For

- DC spike above noise floor: warn at 20 dB, serious at 30+ dB
- Narrowband spikes inside ±511 kHz: interference inside the GPS band
- C/N₀ per PRN: healthy >35 dB-Hz, marginal 28–35, too weak <28
- Correlation maps: should show one sharp bright dot — horizontal stripes mean interference
- Tracking sim lock fraction: >80% healthy, 40–80% marginal, <40% cannot hold lock

## Legacy Reference: Older hft09 TCP Refresh Path

This path is still documented because it produced usable XML once, but it is no longer the main workflow.

Reference artifacts:

- scripts: `scripts_used/f9t_refresh/`
- older XML snapshot: `results/assist/f9t_tcp_reference/`
- failed refresh log: `results/logs/f9t_refresh/refresh_20260426_042603.log`

Important context:

- source was `10.30.200.59:50012`
- it behaved like raw TCP, not proper NTRIP
- `nc` worked better than trying to force `str2str`
- failed captures often stalled or went to zero-byte progress
