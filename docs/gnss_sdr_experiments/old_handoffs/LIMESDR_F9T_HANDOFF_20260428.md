# LimeSDR + F9T GNSS-SDR Handoff Notes

Date: 2026-04-28

## Current State

The LimeSDR path is alive but still not solved.

Working:

- F9T XML refresh works.
- GNSS-SDR loads F9T XML assistance.
- LimeSDR opens through `gr-osmosdr` / `SoapySDR`.
- receiver time advances during live runs
- acquisition starts
- focused PRN restriction now works
- tracking starts on the correct ephemeris PRNs

Not working yet:

- tracking bit synchronization lock
- GPS NAV decode from Lime
- position fix from Lime

Current bottleneck:

- tracking stability after acquisition

## Best Current Evidence

Most useful current files:

- current assist snapshot:
  - `results/assist/f9t_latest/`
  - `results/assist/f9t_latest/README_CURRENT_XML.txt`
- current run configs:
  - `configs_used/f9t_lime_current/`
- current run summaries:
  - `results/logs/f9t_lime_current/`
- current helper scripts:
  - `scripts_used/f9t_lime_current/`

The latest local F9T refresh metadata records:

- UTC generated: `Tue Apr 28 07:16:34 AM UTC 2026`
- GPS satellites: `G03 G07 G08 G09 G16 G27`
- XML count: `<count>6</count>`

## Most Informative Current Runs

Focused-threshold runs:

- `ephem_focus_threshold26_20260428_074109_summary.txt`
  - receiver time: `282`
  - tracking starts: `22`
  - losses of lock: `21`
  - bit sync: `0`
- `ephem_focus_threshold28_20260428_073347_summary.txt`
  - receiver time: `259`
  - tracking starts: `5`
  - losses of lock: `5`
  - bit sync: `0`
- `ephem_focus_threshold30_20260428_073152_summary.txt`
  - tracking starts: `0`
- `ephem_focus_threshold35_20260428_072802_summary.txt`
  - tracking starts: `0`

Focused 6-channel runs:

- `ephem_6ch_t26_clean_20260428_074552_summary.txt`
  - receiver time: `163`
  - tracking starts: `38`
  - losses of lock: `35`
  - bit sync: `0`
  - PRNs attempted most often: `27`, `08`, `03`, `16`, `09`, `07`
- `ephem_6ch_t26_sticky_tracking_20260428_074838_summary.txt`
  - receiver time: `144`
  - tracking starts: `37`
  - losses of lock: `36`
  - bit sync: `0`
- `ephem_6ch_t28_wide_tracking_20260428_075114_summary.txt`
  - receiver time: `42`
  - tracking starts: `7`
  - losses of lock: `4`
  - bit sync: `0`

Practical takeaway:

- threshold `2.6` is still the most useful starting point
- threshold `2.8` is usable but weaker
- `3.0+` is too strict in the current focused setup
- sticky/gentle tracking did not solve the problem

## Best Config To Branch From

Use this as the main base for next experiments:

- `configs_used/f9t_lime_current/lime_gain20_10mhz_ephem_6ch_t26_clean.conf`

Use these as comparison references:

- `configs_used/f9t_lime_current/lime_gain20_10mhz_ephem_6ch_t26_sticky_tracking.conf`
- `configs_used/f9t_lime_current/lime_gain20_10mhz_ephem_6ch_t28_wide_tracking.conf`
- `configs_used/f9t_lime_current/lime_gain20_10mhz_ephem_focus_threshold26.conf`
- `configs_used/f9t_lime_current/lime_gain20_10mhz_ephem_focus_threshold28.conf`

## Recommended Next Experiments

Run one variable at a time:

1. Wider tracking loops from the `t26_clean` base.
2. Gain A/B test while keeping PRN list and threshold fixed.
3. External `10 MHz` `LOAD_CONFIG` on versus off.
4. GPS L1 filter on versus off.
5. Only after stable bit sync appears, consider relaxing PRN focus or increasing channels.

## Run Discipline

- Keep `SignalSource.dump=false` during position attempts.
- Run in a clean per-run directory.
- Prefer a direct or terminal-like launch if tmux/nohup piping behaves oddly.
- Change one variable per run.
- Do not change XML, gain, clock, acquisition, and tracking together.

## Bottom-Line Interpretation

The problem is no longer dead RF or missing ephemeris. The LimeSDR receives, enters live processing, acquires, and starts tracking on expected satellites, but it cannot hold lock long enough to reach bit sync, NAV decode, or a fix.
