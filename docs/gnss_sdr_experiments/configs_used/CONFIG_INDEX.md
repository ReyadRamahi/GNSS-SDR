# Config Index

This index points to the config families that matter most for continuing the work.

## Current Priority

If you are continuing the active Lime debugging, start in:

- `f9t_lime_current/`

The best current base config to branch from is:

- `f9t_lime_current/lime_gain20_noclockini_ephem_6ch_t26.conf`

Note: the older `t26_clean` config has a silent XML path bug pointing to `f9t_tcp_latest/` instead of `f9t_latest/`. Use the `noclockini` version as the new clean base — it has the correct XML path and LOAD_CONFIG has been confirmed neutral (see `EXPERIMENT_LOG.md` Phase 7b).

## Ruled-Out Config Families (Do Not Re-Test Without New Hypothesis)

These configs have been run and their key variable confirmed to have no effect on bit sync:

| Config | Variable tested | Result |
| --- | --- | --- |
| `lime_gain20_10mhz_ephem_6ch_t26_wideloop.conf` | wider PLL/FLL loops | no effect |
| `lime_gain20_noclockini_ephem_6ch_t26.conf` | LOAD_CONFIG removed | no effect |
| `lime_gain10_noclockini_ephem_6ch_t26.conf` | gain=10 (52 dB actual) | no effect |
| `lime_gain30_noclockini_ephem_6ch_t26.conf` | gain=30 (61 dB actual) | no effect |
| `lime_gain20_dcoffset250_ephem_6ch_t26.conf` | LO offset 250 kHz | no effect |

## Folder Summary

### `baseline/`

- `limesdr_reference.conf` — older reference Lime config
- `limesdr_l1.conf` — basic Lime L1 config
- `limesdr_l1_balanced.conf` — earlier balanced Lime config before the latest focused F9T work
- `limesdr_l5.conf` — Lime L5 experiment config, not part of the main L1 workflow
- `limesdr_marty_test.conf` — ad hoc Lime test config kept for reference

### `agnss/`

- `limesdr_l1_agnss.conf` — older Lime L1 config with assistance XML
- `limesdr_l1_balanced_agnss.conf` — balanced Lime config with assistance XML
- `limesdr_l1_balanced_f9t_tcp_latest_agnss.conf` — older F9T TCP based AGNSS config retained as reference

### `f9t_lime_current/`

See `f9t_lime_current/README.md` for the most useful file-by-file notes.

Pre-2026-04-28 base configs (XML path bug — points to `f9t_tcp_latest/`):

- `lime_gain20_10mhz_ephem_focus_threshold26.conf`
- `lime_gain20_10mhz_ephem_focus_threshold28.conf`
- `lime_gain20_10mhz_ephem_6ch_t26_clean.conf`
- `lime_gain20_10mhz_ephem_6ch_t26_sticky_tracking.conf`
- `lime_gain20_10mhz_ephem_6ch_t28_wide_tracking.conf`

2026-04-28 single-variable experiment configs (XML path correct, use these as base):

- `lime_gain20_10mhz_ephem_6ch_t26_wideloop.conf` — wide loops experiment
- `lime_gain20_noclockini_ephem_6ch_t26.conf` — LOAD_CONFIG off, current clean base
- `lime_gain10_noclockini_ephem_6ch_t26.conf` — gain=10 experiment
- `lime_gain30_noclockini_ephem_6ch_t26.conf` — gain=30 experiment
- `lime_gain20_dcoffset250_ephem_6ch_t26.conf` — DC offset 250 kHz experiment
- `lime_iq_capture.conf` — raw IQ dump config, 10 seconds at 2 Msps, no tracking

### `rtl_reference/`

- `rtlsdr_l1.conf` — base RTL L1 reference
- `rtlsdr_l1_harvest.conf` — RTL config used to harvest assistance-related data
- `rtlsdr_l1_track10_g42.conf`
- `rtlsdr_l1_track10_g45.conf`
- `rtlsdr_l1_track10_g49.conf`
  - targeted RTL tracking configs tied to `results/logs/rtl_track/run_summary.txt`
  - `g45` is the most important reference — it produced 4 bit sync locks and 227 NAV messages

### `sweeps/`

- `msps/` — sample-rate sweep configs for Lime comparisons

Generated per-run sweep configs also live alongside the sweep logs in:

- `../results/logs/lime_sweeps/v1/`
- `../results/logs/lime_sweeps/v2/`
- `../results/logs/lime_sweeps/v3/`

## MATLAB Analysis Scripts And Figures

All MATLAB work lives in `scripts_used/matlab_analysis/`.

### Scripts

| Script | Purpose |
| --- | --- |
| `spectrum.m` | Power spectrum, DC spike magnitude, narrowband interference identification |
| `prn_correlation.m` | PRN correlation maps and C/N₀ estimates for all ephemeris PRNs |
| `tracking_sim.m` | PLL/DLL tracking loop simulation on raw IQ, lock fraction, drift diagnosis |
| `rtl_vs_lime.m` | Side-by-side RTL vs Lime comparison (requires separate RTL capture) |

Run order: capture IQ on hft02 using `lime_iq_capture.conf` → download `.dat` → run `spectrum.m` → run `prn_correlation.m` → update `PRN` and `DOPPLER_HZ` in `tracking_sim.m` from `prn_correlation.m` results → run `tracking_sim.m`.

### Figures From 2026-04-29 Lime IQ Capture

All saved in `scripts_used/matlab_analysis/figures/`:

| Figure | What it shows |
| --- | --- |
| `PowerSpectrum.fig` | Full ±1 MHz band view — noise floor, DC spike, GPS band edges, -365 kHz interferer |
| `DCSpike.fig` | Zoomed ±100 kHz — DC spike 32 dB above noise floor |
| `PRNCorrelationMaps.fig` | Acquisition correlation maps for all 6 ephemeris PRNs — horizontal stripes show interference corrupting code delay axis |
| `CN0Summary.fig` | Per-PRN C/N₀ bar chart — all PRNs 33–38 dB-Hz, straddling healthy threshold |
| `TrackingLoopSim.fig` | G27 tracking loop simulation — 25.6% lock fraction, PLL discriminator saturated throughout |

### Key Numbers From This Analysis

| Metric | Value | Interpretation |
| --- | --- | --- |
| DC spike above floor | 32 dB | Severe — threshold for concern is 20 dB |
| Narrowband interferer | -365 kHz offset | Inside GPS band, likely USB 3.0 harmonic |
| Best PRN C/N₀ | 37.6 dB-Hz (G27) | Marginal — healthy threshold is 35 dB-Hz |
| Worst PRN C/N₀ | 33.7 dB-Hz (G03) | Below healthy threshold |
| Tracking lock fraction | 25.6% (G27) | Cannot hold lock — matches GNSS-SDR behavior |

### IQ Capture File

The 2026-04-29 capture is committed to the repo at `results/IQ_pairs/lime_iq_capture.dat` (gr_complex, 2 Msps, 10 seconds, ~160 MB). To reproduce or replace the capture, run a fresh capture on hft02 using `lime_iq_capture.conf` and save the output `.dat` to `results/IQ_pairs/`.
