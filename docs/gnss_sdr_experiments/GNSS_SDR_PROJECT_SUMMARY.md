# GNSS-SDR Project Summary

## Goal

Receive live GPS L1 C/A with GNSS-SDR on `hft02`, using SDR hardware and fresh assistance data, then carry receiver/satellite/status information forward into the broader project dashboard work.

## Hardware And Software In Scope

Hardware tested:

- RTL-SDR path through SoapyRemote
- LimeSDR-USB on LNAW
- shared GNSS antenna feed through splitter
- external antenna bias, not Lime bias
- local u-blox F9T on `hft02` for fresh assistance XML
- external 10 MHz clock path for Lime testing

Software used:

- GNSS-SDR `v0.0.16`
- GNU Radio `3.10.1.1`
- `gr-osmosdr` / `SoapySDR`
- RTKLIB `convbin`
- `rinex2assist`
- `pyubx2` for F9T UBX configuration

Important environment constraint:

- this GNSS-SDR build does not have the dedicated Lime source block, so Lime runs go through `gr-osmosdr` / `SoapySDR`

## Current Workflow

1. Refresh GPS assistance XML from the local F9T on `hft02`.
2. Point GNSS-SDR at the refreshed XML.
3. Run LimeSDR-USB on GPS L1 C/A with focused PRNs from the current ephemeris.
4. Watch for the progression:
   - receiver time advancing
   - acquisition
   - tracking starts
   - bit sync
   - NAV decode
   - position fix

As of 2026-04-28, the pipeline reaches acquisition and tracking starts, but repeatedly loses lock before bit sync.

## What Is Proven

### 1. The antenna + GNSS-SDR pipeline can decode real GPS

The RTL-SDR reference path is healthy enough to decode real navigation data.

Evidence:

- `results/logs/rtl_track/run_summary.txt`
- `results/assist/rtl_harvested/`

Most important reference result:

- `track10_g45` produced `4` bit-sync locks and `227` NAV messages
- decoded subframes were seen for PRNs `12`, `15`, and `20`

That means the shared antenna path and GNSS-SDR processing chain are capable of real GPS decode.

### 2. The LimeSDR path is alive

The Lime is not failing at device-open or dead-RF stage.

Observed signs:

- GNSS-SDR opens the Lime through `gr-osmosdr` / `SoapySDR`
- receiver time advances during live runs
- acquisition succeeds
- tracking starts occur on expected PRNs
- gain changes measurably affect RF sanity runs

This rules out the simplest failure modes such as no device, no samples, or no ephemeris load.

### 3. F9T XML refresh works

The current F9T path is the local serial receiver on `hft02`, not the older `hft09` TCP stream.

Current evidence:

- `scripts_used/f9t_lime_current/refresh_f9t_xml_local.sh`
- `results/assist/f9t_latest/README_CURRENT_XML.txt`
- `results/logs/f9t_lime_current/latest_f9t_refresh.log`

The 2026-04-28 local refresh recorded six GPS satellites:

- `G03`
- `G07`
- `G08`
- `G09`
- `G16`
- `G27`

### 4. Assistance loading works, but assistance alone does not solve Lime tracking

GNSS-SDR successfully reads the XML assistance data, but live Lime runs still fail later in the chain.

Important interpretation:

- XML loading proves the assistance input path works
- receiver time advancing proves GNSS-SDR entered the live processing loop
- only bit sync, NAV messages, and fixes prove stable end-to-end tracking

## What Is Not Solved

The remaining blocker is repeated loss of lock before:

- tracking bit synchronization
- GPS NAV decode
- position fix

Typical Lime pattern:

- acquisition
- tracking start
- quick loss of lock
- reacquisition
- another tracking start
- no bit sync
- no NAV message
- no fix

This points to a tracking-stability problem rather than a missing-ephemeris problem.

## Best Current Technical Interpretation

The Lime issue is now most likely in one or more of these areas:

- loop bandwidth choice
- gain setting
- front-end filtering
- external clock interaction
- sample quality or RF cleanliness

The evidence does not support the claim that Lime is simply seeing no signal.

## Parameter Findings So Far

### Older/default Lime settings were poor

Weak settings from the earlier direction:

- `SignalSource.AGC_enabled=true`
- acquisition threshold around `3.5`
- `InputFilter.number_of_taps=51`
- narrow filter around `band1_end=0.45`

Those settings produced little useful tracking.

### Sweep work improved the Lime starting point

Best general direction from earlier sweep work:

- sample rate: `2 Msps`
- AGC: disabled
- `InputFilter.number_of_taps=101`
- `InputFilter.band1_end=0.70`
- lower acquisition threshold

That direction restored useful tracking starts but still did not reach stable lock.

### Current threshold finding

Current useful threshold range is:

- `2.6` to `2.8`

Observed outcomes from `results/logs/f9t_lime_current/`:

- `2.5` was too loose in earlier work
- `2.6` produced active acquisitions and repeated tracking starts
- `2.8` still produced some tracking but noticeably less
- `3.0` and `3.5` were too strict and produced no tracking starts in the focused tests

### Sticky/gentle tracking did not solve the core problem

The `t26` sticky-tracking run still lost lock repeatedly and produced:

- `0` bit-sync locks
- `0` NAV messages
- `0` fixes

## Recommended Next Experiments

Run these one variable at a time:

1. Wider tracking loops using the current best focused F9T+Lime setup as the base.
2. Gain A/B testing around the current gain-20 setup.
3. External `10 MHz` `LOAD_CONFIG` on versus off.
4. GPS L1 filter on versus off.
5. Only after tracking stabilizes, consider relaxing PRN focus or increasing channel count.

## Where To Look Next

- Start here: `README.md`
- Current handoff: `LIMESDR_F9T_HANDOFF_20260428.md`
- Operator workflow: `WORKFLOW.md`
- Short history of what was tried: `EXPERIMENT_LOG.md`
- Config map: `configs_used/CONFIG_INDEX.md`

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
