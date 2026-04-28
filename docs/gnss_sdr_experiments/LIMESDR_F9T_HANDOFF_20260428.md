# LimeSDR + F9T GNSS-SDR Handoff Notes

Date: 2026-04-28  
Project: GNSS-SDR GPS L1 C/A receiver testing  
Machine: hft02  
Main goal: get LimeSDR-USB to hold GPS L1 C/A lock long enough for bit sync, NAV decode, and position fix.

---

## 1. Current State

The LimeSDR path is alive, but not solved.

We have proven:

- GNSS-SDR can open the LimeSDR.
- The LimeSDR receives nonzero RF/IQ samples.
- GNSS-SDR current receiver time advances.
- Acquisition/tracking starts occur.
- Restricting channels to the F9T ephemeris PRNs now works.
- The current failure is repeated loss of lock after tracking starts.

We have not yet achieved:

- tracking bit synchronization locked
- New GPS NAV message received
- Position at

Current bottleneck:

- Tracking stability after acquisition.

---

## 2. Hardware and Software Setup

Hardware:

- LimeSDR-USB
- Lime serial: 0009061C01502715
- Lime antenna input: LNAW
- Local u-blox F9T receiver on hft02
- Shared GNSS antenna feed
- Antenna bias is externally supplied
- External 10 MHz clock path available

Software:

- Ubuntu 22.04
- GNSS-SDR v0.0.16
- GNU Radio 3.10.1.1
- gr-osmosdr / SoapySDR path
- RTKLIB convbin
- rinex2assist
- pyubx2 for F9T UBX configuration

Known warnings:

- SoapySDR duplicate entry for lime
- Gateware version mismatch

These warnings did not stop GNSS-SDR from opening LimeSDR or starting tracking.

Do not run LimeUtil --update unless the professor explicitly approves it.

---

## 3. F9T XML Refresh Workflow

The original TCP stream from hft09 was unreliable:

- 10.30.200.59:50012

It worked once but later gave connection refusals, zero-byte captures, or stalls.

We switched to the local F9T on hft02:

- /dev/ttyUSB0

Initial local F9T output was NMEA-only:

- NMEA count was nonzero
- UBX sync count was 0
- RTCM count was 0

NMEA alone is not enough for ephemeris extraction. The F9T must output UBX RXM messages.

Important UBX messages:

- UBX-RXM-SFRBX gives raw satellite navigation subframes for ephemeris.
- UBX-RXM-RAWX gives raw measurements useful for RINEX observation output.

Useful F9T config keys:

- CFG_UART1INPROT_UBX
- CFG_UART1OUTPROT_UBX
- CFG_UART1OUTPROT_NMEA
- CFG_MSGOUT_UBX_RXM_SFRBX_UART1
- CFG_MSGOUT_UBX_RXM_RAWX_UART1

Scripts:

- ~/gnss/scripts/enable_f9t_ubx_uart1.py
- ~/gnss/scripts/refresh_f9t_xml_local.sh
- ~/gnss/scripts/start_f9t_refresh_local_tmux.sh

Latest XML folder:

- /home/rrama28/gnss/assist/f9t_tcp_latest/

Important files:

- gps_ephemeris.xml
- gps_utc_model.xml
- README_CURRENT_XML.txt

Check current XML:

    ls -lh /home/rrama28/gnss/assist/f9t_tcp_latest/
    grep -o '<count>[0-9]*</count>' /home/rrama28/gnss/assist/f9t_tcp_latest/gps_ephemeris.xml
    grep -o 'G[0-9][0-9]' /home/rrama28/gnss/assist/f9t_tcp_latest/gps_ephemeris.xml | sort -u

Important lesson:

GNSS-SDR reads XML only at startup. If XML refreshes while GNSS-SDR is running, restart GNSS-SDR to use the new XML.

---

## 4. GNSS-SDR Run Organization

GNSS-SDR writes runtime files into the current working directory.

Do not launch GNSS-SDR from /home/rrama28.

Use one folder per run:

    RUN_ID=$(date -u +%Y%m%d_%H%M%S)
    RUN_DIR=/home/rrama28/gnss/output/position_attempts/example_${RUN_ID}
    mkdir -p "$RUN_DIR"
    cd "$RUN_DIR"
    gnss-sdr --config_file=/path/to/config.conf

Files that may appear:

- GSDR*
- pvt_dat_*
- .gpx
- .kml
- .nmea
- run.log

Do not commit these runtime files unless they are tiny, curated log snippets.

---

## 5. Best Known Working Config Direction

Current best base config:

- /home/rrama28/gnss/configs/lime_gain20_latestxml_processing_only_10mhz_clock.conf

