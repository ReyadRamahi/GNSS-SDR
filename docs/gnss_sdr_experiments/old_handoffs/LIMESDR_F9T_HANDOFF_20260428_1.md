# LimeSDR + F9T Handoff — 2026-04-28

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

### Not Working Yet

- Tracking bit synchronization lock
- GPS NAV decode from Lime
- Position fix from Lime

### Current Blocker

All software-accessible variables have been tested and ruled out as the primary cause. The tracking treadmill — acquire, start, lose lock, repeat — persists regardless of loop bandwidth, gain, clock INI, or LO offset. The remaining lever is RF signal quality at the correlator input, which requires a hardware L1 bandpass filter before the LimeSDR.

---

## Today's Experiment Summary (2026-04-28)

Six controlled experiments were run today, each changing exactly one variable from the `t26_clean` base config.

| Experiment | Key change | Starts | Losses | Bit sync |
| --- | --- | ---: | ---: | ---: |
| Wide loops | `pll_bw_hz` 40→50, `fll_bw_hz` 10→20 | 103 | 99 | 0 |
| LOAD_CONFIG off | Removed clock INI from `osmosdr_args` | 95 | 91 | 0 |
| gain=10 | `gain=10` → 52 dB actual | 99 | 95 | 0 |
| gain=20 no INI | `gain=20` → 58 dB actual, no clock INI | 82 | 79 | 0 |
| gain=30 | `gain=30` → 61 dB actual | 90 | 86 | 0 |
| DC offset 250 kHz | LO at L1−250 kHz, `IF=250000` | 96 | 92 | 0 |

### What Was Ruled Out Today

- Loop bandwidth (both wider and tighter directions tested across multiple prior runs)
- `LOAD_CONFIG` / clock INI (neutral — removing it had no effect)
- Gain across a 9 dB actual range (52–61 dB)
- DC offset / zero-IF contamination

### What This Means

The start/loss count is remarkably stable across every experiment — roughly 80–100 starts and nearly identical losses regardless of the parameter changed. That consistency across independent variables points to a floor that software cannot move. The RTL-SDR reached bit sync and NAV decode on the same antenna path, which rules out the antenna and GNSS-SDR itself. The gap is the Lime frontend noise figure combined with the absence of a hardware L1 bandpass filter.

---

## Also Fixed Today

The base config had a silent XML path bug: `AGNSS` paths pointed to `f9t_tcp_latest/` (the old, unreliable TCP source) instead of `f9t_latest/` (the current local F9T snapshot). All new configs created today use the correct path. The old base configs in `f9t_lime_current/` still have the wrong path and should not be used without fixing this first.

---

## Configs Created Today

All in `configs_used/f9t_lime_current/`:

- `lime_gain20_10mhz_ephem_6ch_t26_wideloop.conf`
- `lime_gain20_noclockini_ephem_6ch_t26.conf`
- `lime_gain10_noclockini_ephem_6ch_t26.conf`
- `lime_gain30_noclockini_ephem_6ch_t26.conf`
- `lime_gain20_dcoffset250_ephem_6ch_t26.conf`

---

## Recommended Next Step

Hardware L1 bandpass filter before the LimeSDR LNAW input. This is the only remaining lever. A filter with a passband centered on 1575.42 MHz and a bandwidth of ≤10 MHz would reject wideband noise and interference that the software filter cannot remove, improving the effective C/N₀ at the correlators. Ask the professor whether one is available in the lab.

---

## Most Relevant Current Artifacts

- Current local F9T XML snapshot: `results/assist/f9t_latest/`
- Generation metadata: `results/assist/f9t_latest/README_CURRENT_XML.txt`
- Current focused Lime configs: `configs_used/f9t_lime_current/`
- Today's run logs: `results/logs/f9t_lime_current/`
- Current helper scripts: `scripts_used/f9t_lime_current/`

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
