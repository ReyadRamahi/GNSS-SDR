# Experiment Log

This page summarizes the most important experiment phases and what each phase taught the team.

## 1. RTL Reference Path Proved The Pipeline

Evidence:

- `results/logs/rtl_track/run_summary.txt`
- `results/assist/rtl_harvested/`

Key results:

- `track10_g42`: `10` tracking starts, `0` bit sync, `0` NAV
- `track10_g45`: `249` tracking starts, `4` bit sync locks, `227` NAV messages
- `track10_g49`: `37` tracking starts, `0` bit sync, `0` NAV

Decoded subframes from `track10_g45`:

- PRN `12`: `SF1` to `SF5`
- PRN `15`: `SF1` to `SF5`
- PRN `20`: `SF1` to `SF5`

Conclusion:

- the shared antenna path and GNSS-SDR chain can decode real GPS NAV data
- Lime instability is not proof that the whole system is dead

## 2. Early Lime Defaults Were Weak

Older poor-direction settings included:

- `SignalSource.AGC_enabled=true`
- acquisition threshold near `3.5`
- `InputFilter.number_of_taps=51`
- narrow front-end filter around `band1_end=0.45`

Conclusion:

- early baseline Lime configs were too conservative and did not produce useful tracking behavior

## 3. Lime Sweep Work Found A Better Starting Point

Relevant artifacts:

- `results/logs/lime_sweeps/v1/`
- `results/logs/lime_sweeps/v2/`
- `results/logs/lime_sweeps/v3/`
- `configs_used/sweeps/msps/`

Best broad direction to come out of the sweeps:

- sample rate: `2 Msps`
- AGC: off
- filter taps: `101`
- `band1_end=0.70`
- lower acquisition threshold

Conclusion:

- sweep testing moved Lime from mostly-dead behavior to repeatable acquisition and tracking starts
- it still did not solve stable lock

## 4. F9T Assistance Moved From Unreliable TCP To Local Serial

Older reference path:

- `scripts_used/f9t_refresh/`
- `results/assist/f9t_tcp_reference/`
- `results/logs/f9t_refresh/refresh_20260426_042603.log`

Current path:

- `scripts_used/f9t_lime_current/`
- `results/assist/f9t_latest/`

Why the change happened:

- the older `hft09` TCP source worked once but later stalled, refused connections, or ended with zero-byte progress
- the local F9T on `hft02` became the more reliable way to refresh assistance XML

Important fix:

- enable UBX on UART1
- enable `UBX-RXM-SFRBX`
- enable `UBX-RXM-RAWX`

Conclusion:

- fresh assistance XML is no longer the main bottleneck

## 5. 2026-04-28 Focused Threshold Experiments

Artifacts:

- `results/logs/f9t_lime_current/ephem_focus_threshold26_20260428_074109_summary.txt`
- `results/logs/f9t_lime_current/ephem_focus_threshold28_20260428_073347_summary.txt`
- `results/logs/f9t_lime_current/ephem_focus_threshold30_20260428_073152_summary.txt`
- `results/logs/f9t_lime_current/ephem_focus_threshold35_20260428_072802_summary.txt`

Results:

| Config family | Receiver time lines | Tracking starts | Losses of lock | Bit sync | NAV |
| --- | ---: | ---: | ---: | ---: | ---: |
| threshold 2.6 | 282 | 22 | 21 | 0 | 0 |
| threshold 2.8 | 259 | 5 | 5 | 0 | 0 |
| threshold 3.0 | 112 | 0 | 0 | 0 | 0 |
| threshold 3.5 | 210 | 0 | 0 | 0 | 0 |

Conclusion:

- `2.6` to `2.8` is the useful threshold range
- `3.0+` is too strict in the current focused setup

## 6. 2026-04-28 Focused 6-Channel Lime Runs

Artifacts:

- `results/logs/f9t_lime_current/ephem_6ch_t26_clean_20260428_074552_summary.txt`
- `results/logs/f9t_lime_current/ephem_6ch_t26_sticky_tracking_20260428_074838_summary.txt`
- `results/logs/f9t_lime_current/ephem_6ch_t28_wide_tracking_20260428_075114_summary.txt`

Results:

| Run | Receiver time lines | Tracking starts | Losses of lock | Bit sync | NAV | Fix |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `t26_clean` | 163 | 38 | 35 | 0 | 0 | 0 |
| `t26_sticky_tracking` | 144 | 37 | 36 | 0 | 0 | 0 |
| `t28_wide_tracking` | 42 | 7 | 4 | 0 | 0 | 0 |

Extra note:

- the `t28_wide_tracking` run was short-lived with gateware warnings — not a valid data point
- sticky vs clean comparison is nearly identical — loop tightness is not the variable

