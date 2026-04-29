# GNSS-SDR Workflow

## Purpose

This is the current operator workflow for the GNSS-SDR GPS L1 C/A experiments. The active path is:

```text
local F9T on hft02
→ refresh assistance XML
→ copy/verify XML in the active assist folder
→ load XML into GNSS-SDR
→ run LimeSDR-USB on GPS L1 C/A
→ watch acquisition, tracking, bit sync, NAV decode, and fix
```

The older `hft09` TCP F9T path is kept only as a reference workflow now.

## Step 1: Refresh Local F9T XML

Current helper scripts on `hft02`:

- `/home/rrama28/gnss/scripts/enable_f9t_ubx_uart1.py`
- `/home/rrama28/gnss/scripts/refresh_f9t_xml_local.sh`
- `/home/rrama28/gnss/scripts/start_f9t_refresh_local_tmux.sh`

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

**Important:** do not use `/home/rrama28/gnss/assist/f9t_latest/`.

That folder appears in older notes, but it does not exist in the current `hft02` runtime tree.

The local F9T refresh writes generated XML into a run/session folder under:

```text
/home/rrama28/gnss/f9t/assist_runs/
```

The output folder name matches the refresh run format:

```text
hft02_YYYYMMDD_HHMMSS
```

Examples from current `hft02`:

```text
/home/rrama28/gnss/f9t/assist_runs/hft02_20260428_040552/
/home/rrama28/gnss/f9t/assist_runs/hft02_20260428_070133/
/home/rrama28/gnss/f9t/assist_runs/hft02_20260429_071857/
```

GNSS-SDR configs usually read from the active assist folder:

```text
/home/rrama28/gnss/assist/gps_ephemeris.xml
/home/rrama28/gnss/assist/gps_iono.xml
/home/rrama28/gnss/assist/gps_utc_model.xml
```

So the correct workflow is:

```text
run F9T refresh
→ find the generated hft02_* output folder for that refresh
→ verify its XML count and PRNs
→ copy that XML into /home/rrama28/gnss/assist/
→ verify /home/rrama28/gnss/assist/
→ run Lime
```

### Find F9T Refresh Output Folders

List the newest generated refresh folders first:

```bash
ls -lht /home/rrama28/gnss/f9t/assist_runs/
```

Or show every generated ephemeris XML:

```bash
find /home/rrama28/gnss/f9t/assist_runs -type f -name "gps_ephemeris.xml" -ls 2>/dev/null
```

### Pick The Correct Refresh Output Folder

Use the `hft02_*` folder that matches the refresh you just ran or the GNSS-SDR/IQ capture time.

For example:

```bash
SESSION_DIR=/home/rrama28/gnss/f9t/assist_runs/hft02_20260429_071857
```

Do **not** blindly use the newest folder if it does not match the run you are testing.

### Verify The Generated XML

```bash
ls -lh "$SESSION_DIR"/gps_*.xml

grep -o '<count>[0-9]*</count>' "$SESSION_DIR/gps_ephemeris.xml"
grep -o '<PRN>[0-9]*</PRN>' "$SESSION_DIR/gps_ephemeris.xml"
```

Good example output:

```text
<count>6</count>
<PRN>16</PRN>
<PRN>3</PRN>
<PRN>27</PRN>
<PRN>7</PRN>
<PRN>8</PRN>
<PRN>9</PRN>
```

### Copy The Verified XML Into The Active Assist Folder

Only do this after confirming the generated XML has a useful nonzero count.

```bash
ACTIVE=/home/rrama28/gnss/assist
BACKUP="$ACTIVE/backups/manual_fix_$(date -u +%Y%m%d_%H%M%S)"

mkdir -p "$BACKUP"
cp "$ACTIVE"/gps_*.xml "$BACKUP"/ 2>/dev/null || true

cp "$SESSION_DIR/gps_ephemeris.xml" "$ACTIVE/gps_ephemeris.xml"
cp "$SESSION_DIR/gps_iono.xml" "$ACTIVE/gps_iono.xml" 2>/dev/null || true
cp "$SESSION_DIR/gps_utc_model.xml" "$ACTIVE/gps_utc_model.xml" 2>/dev/null || true
```

### Verify The Active Assist Folder

```bash
ls -lh /home/rrama28/gnss/assist/gps_ephemeris.xml
grep -o '<count>[0-9]*</count>' /home/rrama28/gnss/assist/gps_ephemeris.xml
grep -o '<PRN>[0-9]*</PRN>' /home/rrama28/gnss/assist/gps_ephemeris.xml
```

Good signs:

- the selected `hft02_*` output folder exists
- the selected folder contains `gps_ephemeris.xml`
- `<count>` is nonzero
- expected PRNs appear as `<PRN>...</PRN>`
- the active assist XML now matches the verified generated XML
- GNSS-SDR later prints the usual XML-load messages

Do not use this as the main PRN check:

```bash
grep -o 'G[0-9][0-9]' gps_ephemeris.xml
```

The XML stores satellites as:

```xml
<PRN>3</PRN>
```

not as:

```text
G03
```

## Step 3: Pick The Right Config

Most relevant config groups:

