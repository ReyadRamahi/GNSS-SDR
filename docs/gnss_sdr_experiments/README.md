# GNSS-SDR / LimeSDR / F9T Experiment Docs

## Start with the latest run

- [Experiment results](EXPERIMENT_RESULTS.md) documents the November 23, 2026 CT LimeSDR recording and offline GPS fix.
- [Docker replay](../../docker/gnss-sdr/README.md) shows how to build the receiver and replay a verified copy of the recording.
- [MATLAB RINEX cross-check](scripts_used/matlab_analysis/solve_lime_rinex.m) solves the receiver position from exported observations and ephemerides.

## Find earlier work

| Looking for | Open |
| --- | --- |
| Live F9T assistance and receiver workflow | [Workflow](WORKFLOW.md) |
| Project goals and earlier results | [Project summary](GNSS_SDR_PROJECT_SUMMARY.md) and [experiment log](EXPERIMENT_LOG.md) |
| Receiver configuration families | [Config index](configs_used/CONFIG_INDEX.md) |
| Capture, MATLAB, and F9T scripts | [Scripts index](scripts_used/README.md) |
| Logs, assistance data, and run evidence | [Results index](results/README.md) |
| 10 MHz reference-lock investigation | [External reference audit](LIMESDR_EXTERNAL_REFERENCE_AUDIT.md) |
| November 13 standalone positioning investigation | [TOW 14052 report](RX1H_14052_BOOTSTRAP_RESULTS.md) |

<details>
<summary>May 2026 observations and archive notes</summary>

## May 2026 observations (historical)

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

## May 2 IQ correction handoff

[Captured-file IQ correction workflow](LIMESDR_IQ_CORRECTED_FILE_SOURCE_HANDOFF_20260502.md)

## Folder Map

- `configs_used/`
  - GNSS-SDR config files grouped into `baseline/`, `agnss/`, `f9t_lime_current/`, `rtl_reference/`, and `sweeps/`
- `scripts_used/`
  - helper scripts grouped into generic `capture_and_sweep/`, older `f9t_refresh/`, and current `f9t_lime_current/`
- `results/assist/`
  - assistance XML grouped by source: current local F9T, older F9T TCP reference, RTL-harvested XML, and raw inputs
- `results/logs/`
  - logs grouped into baseline runs, current F9T+Lime focused runs, Lime sweep phases, RTL reference runs, and F9T refresh logs

## Artifacts from earlier runs

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

</details>