Conclusion:

- sticky/gentle tracking did not fix loss of lock
- the current challenge is not getting starts, it is holding them

## 7. 2026-04-28 Single-Variable Sweep — Software Parameters Exhausted

All runs branched from `lime_gain20_10mhz_ephem_6ch_t26_clean.conf` with exactly one variable changed per run. LOAD_CONFIG was removed for all gain and DC offset runs to isolate variables cleanly. All new configs also fix the XML path bug (see Phase 7b).

### 7a. Wide Tracking Loops

Config: `lime_gain20_10mhz_ephem_6ch_t26_wideloop.conf`

Changes: `pll_bw_hz` 40→50, `fll_bw_hz` 10→20

| Receiver time | Tracking starts | Losses of lock | Bit sync | NAV |
| ---: | ---: | ---: | ---: | ---: |
| 401 | 103 | 99 | 0 | 0 |

Conclusion: loop bandwidth in either direction has no effect. Ruled out.

### 7b. LOAD_CONFIG Off

Config: `lime_gain20_noclockini_ephem_6ch_t26.conf`

Changes: `LOAD_CONFIG=...` removed from `osmosdr_args`, XML paths corrected to `f9t_latest/`

| Receiver time | Tracking starts | Losses of lock | Bit sync | NAV |
| ---: | ---: | ---: | ---: | ---: |
| 361 | 95 | 91 | 0 | 0 |

Conclusion: `10mhz_clock_working.ini` is neutral. LOAD_CONFIG ruled out.

### 7c. Gain Sweep

All runs used LOAD_CONFIG off and corrected XML paths.

| Config | Actual RX Gain | Receiver time | Tracking starts | Losses of lock | Bit sync |
| --- | ---: | ---: | ---: | ---: | ---: |
| `lime_gain10_noclockini_ephem_6ch_t26.conf` | 52 dB | 403 | 99 | 95 | 0 |
| `lime_gain20_noclockini_ephem_6ch_t26.conf` | 58 dB | 304 | 82 | 79 | 0 |
| `lime_gain30_noclockini_ephem_6ch_t26.conf` | 61 dB | 350 | 90 | 86 | 0 |

Note: `gain=20` maps to `58 dB` actual. Always check the reported actual gain, not the config value.

Conclusion: gain across a 9 dB actual range had no effect. Ruled out.

### 7d. DC Offset Tuning

Config: `lime_gain20_dcoffset250_ephem_6ch_t26.conf`

Changes: `SignalSource.freq` 1575420000→1575170000, `InputFilter.IF` 0→250000

| Receiver time | Tracking starts | Losses of lock | Bit sync | NAV |
| ---: | ---: | ---: | ---: | ---: |
| 365 | 96 | 92 | 0 | 0 |

Conclusion: 250 kHz offset did not help. The DC spike is wide enough that 250 kHz was insufficient clearance, and the -365 kHz interferer was the dominant impairment regardless.

## 8. 2026-04-29 Raw IQ Analysis In MATLAB

A 10-second raw IQ capture was taken from the LimeSDR using `lime_iq_capture.conf` and analyzed offline in MATLAB. This bypassed GNSS-SDR entirely and examined the raw samples to identify what the correlator is actually receiving.

Capture config: `configs_used/f9t_lime_current/lime_iq_capture.conf`
IQ data: `results/IQ_pairs/lime_iq_capture.dat` — 10 seconds at 2 Msps, gr_complex
Scripts: `scripts_used/matlab_analysis/`
Figures: `scripts_used/matlab_analysis/figures/`

### 8a. Spectrum Analysis

Script: `spectrum.m`
Figures: `PowerSpectrum.fig`, `DCSpike.fig`

| Metric | Value |
| --- | --- |
| Noise floor | -102.4 dB |
| Peak power | -68.9 dB |
| DC spike power | -70.4 dB |
| DC spike above floor | **32 dB** |
| Narrowband interferer offset | **-365 kHz** |
| Interferer above floor | ~15–17 dB |

The DC spike at 32 dB above floor exceeds the warning threshold of 20 dB significantly. The narrowband interferer at -365 kHz sits inside the GPS C/A code bandwidth (±511 kHz). 
### 8b. PRN Correlation

Script: `prn_correlation.m`
Figures: `PRNCorrelationMaps.fig`, `CN0Summary.fig`

| PRN | C/N₀ (dB-Hz) | Peak/Noise | Doppler (Hz) | Status |
| --- | ---: | ---: | ---: | --- |
| G03 | 33.7 | 1.84 | +2000 | Weak |
| G07 | 34.7 | 1.98 | -5000 | Weak |
| G08 | 36.3 | 2.30 | +3500 | Weak |
| G09 | 35.7 | 2.18 | -5000 | Weak |
| G16 | 36.7 | 2.38 | -4750 | Weak |
| G27 | 37.6 | 2.59 | -4000 | Found |