- current focused Lime work: `configs_used/f9t_lime_current/`
- older baseline Lime configs: `configs_used/baseline/`
- AGNSS-oriented Lime configs: `configs_used/agnss/`
- RTL reference configs: `configs_used/rtl_reference/`
- sweep config families: `configs_used/sweeps/` and `results/logs/lime_sweeps/`

Current best starting point for new Lime tracking tests:

- `configs_used/f9t_lime_current/lime_gain20_noclockini_ephem_6ch_t26.conf`

Before running, make sure the config points to the active XML files:

```ini
GNSS-SDR.AGNSS_gps_ephemeris_xml=/home/rrama28/gnss/assist/gps_ephemeris.xml
GNSS-SDR.AGNSS_gps_iono_xml=/home/rrama28/gnss/assist/gps_iono.xml
GNSS-SDR.AGNSS_gps_utc_model_xml=/home/rrama28/gnss/assist/gps_utc_model.xml
```

Do not use configs that still point to:

```text
/home/rrama28/gnss/assist/f9t_latest/
```

because that folder does not exist in the current `hft02` runtime tree.

## Step 4: Set Focused PRNs Correctly

When testing only the current ephemeris satellites, all of these settings matter together:

- `Channels_1C.count`
- `Channel.signal`
- `Channels.in_acquisition`
- each `ChannelN.satellite`

Example for the useful six-PRN snapshot:

```ini
Channels_1C.count=6
Channel.signal=1C
Channels.in_acquisition=6
Channel0.satellite=16
Channel1.satellite=3
Channel2.satellite=27
Channel3.satellite=7
Channel4.satellite=8
Channel5.satellite=9
```

Same PRNs sorted:

```text
3, 7, 8, 9, 16, 27
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

- print all four variables before launching so you have the exact `RUN_DIR` for monitoring
- keep `SignalSource.dump=false` during position attempts
- use a fresh run directory every time
- do not launch GNSS-SDR from the home directory because it will dump `GSDR*`, `pvt_dat_*`, GPX, KML, and NMEA files there

## Step 6: Monitor From A Second SSH Session

Set `LOG` explicitly using the printed `RUN_DIR`. Do not rely on shell variables from the launch session.

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

Use this workflow to bypass GNSS-SDR tracking and analyze what the LimeSDR is actually receiving at the sample level. All scripts and saved figures are in `scripts_used/matlab_analysis/`.

### Capture IQ On hft02

```bash
RUN_ID=$(date -u +%Y%m%d_%H%M%S)
RUN_DIR=/home/alexgu2/gnss/runs/iq_capture_${RUN_ID}
mkdir -p "$RUN_DIR"
cd "$RUN_DIR"
gnss-sdr --config_file=/home/alexgu2/gnss/configs/lime_iq_capture.conf
```

Config:

- `configs_used/f9t_lime_current/lime_iq_capture.conf`

GNSS-SDR runs for 10 seconds and exits automatically.

Expected output:

- `lime_iq_capture.dat`
- about 160 MB
- `gr_complex`
- 2 Msps

The 2026-04-29 useful capture was:

```text
/home/alexgu2/gnss/runs/iq_capture_20260429_045742/lime_iq_capture.dat
```

The earlier capture was 0 MB and should not be used:

```text
/home/alexgu2/gnss/runs/iq_capture_20260429_045321/lime_iq_capture.dat
```

Future captures should be downloaded locally for MATLAB analysis. Do not commit large `.dat` files unless the team explicitly wants that.

### Copy IQ File From Alex Folder If Needed

```bash
mkdir -p /home/rrama28/gnss/iq_from_alex

sudo cp -r /home/alexgu2/gnss/runs/iq_capture_20260429_045742 /home/rrama28/gnss/iq_from_alex/

sudo chown -R rrama28:rrama28 /home/rrama28/gnss/iq_from_alex
```

Verify:

```bash
ls -lh /home/rrama28/gnss/iq_from_alex/iq_capture_20260429_045742/
```

### Run MATLAB Scripts In Order

Put all four `.m` files and `lime_iq_capture.dat` in the same local folder on the computer running MATLAB.

| Step | Script | What to do |
| --- | --- | --- |
| 1 | `spectrum.m` | Run as-is. Check DC spike dB above floor and any narrowband spikes inside ±511 kHz. |
| 2 | `prn_correlation.m` | Update `PRNS_TO_TEST` to match the verified ephemeris PRNs. |
| 3 | `tracking_sim.m` | Update `PRN` and `DOPPLER_HZ` from step 2 results before running. |
| 4 | `rtl_vs_lime.m` | Requires a separate RTL capture. Run only if RTL `.dat` is available. |

For the useful six-PRN snapshot, use:

```matlab
PRNS_TO_TEST = [3 7 8 9 16 27];
```

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
- narrowband spikes inside ±511 kHz: interference inside the GPS C/A code band
- C/N₀ per PRN: healthy >35 dB-Hz, marginal 28–35, too weak <28
- correlation maps: should show one sharp bright dot; horizontal stripes mean interference
- tracking sim lock fraction: >80% healthy, 40–80% marginal, <40% cannot hold lock

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