Important settings:

- SignalSource.implementation=Osmosdr_Signal_Source
- SignalSource.freq=1575420000
- SignalSource.sampling_frequency=2000000
- SignalSource.gain=20
- SignalSource.dump=false
- SignalSource.osmosdr_args=soapy=0,driver=lime,serial=0009061C01502715,antenna=LNAW,LOAD_CONFIG=/home/rrama28/gnss/lime_settings/10mhz_clock_working.ini

GNSS-SDR reports:

- Actual RX Gain: 58 dB

This means the requested config gain does not directly equal the printed hardware gain. The printed actual gain is what should be compared between runs.

---

## 6. External 10 MHz Clock Notes

Clock settings file:

- /home/rrama28/gnss/lime_settings/10mhz_clock_working.ini

Soapy argument:

- LOAD_CONFIG=/home/rrama28/gnss/lime_settings/10mhz_clock_working.ini

This is not guaranteed to be a pure clock-only setting. It may also change Lime front-end/LMS7002M settings.

Scientific method rule:

- Test with clock and without clock as separate A/B tests.
- Do not change XML, gain, acquisition, tracking, and clock all at once.

Current state:

- The clock config no longer kills the run.
- GNSS-SDR still reaches current receiver time and starts tracking with LOAD_CONFIG enabled.
- The failure remains loss of lock.

---

## 7. Acquisition Experiments Tried

Original loose acquisition:

- Acquisition_1C.threshold=2.5
- Result: many tracking starts, many fast losses, lots of PRNs attempted.

Strict acquisition:

- threshold=5.0
- Result: too strict, no tracking starts.

Middle strict attempts:

- threshold=3.5
- threshold=3.0
- Result: still too strict, no useful tracking starts.

Better focused attempts:

- threshold=2.8
- threshold=2.6
- Result: tracking starts occur, fewer than 2.5, but still loss of lock.

Current useful range:

- Acquisition threshold is likely between 2.5 and 2.8.

---

## 8. Ephemeris-Focused PRN Restriction

At first, GNSS-SDR was trying nearly every PRN, which looked like false or weak acquisition chaos.

We then restricted channels to the PRNs in the current F9T XML.

Current refreshed XML loaded:

- PRN 16
- PRN 03
- PRN 27
- PRN 07
- PRN 08
- PRN 09

Working focused channel config needs these kinds of lines:

- Channels_1C.count=6
- Channel.signal=1C
- Channels.in_acquisition=6
- Channel0.satellite=16
- Channel1.satellite=3
- Channel2.satellite=9
- Channel3.satellite=27
- Channel4.satellite=7
- Channel5.satellite=8

Important lesson:

ChannelN.satellite alone was not enough in the earlier attempt. The clean version also forced Channels_1C.count, Channel.signal, and Channels.in_acquisition.

Result:

GNSS-SDR finally focused on only the ephemeris PRNs.

That was a major improvement.

---

## 9. Current Failure Pattern

With focused PRNs, tracking starts on the correct satellites.

Example behavior:

- Tracking of GPS L1 C/A signal started on PRN 08
- Tracking of GPS L1 C/A signal started on PRN 07
- Tracking of GPS L1 C/A signal started on PRN 03
- Tracking of GPS L1 C/A signal started on PRN 09
- Tracking of GPS L1 C/A signal started on PRN 27
- Tracking of GPS L1 C/A signal started on PRN 16

But it still drops lock.

Typical pattern:

- acquisition starts
- tracking starts
- current receiver time continues
- loss of lock after about 10 to 20 seconds
- same or another PRN reacquires
- no bit sync
- no NAV message
- no position fix

This strongly suggests the issue is now tracking loop stability or RF signal quality, not missing ephemeris.

---

## 10. Tracking Experiments Tried

Original tracking settings:

- Tracking_1C.pll_bw_hz=40.0
- Tracking_1C.dll_bw_hz=2.0
- Tracking_1C.pll_bw_narrow_hz=2.0
- Tracking_1C.dll_bw_narrow_hz=0.25
- Tracking_1C.fll_bw_hz=10.0
- Tracking_1C.enable_fll_pull_in=true
- Tracking_1C.early_late_space_chips=0.5

Sticky/gentle tracking attempt:

- Tracking_1C.cn0_min=20
- Tracking_1C.cn0_samples=40
- Tracking_1C.max_lock_fail=100
- Tracking_1C.pll_bw_hz=25.0
- Tracking_1C.dll_bw_hz=1.0
- Tracking_1C.fll_bw_hz=10.0

Result:

- Still dropped lock.
- Gentler loops did not fix the issue.

Next tracking idea:

