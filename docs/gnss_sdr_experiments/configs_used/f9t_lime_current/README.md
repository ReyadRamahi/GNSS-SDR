# Current F9T + Lime Configs

These are the configs most relevant to the current unresolved Lime tracking issue.

## Files

- `lime_gain20_10mhz_ephem_focus_threshold26.conf`
  - focused-PRN configuration for threshold `2.6`
- `lime_gain20_10mhz_ephem_focus_threshold28.conf`
  - focused-PRN configuration for threshold `2.8`
- `lime_gain20_10mhz_ephem_6ch_t26_clean.conf`
  - current best base config for follow-up testing
- `lime_gain20_10mhz_ephem_6ch_t26_sticky_tracking.conf`
  - tests gentler or stickier tracking behavior
- `lime_gain20_10mhz_ephem_6ch_t28_wide_tracking.conf`
  - tests wider tracking-loop behavior
- `lime_gain20_latestxml_processing_only.conf`
  - processing-only check using the latest XML path
- `lime_gain20_latestxml_processing_only_10mhz_clock.conf`
  - processing-only check with the external `10 MHz` path enabled
- `lime_rf_sanity_gain20.conf`
  - RF sanity check at gain `20`
- `lime_rf_sanity_gain61.conf`
  - RF sanity check at gain `61`

## How To Use This Folder

- branch new Lime tracking tests from `lime_gain20_10mhz_ephem_6ch_t26_clean.conf`
- compare against the threshold and tracking-variant configs one variable at a time
- use the RF sanity configs only to confirm front-end behavior, not as final position-attempt configs
