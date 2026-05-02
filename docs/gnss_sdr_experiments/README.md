# GNSS-SDR / LimeSDR / F9T Experiment Docs

Start here. This folder now groups the GNSS-SDR GPS L1 C/A work by purpose:

- what the project is trying to do
- what the current blocker is
- which configs and scripts were used
- which assist XML and logs back up the conclusions

## Current Bottom Line

- Local F9T XML refresh on `hft02` works.
- GNSS-SDR loads the assistance XML successfully.
- LimeSDR-USB opens through `gr-osmosdr` / `SoapySDR`.
- Receiver time advances during live runs.
- Acquisition works.
- Focused PRN restriction works when `Channels_1C.count`, `Channel.signal`, `Channels.in_acquisition`, and `ChannelN.satellite` are all set together.
- Tracking starts on the correct ephemeris PRNs.
- **Root cause identified: LimeSDR has severe IQ amplitude imbalance (Q channel 4.6x stronger than I, -13 dB power ratio).** This was corrupting the PLL discriminator on every 1ms integration period and explains why no software parameter change ever held lock.
- **IQ correction confirmed working:** offline MATLAB correction (`iq_correct.m`) reduced imbalance from 123% to 0.00%. Corrected file fed into GNSS-SDR via `File_Signal_Source` — tracking started on PRN 03 and PRN 07.
- Remaining blocker: corrected capture was only 9.9 seconds — too short for bit sync or NAV decode. Need a 2–3 minute corrected capture.

## Read In This Order

1. [LIMESDR_IQ_CORRECTED_FILE_SOURCE_HANDOFF_20260502.md](LIMESDR_IQ_CORRECTED_FILE_SOURCE_HANDOFF_20260502.md) ← most recent
2. [WORKFLOW.md](WORKFLOW.md)
3. [EXPERIMENT_LOG.md](EXPERIMENT_LOG.md)
4. [configs_used/CONFIG_INDEX.md](configs_used/CONFIG_INDEX.md)
5. [GNSS_SDR_PROJECT_SUMMARY.md](GNSS_SDR_PROJECT_SUMMARY.md)

## Folder Map

- `configs_used/`
  - GNSS-SDR config files grouped into `baseline/`, `agnss/`, `f9t_lime_current/`, `rtl_reference/`, and `sweeps/`
- `scripts_used/`
  - helper scripts grouped into generic `capture_and_sweep/`, older `f9t_refresh/`, and current `f9t_lime_current/`
- `results/assist/`
  - assistance XML grouped by source: current local F9T, older F9T TCP reference, RTL-harvested XML, and raw inputs
- `results/logs/`
  - logs grouped into baseline runs, current F9T+Lime focused runs, Lime sweep phases, RTL reference runs, and F9T refresh logs

## Most Relevant Current Artifacts

- **IQ correction script:** `scripts_used/matlab_analysis/iq_correct.m`
- **IQ-corrected file source config:** `configs_used/f9t_lime_current/lime_iq_corrected_file_source.conf`
- Current local F9T XML snapshot:
  - `results/assist/f9t_latest/`
  - generation metadata is in `results/assist/f9t_latest/README_CURRENT_XML.txt`
- Current focused Lime configs:
  - `configs_used/f9t_lime_current/`
- Current focused run summaries:
  - `results/logs/f9t_lime_current/`
- Current local F9T helper scripts:
  - `scripts_used/f9t_lime_current/`

## Notes On The Reorganization

- The older `f9t_refresh_workflow/` category has been split into the main `configs_used/`, `scripts_used/`, and `results/` trees so future work is organized by artifact type instead of by one historical workflow.
- No non-Markdown file contents were edited. Non-Markdown artifacts were only moved into clearer folders.
