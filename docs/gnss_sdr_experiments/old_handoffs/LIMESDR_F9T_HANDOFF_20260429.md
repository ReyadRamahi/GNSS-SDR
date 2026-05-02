# LimeSDR + F9T Handoff — 2026-04-29

## Current State

The LimeSDR path is alive but not yet solved.

### Working

- F9T XML refresh on local serial path (`hft02`)
- GNSS-SDR loads F9T XML assistance successfully
- LimeSDR opens through `gr-osmosdr` / `SoapySDR`
- Receiver time advances during live runs
- Acquisition works at threshold `2.6`
- Focused PRN restriction works when all four channel settings are set together
- Tracking starts on the correct ephemeris PRNs
- Raw IQ analysis confirms GPS signal is present on all 6 ephemeris PRNs

### Not Working Yet

- Tracking bit synchronization lock
- GPS NAV decode from Lime
- Position fix from Lime

### Current Blocker

Raw IQ analysis identifies two hardware-level interference sources corrupting the correlator input:

1. **DC spike 32 dB above the noise floor** — severe zero-IF contamination
2. **Narrowband interferer at -365 kHz inside the GPS band** — likely USB 3.0 interference from the host

The GPS signal is present (C/N₀ 33–38 dB-Hz across all 6 PRNs) but the interference prevents the correlator from forming a clean peak. The tracking loop sees noise instead of signal and cannot hold lock.

---

## Today's Experiment Summary (2026-04-28)

### Phase 1 — Software Parameter Sweep

Six controlled single-variable experiments, all producing the same result:

| Experiment | Key change | Starts | Losses | Bit sync |
| --- | --- | ---: | ---: | ---: |
| Wide loops | `pll_bw_hz` 40→50, `fll_bw_hz` 10→20 | 103 | 99 | 0 |
| LOAD_CONFIG off | Removed clock INI from `osmosdr_args` | 95 | 91 | 0 |
| gain=10 | 52 dB actual | 99 | 95 | 0 |
| gain=20 no INI | 58 dB actual | 82 | 79 | 0 |
| gain=30 | 61 dB actual | 90 | 86 | 0 |
| DC offset 250 kHz | LO at L1−250 kHz, `IF=250000` | 96 | 92 | 0 |

### Phase 2 — Raw IQ Analysis in MATLAB

A 10-second IQ capture was taken from the LimeSDR and analyzed with four MATLAB scripts. Saved figures are in `scripts_used/matlab_analysis/figures/`.

**Spectrum analysis (`spectrum.m` → `PowerSpectrum.fig`, `DCSpike.fig`):**
- Noise floor: -102.4 dB
- DC spike: -70.4 dB → **32 dB above noise floor** (threshold for concern is 20 dB)
- Narrowband interferer at **-365 kHz offset** from L1, ~15–17 dB above noise floor
- Interferer sits inside the GPS C/A code bandwidth (±511 kHz)

**PRN correlation (`prn_correlation.m` → `PRNCorrelationMaps.fig`, `CN0Summary.fig`):**

| PRN | C/N₀ (dB-Hz) | Peak/Noise | Status |
| --- | ---: | ---: | --- |
| G03 | 33.7 | 1.84 | Weak |
| G07 | 34.7 | 1.98 | Weak |
| G08 | 36.3 | 2.30 | Weak |
| G09 | 35.7 | 2.18 | Weak |
| G16 | 36.7 | 2.38 | Weak |
| G27 | 37.6 | 2.59 | Found |

All PRNs straddling the 35 dB-Hz healthy tracking threshold. Correlation maps show horizontal stripes across all code delays — interference corrupting the entire code delay range.

**Tracking loop simulation (`tracking_sim.m` → `TrackingLoopSim.fig`) on G27:**
- Fraction locked: 25.6%
- I and Q prompt correlator outputs indistinguishable — loop never achieved coherent lock
- PLL discriminator saturated at ±0.25 cycle limits throughout
- Carrier frequency estimate drifted monotonically — loop integrator winding up with no valid signal

---

## Also Fixed Today

The base config had a silent XML path bug: `AGNSS` paths pointed to `f9t_tcp_latest/` instead of `f9t_latest/`. All new configs use the correct path.

---

## Artifacts Created Today

GNSS-SDR configs in `configs_used/f9t_lime_current/`:

- `lime_gain20_10mhz_ephem_6ch_t26_wideloop.conf`
- `lime_gain20_noclockini_ephem_6ch_t26.conf`
- `lime_gain10_noclockini_ephem_6ch_t26.conf`
- `lime_gain30_noclockini_ephem_6ch_t26.conf`
- `lime_gain20_dcoffset250_ephem_6ch_t26.conf`
- `lime_iq_capture.conf`

Raw IQ data in `results/IQ_pairs/`:

- `lime_iq_capture.dat` — 10-second capture at 2 Msps, gr_complex, ~160 MB

MATLAB scripts in `scripts_used/matlab_analysis/`:

- `spectrum.m`
- `prn_correlation.m`
- `tracking_sim.m`
- `rtl_vs_lime.m`

Saved figures in `scripts_used/matlab_analysis/figures/`:

- `PowerSpectrum.fig`
- `DCSpike.fig`
- `PRNCorrelationMaps.fig`
- `CN0Summary.fig`
- `TrackingLoopSim.fig`

---

## Most Relevant Current Artifacts

- Current local F9T XML: `results/assist/f9t_latest/`
- Generation metadata: `results/assist/f9t_latest/README_CURRENT_XML.txt`
- Current focused Lime configs: `configs_used/f9t_lime_current/`
- Today's run logs: `results/logs/f9t_lime_current/`
- MATLAB scripts: `scripts_used/matlab_analysis/`
- MATLAB figures: `scripts_used/matlab_analysis/figures/`
- IQ capture config: `configs_used/f9t_lime_current/lime_iq_capture.conf`
- IQ capture data: `results/IQ_pairs/lime_iq_capture.dat`

## Latest F9T Refresh Metadata

- UTC generated: `Tue Apr 28 07:16:34 AM UTC 2026`
- GPS satellites: `G03 G07 G08 G09 G16 G27`
- XML count: `<count>6</count>`

## Read In This Order

1. This file
2. `WORKFLOW.md`
3. `EXPERIMENT_LOG.md`
4. `configs_used/CONFIG_INDEX.md`
5. `GNSS_SDR_PROJECT_SUMMARY.md`