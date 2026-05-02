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

- `lime_iq_corrected_file_source.conf`
  - feeds the offline IQ-corrected `.dat` file into GNSS-SDR via `File_Signal_Source`
  - IQ correction (DC removal + Q scaling by 0.409) is baked into the `.dat` file — no in-config correction needed
  - update `SignalSource.filename` to point at the corrected capture before each run
  - update AGNSS XML paths to `results/assist/f9t_latest/` before running

## How To Use This Folder

- for file-source tracking experiments, start from `lime_iq_corrected_file_source.conf`
- for live LimeSDR experiments, branch from `lime_gain20_10mhz_ephem_6ch_t26_clean.conf`
- compare against the threshold and tracking-variant configs one variable at a time
- use the RF sanity configs only to confirm front-end behavior, not as final position-attempt configs