Try wider loops again because the Lime/frequency behavior may require tracking to follow faster movement:

- Acquisition_1C.threshold=2.8
- Tracking_1C.pll_bw_hz=50.0
- Tracking_1C.dll_bw_hz=2.0
- Tracking_1C.fll_bw_hz=20.0
- Tracking_1C.enable_fll_pull_in=true

---

## 11. How To Continue From Here

Step 1: Refresh F9T XML.

    DUR=900
    SESSION=f9t_xml_refresh_$(date -u +%Y%m%d_%H%M%S)
    tmux new-session -d -s "$SESSION" "/home/rrama28/gnss/scripts/refresh_f9t_xml_local.sh $DUR"
    tmux attach -t "$SESSION"

Step 2: Verify XML.

    ls -lh /home/rrama28/gnss/assist/f9t_tcp_latest/
    grep -o '<count>[0-9]*</count>' /home/rrama28/gnss/assist/f9t_tcp_latest/gps_ephemeris.xml
    grep -o 'G[0-9][0-9]' /home/rrama28/gnss/assist/f9t_tcp_latest/gps_ephemeris.xml | sort -u

Step 3: Update the focused PRN list in the GNSS-SDR config based on the XML.

Example if XML has PRNs 16, 03, 27, 07, 08, 09:

- Channel0.satellite=16
- Channel1.satellite=3
- Channel2.satellite=9
- Channel3.satellite=27
- Channel4.satellite=7
- Channel5.satellite=8

Step 4: Run one experiment at a time.

Use one variable per run:

- threshold only
- tracking loop bandwidth only
- gain only
- clock LOAD_CONFIG on/off only
- filter/no filter only

Step 5: Monitor counts.

    LOG=/path/to/run.log

    grep -c "Current receiver time" "$LOG"
    grep -c "Tracking of GPS" "$LOG"
    grep -c "Loss of lock" "$LOG"
    grep -c "tracking bit synchronization locked" "$LOG"
    grep -c "New GPS NAV message received" "$LOG"
    grep -c "Position at" "$LOG"

    grep "Tracking of GPS" "$LOG" | sed -E 's/.*PRN ([0-9]+).*/PRN \1/' | sort | uniq -c | sort -nr

Step 6: Decide if the run improved.

Better run means:

- Current receiver time advances.
- Tracking starts occur only on intended PRNs.
- Loss of lock count decreases.
- Tracks survive longer.
- Bit sync appears.
- NAV messages appear.
- Position appears.

More tracking starts alone is not necessarily better.

---

## 12. Recommended Next Experiments

Experiment A: Focused PRNs, threshold 2.8, wider tracking loops.

Purpose:

- See if wider loops can follow Lime clock/frequency wobble better.

Experiment B: Same as A, but no external 10 MHz LOAD_CONFIG.

Purpose:

- Check if the clock settings file helps or hurts tracking stability.

Experiment C: Same as best focused config, but adjust gain.

Purpose:

- Current requested gain is 20 and actual printed gain is around 58 dB.
- Try one slightly lower and one slightly higher setting.
- Compare loss of lock and bit sync.

Experiment D: Add GPS L1 bandpass filter before LimeSDR.

Purpose:

- If software cannot fix loss of lock, RF front-end noise/interference is likely.
- A hardware L1 filter may improve tracking stability.

---

## 13. What Not To Do

Do not enable SignalSource.dump during position attempts.

Reason:

- It creates huge IQ files.
- It made debugging harder.
- It can fill disk quickly.

Do not run GNSS-SDR from /home/rrama28.

Reason:

- It sprays runtime output files into the home directory.

Do not update Lime firmware/gateware without professor approval.

Reason:

- Gateware mismatch warning exists, but Lime still opens and tracks.
- Firmware changes could create new problems.

Do not change five variables at once.

Reason:

- We need scientific-method debugging where each run has one clear difference.

---

## 14. Current Best Interpretation

We have moved through the pipeline:

- F9T XML refresh works.
- GNSS-SDR loads AGNSS XML.
- LimeSDR opens.
- LimeSDR RF is alive.
- Receiver time advances.
- Acquisition starts.
- PRN restriction works.
- Tracking starts on correct PRNs.
- Tracking cannot hold long enough for bit sync.

The current problem is likely one of:

- LimeSDR RF/front-end signal quality
- Too much interference before SDR
- Need for GPS L1 bandpass filter
- Gain not ideal
- Tracking loop bandwidth not ideal
- External clock config altering Lime front-end settings
- Clock/reference quality or temperature stability issue

Next person should start from the focused six-PRN config and tune tracking/gain/RF hardware, not restart from XML debugging.
