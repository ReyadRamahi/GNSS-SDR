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

As of 2026-04-28, the pipeline reaches acquisition and tracking starts, but repeatedly loses lock before bit sync. All software-accessible variables have been tested and ruled out. The remaining lever is a hardware GPS L1 bandpass filter.

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
- gain changes measurably affect actual RX gain

### 3. F9T XML refresh works

The current F9T path is the local serial receiver on `hft02`, not the older `hft09` TCP stream.

Current evidence:

- `scripts_used/f9t_lime_current/refresh_f9t_xml_local.sh`
- `results/assist/f9t_latest/README_CURRENT_XML.txt`
- `results/logs/f9t_lime_current/latest_f9t_refresh.log`

The 2026-04-28 local refresh recorded six GPS satellites:

- `G03`, `G07`, `G08`, `G09`, `G16`, `G27`

### 4. All software-accessible tracking variables have been ruled out

Six controlled single-variable experiments were run on 2026-04-28. None produced bit sync.

| Variable | Range tested | Effect on bit sync |
| --- | --- | --- |
| PLL/FLL loop bandwidth | wider (50/20 Hz) vs base (40/10 Hz) | none |
| LOAD_CONFIG / clock INI | present vs absent | none |
| Gain | 52 dB, 58 dB, 61 dB actual | none |
| LO offset | 0 Hz vs 250 kHz below L1 | none |

The start/loss count was stable at roughly 80–100 starts and nearly identical losses across every run. This consistency across independent variables confirms the problem is not in any software-tunable parameter.

## What Is Not Solved

The remaining blocker is repeated loss of lock before:

- tracking bit synchronization
- GPS NAV decode
- position fix

Typical Lime pattern across all runs:

- acquisition
- tracking start
- quick loss of lock
- reacquisition
- repeat indefinitely
- no bit sync
- no NAV message
- no fix

## Best Current Technical Interpretation

The effective C/N₀ at the Lime correlator input is below the threshold needed for stable tracking. The RTL-SDR decoded 227 NAV messages on the same antenna path. The Lime has zero across all runs. The difference is the RF frontend.

The LimeSDR routed through `gr-osmosdr`/SoapySDR without the native Lime source block has a higher effective noise figure than the RTL on a working signal path. Without a hardware bandpass filter before the LimeSDR, wideband noise enters the front end and the effective C/N₀ at the correlators is too low to hold lock — regardless of any software parameter.

## Parameter Findings To Date

### Confirmed working range

- acquisition threshold: `2.6` (useful), `2.8` (marginal), `3.0+` (too strict)
- sample rate: `2 Msps`
- AGC: disabled
- filter taps: `101`
- `band1_end=0.70`

### Confirmed neutral or ruled out

- loop bandwidth (both directions)
- LOAD_CONFIG / LMS7002M clock INI
- gain across 52–61 dB actual
- LO offset / DC spike mitigation

### Gain mapping note

The gr-osmosdr/SoapySDR gain mapping for the LimeSDR is nonlinear. Always check the actual reported RX gain in the GNSS-SDR log, not the config value:

```
gain=10 → 52 dB actual
gain=20 → 58 dB actual
gain=30 → 61 dB actual
```

## Recommended Next Step

Hardware GPS L1 bandpass filter before the LimeSDR LNAW input. A filter centered on 1575.42 MHz with a bandwidth of ≤10 MHz would reject the wideband noise that the software filter cannot remove, directly improving the effective C/N₀ at the correlators.

After adding a hardware filter, restart from the clean base config:

- `configs_used/f9t_lime_current/lime_gain20_noclockini_ephem_6ch_t26.conf`

## Known Warnings

These warnings appear often and do not prevent operation:

- SoapySDR duplicate entry for lime
- Gateware version mismatch

Do not run this unless the professor explicitly wants a firmware/gateware update:

```bash
LimeUtil --update
```

## XML Path Warning

Configs created before 2026-04-28 point to `f9t_tcp_latest/` for the AGNSS XML. This is the old, unreliable TCP source. Always verify config AGNSS paths point to `f9t_latest/` before running. The correct paths are:

```ini
GNSS-SDR.AGNSS_gps_ephemeris_xml=/home/rrama28/gnss/assist/f9t_latest/gps_ephemeris.xml
GNSS-SDR.AGNSS_gps_utc_model_xml=/home/rrama28/gnss/assist/f9t_latest/gps_utc_model.xml
```

## Monitoring Commands

```bash
LOG=/path/to/run.log

grep -c "Current receiver time" "$LOG"
grep -c "Tracking of GPS" "$LOG"
grep -c "Loss of lock" "$LOG"
grep -c "tracking bit synchronization locked" "$LOG"
grep -c "New GPS NAV message received" "$LOG"
grep -c "Position at" "$LOG"
grep "Actual RX Gain" "$LOG" | head -3

grep -E "Current receiver time|Tracking of GPS|Loss of lock|tracking bit synchronization locked|New GPS NAV message received|Position at|Actual RX Gain|WARNING|ERROR" "$LOG" | tail -150
```

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

- `*.dat`, `*.bin`, `*.ubx`, `*.cs16`
- `GSDR*`, `pvt_dat_*`
- `*.gpx`, `*.kml`, `*.nmea`
- large IQ captures
- raw runtime folders
