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

- `2.6` to `2.8` is the useful threshold range so far
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

- the earlier `t28_wide_tracking` summary at `20260428_075104` looks noisy and short-lived, with only `8` receiver-time lines and module/gateware warnings in the captured tail
- the sticky vs clean comparison is nearly identical — loop tightness is not the variable

Conclusion:

- sticky/gentle tracking did not fix loss of lock
- the current challenge is not getting starts, it is holding them

## 7. 2026-04-28 Single-Variable Sweep — Software Parameters Exhausted

All runs in this phase branched from `lime_gain20_10mhz_ephem_6ch_t26_clean.conf` with exactly one variable changed per run. LOAD_CONFIG was removed for all gain and DC offset runs to isolate variables cleanly.

Also fixed in all new configs: the base config had a silent XML path bug pointing to `f9t_tcp_latest/` instead of `f9t_latest/`. All Phase 7 configs use the correct path.

### 7a. Wide Tracking Loops

Config: `lime_gain20_10mhz_ephem_6ch_t26_wideloop.conf`

Changes from base:
- `pll_bw_hz`: `40.0` → `50.0`
- `fll_bw_hz`: `10.0` → `20.0`

| Receiver time | Tracking starts | Losses of lock | Bit sync | NAV |
| ---: | ---: | ---: | ---: | ---: |
| 401 | 103 | 99 | 0 | 0 |

Conclusion: loop bandwidth in either direction (wider here, tighter in Phase 6) has no effect on bit sync. Loop bandwidth is ruled out.

### 7b. LOAD_CONFIG Off

Config: `lime_gain20_noclockini_ephem_6ch_t26.conf`

Changes from base:
- `LOAD_CONFIG=...` removed from `osmosdr_args`
- XML paths corrected to `f9t_latest/`

| Receiver time | Tracking starts | Losses of lock | Bit sync | NAV |
| ---: | ---: | ---: | ---: | ---: |
| 361 | 95 | 91 | 0 | 0 |

Conclusion: the `10mhz_clock_working.ini` LMS7002M config file is neutral — removing it had no measurable effect. LOAD_CONFIG is ruled out.

### 7c. Gain Sweep

All three gain runs used LOAD_CONFIG off and corrected XML paths.

| Config | Actual RX Gain | Receiver time | Tracking starts | Losses of lock | Bit sync |
| --- | ---: | ---: | ---: | ---: | ---: |
| `lime_gain10_noclockini_ephem_6ch_t26.conf` | 52 dB | 403 | 99 | 95 | 0 |
| `lime_gain20_noclockini_ephem_6ch_t26.conf` | 58 dB | 304 | 82 | 79 | 0 |
| `lime_gain30_noclockini_ephem_6ch_t26.conf` | 61 dB | 350 | 90 | 86 | 0 |

Note: `gain=20` in the config maps to `58 dB` actual RX gain as reported by GNSS-SDR. The gr-osmosdr/SoapySDR mapping is nonlinear — always check the reported actual gain, not the config value.

Conclusion: gain across a 9 dB actual range had no effect on bit sync. Gain is ruled out.

### 7d. DC Offset Tuning

Config: `lime_gain20_dcoffset250_ephem_6ch_t26.conf`

Hypothesis: the LimeSDR in direct conversion mode produces a DC spike at 0 Hz. Tuning the LO to exactly L1 places the GPS signal at 0 Hz, directly on the spike. Offsetting the LO by 250 kHz moves the GPS signal away from DC.

Changes from base:
- `SignalSource.freq`: `1575420000` → `1575170000` (LO 250 kHz below L1)
- `InputFilter.IF`: `0` → `250000` (Freq_Xlating_FIR shifts signal back to 0)

| Receiver time | Tracking starts | Losses of lock | Bit sync | NAV |
| ---: | ---: | ---: | ---: | ---: |
| 365 | 96 | 92 | 0 | 0 |

Conclusion: DC offset did not help. Zero-IF DC contamination is ruled out as the primary cause, or the DC spike is not the dominant impairment at this signal level.

## 8. Current Best Interpretation

### What is already solved

- assistance XML refresh
- assistance XML loading
- Lime open/init through SoapySDR
- live receiver-time advancement
- acquisition
- focused PRN targeting

### What remains unsolved

- sustained lock through bit synchronization
- NAV decode on Lime
- final position fix on Lime

### What Phase 7 proved

Every software-accessible variable has now been tested in isolation:

- loop bandwidth (both tighter and wider)
- LOAD_CONFIG / clock INI
- gain (9 dB range of actual RX gain)
- LO offset / DC spike mitigation

None moved the needle. The start/loss count is stable at roughly 80–100 starts and nearly identical losses across every experiment. This level of consistency across independent variables points to a hardware floor that software cannot reach.

The RTL-SDR decoded 227 NAV messages on the same antenna path. The Lime has zero across all runs. The difference is the RF frontend. The most likely explanation is that the effective C/N₀ at the Lime correlator input is below the threshold needed for stable tracking, due to the Lime's noise figure combined with the absence of a hardware bandpass filter allowing wideband noise into the front end.

### Recommended next step

Hardware GPS L1 bandpass filter before the LimeSDR LNAW input. This is the only remaining lever. A filter centered on 1575.42 MHz with a bandwidth of ≤10 MHz would reject wideband noise that the software filter cannot remove, directly improving the effective C/N₀ at the correlators.
