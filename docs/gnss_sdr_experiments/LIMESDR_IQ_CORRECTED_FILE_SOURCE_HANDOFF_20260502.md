# Handoff: IQ-Corrected File Source Experiment — 2026-05-02

## What We Found Today

Raw IQ analysis revealed the LimeSDR has a **severe IQ amplitude imbalance**:

- Q channel has 4.6× more power than I channel
- IQ imbalance: ~123%
- Power ratio I/Q: -13 dB
- DC spike: 32 dB above noise floor

This corrupts the PLL discriminator on every 1ms integration period and is the primary reason tracking never reaches bit sync regardless of any software parameter change.

## What We Did

Applied a manual offline IQ correction in MATLAB using `iq_correct.m`:

- Removed DC offset from both I and Q channels
- Scaled Q channel by factor `0.409` to match I amplitude

Result: IQ imbalance dropped from 123% to **0.00%**. Correction confirmed working.

The corrected IQ file was fed into GNSS-SDR using `File_Signal_Source` instead of the live LimeSDR. GNSS-SDR ran through the file and started tracking on **PRN 03 and PRN 07** — but the run only covered 9.9 seconds of data and had no assistance XML loaded, so there was not enough time for bit sync or NAV decode.

## What Still Needs To Happen

### Longer IQ Capture

9.9 seconds is too short even with assistance. Need at least 2–3 minutes for acquisition, tracking, and NAV decode to complete.

## Files Involved

| File | Location | Status |
| --- | --- | --- |
| `iq_correct.m` | `scripts_used/matlab_analysis/` | Done — produces corrected .dat |
| `lime_iq_corrected.dat` | `/home/alexgu2/gnss/captures/` | On hft02, ready to use |
| `lime_iq_corrected_file_source.conf` | `configs_used/f9t_lime_current/` (repo) / `/home/alexgu2/gnss/configs/` (hft02) | Needs XML path fixed |
| `lime_iq_capture.conf` | `configs_used/f9t_lime_current/` | Use for longer capture |

## Exact Next Run

1. Capture a longer corrected IQ file (3 min minimum)
2. Apply `iq_correct.m` to the new longer file
3. Upload corrected file to `/home/alexgu2/gnss/captures/lime_iq_corrected_long.dat`
4. Update `lime_iq_corrected_file_source.conf` filename to point at new file
5. Fix the AGNSS XML path in `lime_iq_corrected_file_source.conf` to point at `results/assist/f9t_latest/`
6. Run GNSS-SDR and watch for:

```
tracking bit synchronization locked
New GPS NAV message received
```

That is the breakthrough we are looking for.

## Key Config Parameters

```ini
SignalSource.implementation=File_Signal_Source
SignalSource.filename=/home/alexgu2/gnss/captures/lime_iq_corrected.dat
SignalSource.item_type=gr_complex
SignalSource.sampling_frequency=2000000
```

PRNs currently targeted: G03 G07 G08 G09 G16 G27

Acquisition threshold: 2.6

IQ correction is already baked into the `.dat` file — no additional correction needed in the GNSS-SDR config.

## Context: Why This Matters

Every prior experiment (Phase 7, loop sweeps, gain sweeps, DC offset tuning, hardware calibration attempts) failed because the IQ imbalance was degrading the correlator input at the hardware level. Software parameters cannot fix a corrupted discriminator input. The offline MATLAB correction bypasses the hardware defect entirely and is the first path to a clean correlator input from the LimeSDR chain.

## Previous Handoff

`old_handoffs/LIMESDR_IQ_CALIBRATION_HANDOFF_20260430.md` — hardware calibration via `skipCal=false` / `CALIBRATE` args (that path was superseded by the offline MATLAB correction confirmed today).
