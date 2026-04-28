# GNSS-SDR Project Summary

## Goal

The project goal is to receive live GPS L1 C/A signals using SDR hardware on hft02, process them through GNSS-SDR, and eventually feed receiver/satellite/status information into the project dashboard.

Hardware tested:
- RTL-SDR path through SoapyRemote
- LimeSDR-USB on LNAW
- Shared GNSS antenna feed through splitter
- Antenna bias supplied externally, not by the LimeSDR
- Local u-blox F9T receiver on hft02 for fresh ephemeris assistance
- External 10 MHz clock path for LimeSDR testing

Software:
- GNSS-SDR v0.0.16
- GNU Radio 3.10.1.1
- gr-osmosdr / SoapySDR path
- RTKLIB convbin
- rinex2assist
- pyubx2 for F9T UBX configuration
- LimeSDR dedicated GNSS-SDR source block is not available in this installed build

---

## Main Findings

### 1. RTL-SDR is still the healthier receiver path

The RTL-SDR successfully decoded real GPS navigation messages. It was able to receive repeated NAV subframes and was good enough to generate GNSS-SDR assistance XML files.

Generated assistance files:
- gps_ephemeris.xml
- gps_iono.xml
- gps_utc_model.xml

Earlier harvested ephemeris XML contained:
- GPS PRN 28
- GPS PRN 31

This proves the antenna feed and GNSS-SDR pipeline can receive and decode real GPS data, at least through the RTL-SDR path.

---

### 2. LimeSDR RF is alive, but tracking is unstable

The LimeSDR is not dead. Recent RF sanity tests confirmed:
- GNSS-SDR can open the LimeSDR.
- The Lime receives nonzero IQ samples.
- RF power changes when gain changes.
- GNSS-SDR can start GPS L1 C/A tracking.
- Current receiver time advances during working runs.

Observed live RF signs:
- Current receiver time advances.
- Tracking starts occur.
- Multiple PRNs are attempted.
- Loss of lock occurs frequently.

Current remaining problem:
- No stable bit synchronization yet.
- No GPS NAV messages from Lime yet.
- No Lime position fix yet.

Typical Lime pattern:
- acquisition/tracking starts
- quick loss of lock
- tracking starts again
- no bit synchronization
- no GPS NAV message
- no position fix

Conclusion:
The Lime issue is not simply “no signal.” It is more likely a tracking stability, RF frontend, gain, filtering, clock, or sample-quality problem.

---

### 3. Old/default Lime config was bad

The old/default Lime config was not useful.

Important bad settings:
- SignalSource.AGC_enabled=true
- acquisition threshold around 3.5
- InputFilter.number_of_taps=51
- narrow filter setting around band1_end=0.45

That config produced weak acquisition behavior and basically no useful tracking.

---

### 4. Better Lime config came from sweep testing

The better Lime config came from sweep results.

Best balanced direction:
- sample rate: 2 Msps
- AGC disabled
- InputFilter.number_of_taps=101
- InputFilter.band1_end=0.70
- lower acquisition threshold
- based on cfg_sr2M_taps101_band70_agcF.conf

This config restored tracking starts, but still did not produce stable lock or NAV decode.

---

### 5. F9T local XML refresh path was added

The original hft09 TCP stream was unreliable:

- 10.30.200.59:50012

It worked once, but later attempts had connection refusals, zero-byte captures, or stalled streams.

We switched to the local F9T receiver on hft02:

- /dev/ttyUSB0

At first, the local F9T stream was NMEA-only:
- NMEA count was nonzero.
- UBX sync count was 0.
- RTCM count was 0.

That could not generate ephemeris because NMEA does not contain the raw navigation subframes needed for GPS ephemeris extraction.

Fix:
- Enable UBX protocol on UART1.
- Enable UBX-RXM-SFRBX.
- Enable UBX-RXM-RAWX.
- Keep NMEA output enabled.

