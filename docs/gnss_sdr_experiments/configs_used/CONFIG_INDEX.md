# Config Index

This index points to the config families that matter most for continuing the work.

## Current Priority

If you are continuing the active Lime debugging, start in:

- `f9t_lime_current/`

The best current base config to branch from is:

- `f9t_lime_current/lime_gain20_10mhz_ephem_6ch_t26_clean.conf`

## Folder Summary

### `baseline/`

- `limesdr_reference.conf`
  - older reference Lime config
- `limesdr_l1.conf`
  - basic Lime L1 config
- `limesdr_l1_balanced.conf`
  - earlier balanced Lime config before the latest focused F9T work
- `limesdr_l5.conf`
  - Lime L5 experiment config, not part of the main L1 workflow
- `limesdr_marty_test.conf`
  - ad hoc Lime test config kept for reference

### `agnss/`

- `limesdr_l1_agnss.conf`
  - older Lime L1 config with assistance XML
- `limesdr_l1_balanced_agnss.conf`
  - balanced Lime config with assistance XML
- `limesdr_l1_balanced_f9t_tcp_latest_agnss.conf`
  - older F9T TCP based AGNSS config retained as reference

### `f9t_lime_current/`

See `f9t_lime_current/README.md` for the most useful file-by-file notes.

Important files:

- `lime_gain20_10mhz_ephem_focus_threshold26.conf`
- `lime_gain20_10mhz_ephem_focus_threshold28.conf`
- `lime_gain20_10mhz_ephem_6ch_t26_clean.conf`
- `lime_gain20_10mhz_ephem_6ch_t26_sticky_tracking.conf`
- `lime_gain20_10mhz_ephem_6ch_t28_wide_tracking.conf`

### `rtl_reference/`

- `rtlsdr_l1.conf`
  - base RTL L1 reference
- `rtlsdr_l1_harvest.conf`
  - RTL config used to harvest assistance-related data
- `rtlsdr_l1_track10_g42.conf`
- `rtlsdr_l1_track10_g45.conf`
- `rtlsdr_l1_track10_g49.conf`
  - targeted RTL tracking configs tied to `results/logs/rtl_track/run_summary.txt`

### `sweeps/`

- `msps/`
  - sample-rate sweep configs for Lime comparisons

Generated per-run sweep configs also live alongside the sweep logs in:

- `../results/logs/lime_sweeps/v1/`
- `../results/logs/lime_sweeps/v2/`
- `../results/logs/lime_sweeps/v3/`
