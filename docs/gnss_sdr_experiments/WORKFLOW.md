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

Useful checks:

```bash
ls -lh /home/rrama28/gnss/assist/f9t_tcp_latest/
grep -o '<count>[0-9]*</count>' /home/rrama28/gnss/assist/f9t_tcp_latest/gps_ephemeris.xml
grep -o 'G[0-9][0-9]' /home/rrama28/gnss/assist/f9t_tcp_latest/gps_ephemeris.xml | sort -u
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

- `configs_used/f9t_lime_current/lime_gain20_10mhz_ephem_6ch_t26_clean.conf`

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
RUN_DIR=/home/rrama28/gnss/output/position_attempts/example_${RUN_ID}
SESSION=example_${RUN_ID}
CONF=/path/to/config.conf
mkdir -p "$RUN_DIR"
tmux new-session -d -s "$SESSION" "cd '$RUN_DIR' && timeout --signal=INT 30m gnss-sdr --config_file='$CONF'"
tmux pipe-pane -o -t "$SESSION" "cat >> '$RUN_DIR/run.log'"
tmux attach -t "$SESSION"
```

Run rules:

- keep `SignalSource.dump=false` during position attempts
- use a fresh run directory every time
- if tmux/nohup piping behaves strangely, try a more direct terminal-like run

## Step 6: Check The Right Signals In The Log

Useful commands:

```bash
LOG=/path/to/run.log
grep -c "Current receiver time" "$LOG"
grep -c "Tracking of GPS" "$LOG"
grep -c "Loss of lock" "$LOG"
grep -c "tracking bit synchronization locked" "$LOG"
grep -c "New GPS NAV message received" "$LOG"
grep -c "Position at" "$LOG"
grep "Tracking of GPS" "$LOG" | sed -E 's/.*PRN ([0-9]+).*/PRN \1/' | sort | uniq -c | sort -nr
```

Interpretation:

- assistance loaded: XML path is working
- receiver time advancing: GNSS-SDR entered live processing
- tracking starts: acquisition is producing candidates
- repeated loss of lock with zero bit sync: current blocker is tracking stability
- NAV messages or a fix: the main Lime problem is finally breaking

## Step 7: Change One Variable Per Run

Good controlled variables:

- acquisition threshold
- tracking loop bandwidth
- gain
- external `10 MHz` `LOAD_CONFIG` on versus off
- GPS L1 filter on versus off
- antenna/feed path

Do not change XML, gain, clock, threshold, and tracking behavior all at once.

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