Important UBX messages:
- UBX-RXM-SFRBX gives raw satellite navigation subframes needed for ephemeris.
- UBX-RXM-RAWX gives raw measurements useful for RINEX observation output.

Useful F9T config keys:
- CFG_UART1INPROT_UBX
- CFG_UART1OUTPROT_UBX
- CFG_UART1OUTPROT_NMEA
- CFG_MSGOUT_UBX_RXM_SFRBX_UART1
- CFG_MSGOUT_UBX_RXM_RAWX_UART1

Scripts added:
- ~/gnss/scripts/enable_f9t_ubx_uart1.py
- ~/gnss/scripts/refresh_f9t_xml_local.sh
- ~/gnss/scripts/start_f9t_refresh_local_tmux.sh

Latest XML path used by GNSS-SDR:
- /home/rrama28/gnss/assist/f9t_tcp_latest/gps_ephemeris.xml
- /home/rrama28/gnss/assist/f9t_tcp_latest/gps_utc_model.xml

The refresh script should only update the latest XML folder after a valid ephemeris generation. Failed captures should not overwrite known-good XML.

---

### 6. AGNSS XML loading works, but does not solve Lime by itself

GNSS-SDR successfully loads the refreshed F9T assistance XML.

Recent refreshed XML included ephemeris for:
- GPS PRN 31
- GPS PRN 10
- GPS PRN 02
- GPS PRN 28
- GPS PRN 01
- GPS PRN 26

Good XML signs:
- From XML file: Read NAV ephemeris ...
- From XML file: Read GPS UTC model parameters.
- From XML file: Read GPS ionosphere model parameters.
- GNSS assistance data loaded from local XML file(s).
- Using GPS Ephemeris: Sat ...

Important lesson:
XML loading only proves assistance data was loaded. It does not prove live RF tracking is working.

Good live RF signs:
- Current receiver time: 1 s
- Current receiver time: 2 s
- Tracking of GPS L1 C/A signal started ...

If Current receiver time never appears, GNSS-SDR has not really entered the live processing loop.

Conclusion:
AGNSS loading works, but the LimeSDR still needs stable tracking before it can decode NAV or produce a position fix.

---

### 7. Raw IQ dump caused confusion and should stay off for position attempts

GNSS-SDR raw IQ dumping works, but it creates huge files and made debugging much harder.

Example:
- A short dump produced hundreds of MB of IQ data.
- Reusing dump filenames caused confusing behavior.
- Runs with dump enabled were harder to interpret.

For live position attempts, use:
- SignalSource.dump=false

Raw IQ should be captured separately after live-position tests, not during the main position attempt.

---

### 8. Background launching was tricky

Some tmux/nohup runs appeared to stall after ephemeris loading. Foreground/direct runs reached Current receiver time and tracking more reliably.

Working signs from direct/terminal-like runs:
- Current receiver time advances.
- Tracking starts appear.
- Loss of lock events appear.

For future runs:
- Always run inside a clean run folder.
- Avoid piping through complicated tmux/tee setups if GNSS-SDR stalls.
- If backgrounding is needed, consider using script to provide a terminal-like environment.

Every GNSS-SDR run should be started from its own run folder because GNSS-SDR writes output files into the current working directory.

Correct pattern:
- Create a new run directory.
- cd into it.
- Run GNSS-SDR from inside that folder.
- Save run.log there.

Do not launch GNSS-SDR from /home/rrama28, or it will dump files like GSDR*, pvt_dat_*, GPX, KML, and NMEA files into the home directory.

---

### 9. Lime gain behavior is not intuitive

One config requested:

- SignalSource.gain=20

but GNSS-SDR reported:

- Actual RX Gain: 58 dB

So the Lime/gr-osmosdr/Soapy path maps gain internally. The printed Actual RX Gain is more important than the config value.