GPS signal confirmed present on all 6 PRNs. All straddling the 35 dB-Hz healthy threshold. Correlation maps show horizontal stripes across all code delays — the -365 kHz interferer adds structured noise across the entire code delay range, preventing a clean acquisition peak.

### 8c. Tracking Loop Simulation

Script: `tracking_sim.m`
Figure: `TrackingLoopSim.fig`
Target: PRN G27, Doppler -4000 Hz, PLL BW 40 Hz, 2000 ms simulation

| Metric | Value |
| --- | --- |
| Fraction locked | 25.6% |
| PLL discriminator | Saturated at ±0.25 cycles throughout |
| I/Q correlator | Indistinguishable — no coherent lock |
| Carrier frequency estimate | Monotonic drift — integrator winding up |

The 25.6% lock fraction matches the GNSS-SDR treadmill exactly. The correlator output is dominated by interference, so the discriminator has no valid input and the loop cannot pull in.

### 8d. Conclusion From IQ Analysis

The GPS signal is present but marginal. Interference — DC spike at 32 dB above floor and -365 kHz narrowband spur — corrupts every correlation integration period. The effective C/N₀ at the correlator is degraded below the stable tracking threshold by the interference, not by the signal being absent.

This conclusively explains why all six Phase 7 software experiments produced identical results: no software parameter can remove hardware-level interference from the correlator input.

## 9. Current Best Interpretation (updated after Phase 10)

### What is already solved

- assistance XML refresh and loading
- Lime open/init through SoapySDR
- live receiver-time advancement
- acquisition and focused PRN targeting
- GPS signal presence confirmed via raw IQ correlation
- root cause of tracking failure identified: IQ amplitude imbalance in LimeSDR hardware
- offline IQ correction confirmed working (0.00% imbalance after correction)
- tracking on corrected IQ file confirmed (PRN 03 and PRN 07 started tracking)

### What remains unsolved

- sustained tracking lock through bit synchronization
- NAV decode on Lime
- position fix on Lime
- longer corrected IQ capture (9.9 s is too short; need 2–3 min)

---

## 10. 2026-05-02 IQ Correction And File Source Tracking

Artifacts:

- Script: `scripts_used/matlab_analysis/iq_correct.m`
- Config: `configs_used/f9t_lime_current/lime_iq_corrected_file_source.conf`
- Corrected IQ file: `/home/alexgu2/gnss/captures/lime_iq_corrected.dat` (on hft02)

### 10a. IQ Imbalance Root Cause

Further analysis of the raw IQ capture revealed the dominant interference source is a **severe IQ amplitude imbalance** in the LimeSDR hardware:

| Metric | Value |
| --- | --- |
| IQ imbalance | 123% |
| Power ratio I/Q | -13 dB |
| Q/I amplitude ratio | 4.6× |
| DC spike above floor | 32 dB |

The Q channel carries 4.6× more power than I. This corrupts the PLL discriminator output on every 1ms integration period — the loop sees noise regardless of the signal level or any software parameter, which explains why all Phase 7 experiments produced identical zero bit-sync results.

### 10b. Offline IQ Correction In MATLAB

Script: `iq_correct.m` (in `scripts_used/matlab_analysis/`)

Steps applied:
1. Remove DC offset from both I and Q channels
2. Scale Q channel by factor `0.409` to match I amplitude

Result:

| Metric | Before | After |
| --- | --- | --- |
| IQ imbalance | 123% | **0.00%** |
| Power ratio I/Q | -13 dB | 0 dB |

The corrected samples were written to `lime_iq_corrected.dat`.

### 10c. File Source Tracking Run

The corrected `.dat` file was fed into GNSS-SDR using `File_Signal_Source` instead of the live LimeSDR. Key config parameters:

```ini
SignalSource.implementation=File_Signal_Source
SignalSource.filename=/home/alexgu2/gnss/captures/lime_iq_corrected.dat
SignalSource.item_type=gr_complex
SignalSource.sampling_frequency=2000000
```

PRNs targeted: G03 G07 G08 G09 G16 G27. Acquisition threshold: 2.6.

Result: **GNSS-SDR started tracking on PRN 03 and PRN 07.** This is the first confirmed tracking on corrected IQ data from the LimeSDR chain.

Limitation: the capture was only 9.9 seconds. No assistance XML was loaded. The run ended before bit sync or NAV decode could occur.

### 10d. Conclusion

The IQ imbalance was the root cause of all prior tracking failures. With the imbalance removed, the correlator forms a valid input and tracking starts. The next step is a longer capture (2–3 min) to allow bit sync and NAV decode.
