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

Conclusion:

- sticky/gentle tracking did not fix loss of lock
- the current challenge is not getting starts, it is holding them

## 7. Current Best Interpretation

What is already solved:

- assistance XML refresh
- assistance XML loading
- Lime open/init through `SoapySDR`
- live receiver-time advancement
- acquisition
- focused PRN targeting

What remains unsolved:

- sustained lock through bit synchronization
- NAV decode on Lime
- final position fix on Lime

Most likely next experiment axes:

1. wider tracking loops
2. gain A/B tests
3. `10 MHz` `LOAD_CONFIG` on/off
4. GPS L1 filter on/off