RF sanity results:
- Lower requested gain produced live tracking starts.
- Higher gain produced more RF power but did not clearly improve tracking.

Lesson:
Do not assume max gain is better. Tune around the settings that actually produce tracking.

---

### 10. External 10 MHz clock / LOAD_CONFIG should be tested separately

Professor-provided Lime settings file:

- /home/rrama28/gnss/lime_settings/10mhz_clock_working.ini

Soapy accepted it through:

- LOAD_CONFIG=/home/rrama28/gnss/lime_settings/10mhz_clock_working.ini

But this file appears to be an LMS7002M minimal config, not just a pure clock setting. It may change RF/front-end settings too.

Important lesson:
Do not mix all variables at once.

Recommended test order:
1. Get tracking with the known working RF config.
2. Keep dump off.
3. Use latest F9T XML.
4. Let the run continue long enough to test for bit sync and NAV decode.
5. Only then test LOAD_CONFIG as a separate A/B experiment.

---

## Current Best Known Direction

Use the processing-only gain20 latest-XML config:

- /home/rrama28/gnss/configs/lime_gain20_latestxml_processing_only.conf

Important settings:
- SignalSource.osmosdr_args=soapy=0,driver=lime,serial=0009061C01502715,antenna=LNAW
- SignalSource.gain=20
- SignalSource.dump=false
- AGNSS XML points to /home/rrama28/gnss/assist/f9t_tcp_latest/

What success should look like:
- Current receiver time advances.
- Tracking of GPS L1 C/A signal started.
- tracking bit synchronization locked.
- New GPS NAV message received.
- Position at ...

Current observed state:
- Current receiver time advances.
- Tracking starts occur.
- Loss of lock occurs frequently.
- No stable bit sync yet.
- No NAV messages yet.
- No position fix yet.

---

## Known Warnings

These warnings appear often:

- SoapySDR duplicate entry for lime
- Gateware version mismatch

They did not prevent the LimeSDR from opening or starting tracking.

Do not run this unless the professor explicitly wants a firmware/gateware update:

- LimeUtil --update

---

## Recommended Next Experiments

1. Let the current processing-only gain20 run continue for a long attempt.
2. Monitor:
   - Current receiver time
   - Tracking starts
   - Loss of lock
   - Bit synchronization
   - GPS NAV messages
   - Position fixes
3. If tracking starts but lock keeps dropping, tune gain around the actual working gain range.
4. Try a hardware GPS L1 bandpass filter before the LimeSDR.
5. Keep AGC disabled.
6. Keep SignalSource.dump=false during position attempts.
7. Test the external 10 MHz LOAD_CONFIG only after the normal RF config is stable.
8. Continue using RTL-SDR as the known GPS NAV decode baseline.

---

## Monitoring Commands

Set LOG first:

LOG=/path/to/run.log

Then run:

grep -c "Current receiver time" "$LOG"
grep -c "Tracking of GPS" "$LOG"
grep -c "Loss of lock" "$LOG"
grep -c "tracking bit synchronization locked" "$LOG"
grep -c "New GPS NAV message received" "$LOG"
grep -c "Position at" "$LOG"

grep -E "Current receiver time|Tracking of GPS|Loss of lock|tracking bit synchronization locked|New GPS NAV message received|Position at|Actual RX Gain|WARNING|ERROR" "$LOG" | tail -150

---

## Files Preserved in Repo

Curated files should be copied into docs, including:
- tested configs
- helper scripts
- sweep logs/configs
- F9T refresh scripts
- F9T UBX enable script
- RTL harvest logs
- Lime baseline logs
- Lime AGNSS logs
- RF sanity logs
- current run summaries
- GNSS-SDR assistance XML snapshots if small

Large generated files should not be committed:
- *.dat
- *.bin
- *.ubx
- *.cs16
- GSDR*
- pvt_dat_*
- *.gpx
- *.kml
- *.nmea
- large IQ captures
- raw runtime folders
