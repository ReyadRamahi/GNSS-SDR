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
- MATLAB for raw IQ analysis

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

As of 2026-04-29, the pipeline reaches acquisition and tracking starts, but repeatedly loses lock before bit sync. All software-accessible variables have been tested and ruled out. Raw IQ analysis has identified the root cause as hardware-level interference. The fix is hardware.

## What Is Proven

### 1. The antenna + GNSS-SDR pipeline can decode real GPS

The RTL-SDR reference path decoded real navigation data on the same antenna path.

Most important reference result:

- `track10_g45`: `4` bit-sync locks, `227` NAV messages, full subframes on PRNs `12`, `15`, `20`
- artifacts: `results/logs/rtl_track/run_summary.txt`

### 2. The LimeSDR path is alive

- GNSS-SDR opens the Lime through `gr-osmosdr` / `SoapySDR`
- receiver time advances during live runs
- acquisition succeeds at threshold 2.6
- tracking starts occur on expected PRNs

### 3. F9T XML refresh works

Current path: local serial receiver on `hft02`.

2026-04-28 refresh: `G03 G07 G08 G09 G16 G27`, count=6.

Reference: `results/assist/f9t_latest/README_CURRENT_XML.txt`

### 4. GPS signal is confirmed present on all 6 ephemeris PRNs

Raw IQ correlation from `prn_correlation.m` confirmed signal on all PRNs.

See `scripts_used/matlab_analysis/figures/CN0Summary.fig` and `PRNCorrelationMaps.fig`.

### 5. All software-accessible tracking variables have been ruled out

Six controlled single-variable experiments on 2026-04-28:

| Variable | Range tested | Effect on bit sync |
| --- | --- | --- |
| PLL/FLL loop bandwidth | wider (50/20 Hz) vs base (40/10 Hz) | none |
| LOAD_CONFIG / clock INI | present vs absent | none |
| Gain | 52 dB, 58 dB, 61 dB actual | none |
| LO offset | 0 Hz vs 250 kHz below L1 | none |

## What Is Not Solved

The remaining blocker is repeated loss of lock before bit synchronization, NAV decode, and position fix.

### Two interference sources identified

**1. DC spike — 32 dB above noise floor**

Severe zero-IF contamination from LO leakage into the baseband. At 32 dB above floor, significantly exceeds the 20 dB concern threshold.

See: `scripts_used/matlab_analysis/figures/DCSpike.fig`

**2. Narrowband interferer at -365 kHz offset from L1**

Sits inside the GPS C/A code bandwidth (±511 kHz). Likely USB 3.0 clock harmonic mixing into the RF path — a known LimeSDR-USB issue. Creates horizontal stripes across the entire code delay range in the correlation maps, preventing a clean acquisition peak.

See: `scripts_used/matlab_analysis/figures/PowerSpectrum.fig`, `PRNCorrelationMaps.fig`

### Signal level

All 6 ephemeris PRNs measured at 33–38 dB-Hz. Healthy tracking threshold is 35 dB-Hz. The signal is marginally present — interference is pushing the effective C/N₀ below the stable tracking threshold.

### Tracking simulation result

G27 (best PRN, C/N₀ 37.6 dB-Hz): 25.6% lock fraction over 2000 ms. PLL discriminator saturated throughout. Matches GNSS-SDR treadmill behavior exactly.

See: `scripts_used/matlab_analysis/figures/TrackingLoopSim.fig`

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
- LO offset / DC spike mitigation (250 kHz — insufficient clearance)

### Gain mapping note

```
gain=10 → 52 dB actual
gain=20 → 58 dB actual
gain=30 → 61 dB actual
```

Always check the actual reported RX gain in the GNSS-SDR log.

## Recommended Next Steps

**1. Move LimeSDR to USB 2.0 port** — free, immediate. The -365 kHz spur is likely USB 3.0 interference. If it disappears, C/N₀ will improve and tracking may stabilize without any hardware filter.

**2. Hardware GPS L1 bandpass filter** — SAW or cavity filter centered at 1575.42 MHz, ≤10 MHz bandwidth, before the LimeSDR LNAW input. Rejects the interferer and reduces wideband noise.

After either fix, restart from:
- `configs_used/f9t_lime_current/lime_gain20_noclockini_ephem_6ch_t26.conf`

## MATLAB Analysis Artifacts

Scripts: `scripts_used/matlab_analysis/`

| Script | Purpose |
| --- | --- |
| `spectrum.m` | Power spectrum, DC spike, interference identification |
| `prn_correlation.m` | PRN correlation maps, C/N₀ per PRN |
| `tracking_sim.m` | Tracking loop simulation, lock fraction, drift diagnosis |
| `rtl_vs_lime.m` | RTL vs Lime comparison (requires RTL capture) |

Figures: `scripts_used/matlab_analysis/figures/`

| Figure | Key finding |
| --- | --- |
| `PowerSpectrum.fig` | Noise floor -102.4 dB, DC spike and -365 kHz interferer visible |
| `DCSpike.fig` | DC spike 32 dB above floor |
| `PRNCorrelationMaps.fig` | Horizontal stripes — interference corrupting code delay axis |
| `CN0Summary.fig` | All PRNs 33–38 dB-Hz, straddling healthy threshold |
| `TrackingLoopSim.fig` | G27: 25.6% lock fraction, PLL saturated throughout |

IQ capture config: `configs_used/f9t_lime_current/lime_iq_capture.conf`
IQ capture data: `results/IQ_pairs/lime_iq_capture.dat` — 2026-04-29, 10 s at 2 Msps, gr_complex

## XML Path Warning

Configs created before 2026-04-28 point to `f9t_tcp_latest/` for AGNSS XML. Always verify configs point to `f9t_latest/`:

```ini
GNSS-SDR.AGNSS_gps_ephemeris_xml=/home/rrama28/gnss/assist/f9t_latest/gps_ephemeris.xml
GNSS-SDR.AGNSS_gps_utc_model_xml=/home/rrama28/gnss/assist/f9t_latest/gps_utc_model.xml
```

## Known Warnings

These appear often and do not prevent operation:

- SoapySDR duplicate entry for lime
- Gateware version mismatch

Do not run `LimeUtil --update` unless the professor explicitly requests it.

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
```

## Files Preserved in Repo

Commit: configs, scripts, MATLAB `.m` files, MATLAB `.fig` figures, XML snapshots if small, run summaries.

Do not commit: `*.bin`, `*.ubx`, `*.cs16`, `GSDR*`, `pvt_dat_*`, `*.gpx`, `*.kml`, `*.nmea`, large IQ captures, raw runtime folders. Exception: `results/IQ_pairs/lime_iq_capture.dat` is committed intentionally as the reference capture for MATLAB analysis.
