# LimeSDR + F9T GNSS-SDR Handoff Notes

Date: 2026-04-28

## Current State

The LimeSDR path is alive but not solved.

Working:
- F9T XML refresh works.
- GNSS-SDR loads F9T XML assistance.
- LimeSDR opens through gr-osmosdr / SoapySDR.
- Current receiver time advances.
- Acquisition starts.
- PRN restriction now works.
- Tracking starts on the correct ephemeris PRNs.

Not working yet:
- tracking bit synchronization locked
- New GPS NAV message received
- Position at

Current bottleneck:
- Tracking stability after acquisition.

## Main Workflow

1. Refresh F9T XML.

    DUR=900
    SESSION=f9t_xml_refresh_$(date -u +%Y%m%d_%H%M%S)
    tmux new-session -d -s "$SESSION" "/home/rrama28/gnss/scripts/refresh_f9t_xml_local.sh $DUR"
    tmux attach -t "$SESSION"

2. Verify XML.

    ls -lh /home/rrama28/gnss/assist/f9t_tcp_latest/
    grep -o '<count>[0-9]*</count>' /home/rrama28/gnss/assist/f9t_tcp_latest/gps_ephemeris.xml
    grep -o 'G[0-9][0-9]' /home/rrama28/gnss/assist/f9t_tcp_latest/gps_ephemeris.xml | sort -u

3. Update focused PRNs in the GNSS-SDR config.

Example:

    Channels_1C.count=6
    Channel.signal=1C
    Channels.in_acquisition=6
    Channel0.satellite=16
    Channel1.satellite=3
    Channel2.satellite=9
    Channel3.satellite=27
    Channel4.satellite=7
    Channel5.satellite=8

4. Start GNSS-SDR in a clean run folder.

    RUN_ID=$(date -u +%Y%m%d_%H%M%S)
    RUN_DIR=/home/rrama28/gnss/output/position_attempts/example_${RUN_ID}
    SESSION=example_${RUN_ID}
    CONF=/path/to/config.conf
    mkdir -p "$RUN_DIR"
    tmux new-session -d -s "$SESSION" "cd '$RUN_DIR' && timeout --signal=INT 30m gnss-sdr --config_file='$CONF'"
    tmux pipe-pane -o -t "$SESSION" "cat >> '$RUN_DIR/run.log'"
    tmux attach -t "$SESSION"

5. Monitor results.

    LOG=/path/to/run.log
    grep -c "Current receiver time" "$LOG"
    grep -c "Tracking of GPS" "$LOG"
    grep -c "Loss of lock" "$LOG"
    grep -c "tracking bit synchronization locked" "$LOG"
    grep -c "New GPS NAV message received" "$LOG"
    grep -c "Position at" "$LOG"
    grep "Tracking of GPS" "$LOG" | sed -E 's/.*PRN ([0-9]+).*/PRN \1/' | sort | uniq -c | sort -nr

## Scientific Method Notes

Change one variable per run.

Good variables to test:
- acquisition threshold
- tracking loop bandwidth
- gain
- external 10 MHz LOAD_CONFIG on/off
- GPS L1 filter/no filter
- antenna/feed path

Do not change XML, gain, clock, acquisition, tracking, and dump mode all at once.

## Important Findings

Threshold:
- 2.5 too loose
- 3.0+ too strict
- 2.6 to 2.8 useful range

Tracking:
- sticky/gentle tracking did not fix loss of lock
- next likely tracking test is wider loops

Clock:
- LOAD_CONFIG no longer kills the run
- still should be A/B tested against no LOAD_CONFIG

Dump:
- keep SignalSource.dump=false during position attempts

## Best Interpretation

The issue is no longer dead RF or missing ephemeris. The LimeSDR receives and acquires GPS L1 C/A, but cannot maintain stable tracking long enough for bit sync, NAV decode, or a position fix.
