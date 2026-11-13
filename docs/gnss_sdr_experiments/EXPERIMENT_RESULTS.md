# GNSS-SDR experiments: starting context

## Current state and next unresolved experiment

Evidence reconciled on **2026-11-13**. The goal is live GPS L1 C/A reception on
`hft02`, followed eventually by receiver/satellite/status output to a dashboard.
The latest saved LimeSDR recording demonstrates sustained navigation-message
decoding. **No native GNSS-SDR PVT fix has been demonstrated in the November
replays. External-reference lock has not been demonstrated.** These are separate
open questions; the clock result does not explain the measured software rejection.

The next software experiment is **native confirmation of the first four-observation
PVT rejection, followed by a coordinate-free initialization comparison** using the
existing 90-second recording. A standalone reconstruction already reproduces an
elevation-filtering failure, but the diagnostic receiver build stopped at missing
development dependencies. Obtain compatible local build inputs before trying that
comparison; preserve the 3° mask and reapply it at the final solution, compare the
15° case separately, and measure subsequent-epoch fix continuity. A supplied-position
single-epoch control is already successful; repeating it would not establish
autonomous native PVT. No supported installed-version configuration-only seed was
found. See the [native build report](RX1H_NATIVE_CONFIRMATION.md),
[configuration audit](RX1H_CONFIGURATION_WORKAROUND_AUDIT.md), and
[single-epoch diagnosis](RX1H_FIRST_EPOCH_PVT.md).

The next clock investigation should distinguish **reference-signal presence and
compatibility, PLL configuration/control, and lock-status reporting**. The November
13 idle test acknowledged the programmed ADF4002 transaction but observed no high
lock sample. This document proposes no immediate repeat or hardware command.
Any future during-reception status measurement must use the receiver's sole owning
connection; the completed idle test did not test streaming or GNSS reception.

The last recorded hardware end state, at 2026-11-13 01:17:28 UTC, was **DAC-control
mode at code 125**, with a consistent readback and a closed USB connection. This is
a historical end state, not a fresh observation of the board now. Do not assume the
external reference remained selected after cleanup.

## How to use the evidence

This is a consolidation of saved artifacts, not a new receiver run. **Measured**
below means recorded output/readback or a count checked against saved logs;
**interpretation** identifies what that supports; **proposed** means work not yet
performed. A reported frequency is a driver readback unless explicitly measured.
Tracking starts, NAV decoding, ephemeris acceptance, valid observations, and a PVT
fix are different milestones. A process exit of zero alone proves none of them.

No `AGENTS.md` or populated instruction files were found in the repository or its
parent search, and the repository's `.agents` and `.codex` directories were empty.
No separately named current/archived handoff files were found. The preserved
[original project summary](GNSS_SDR_PROJECT_SUMMARY.md) and the later reports linked
below form the available handoff chain. Git history contains the original summary
and curated-artifact commits; most later material was already untracked at the
start of this cleanup. Missing handoffs outside this checkout were not available
for verification.

The installed-version evidence describes GNSS-SDR **0.0.16**, Debian package
**0.0.16-1 amd64**, GNU Radio **3.10.1.1**, SoapySDR **0.8.1**, and gr-osmosdr
package **0.2.3-5build2** (reported library ABI 0.2.0). System LimeSuite
**20.10.0+dfsg-5** and local **22.09.0-ge829d3ed** coexist with two Soapy Lime
plugins. The November RX1_H captures isolated the system 20.10 stack; the low-level
reference diagnostics used local 22.09. These historical process-specific facts
do not identify a future process's loaded libraries. Local GNSS-SDR source has not
been proven equivalent to the installed executable. Sources:
[software audit](SOFTWARE_FIRST_DEBUG.md),
[capture procedure](RX1H_BASELINE.md), and
[reference audit](LIMESDR_EXTERNAL_REFERENCE_AUDIT.md).

## Timeline and experiment results

### April 2026: RTL-SDR control, Lime sweeps, and assistance loading

**Purpose/setup.** Test GPS reception through the shared antenna/splitter feed,
using RTL-SDR through SoapyRemote as a control and LimeSDR through the Osmosdr/Soapy
source. The original setup described LNAW and external antenna bias. That description
does not independently establish the cable route or selected physical socket.
Curated configs (`docs/configs_used`), sweep scripts (`docs/scripts_used`),
receiver logs (`docs/results/logs/output`), and harvest logs (`docs/results/logs/rtl_harvest`)
preserve the early experiments. Dates embedded in logs/configured receiver time
must not automatically be treated as wall-clock capture timestamps.

**Measured.** Counts below were checked against the saved console strings
`Tracking of GPS`, `Loss of lock`, `tracking bit synchronization locked`,
`New GPS NAV message received`, and `Position at`.

| Run / supporting log | Tracking starts | Losses | Bit sync | NAV | Position messages |
| --- | ---: | ---: | ---: | ---: | ---: |
| RTL initial (`docs/results/logs/output/rtlsdr_run.log`) | 20 | 18 | 2 | 36 | 0 |
| RTL baseline recheck (`docs/results/logs/output/rtl_baseline_recheck.log`) | 196 | 193 | 3 | 427 | 0 |
| RTL long (`docs/results/logs/output/rtlsdr_long_run.log`) | 66 | 62 | 2 | 96 | 0 |
| RTL 12-channel long (`docs/results/logs/output/rtlsdr_12ch_long_run.log`) | 113 | 109 | 2 | 214 | 0 |
| RTL 12-channel 30-minute (`docs/results/logs/output/rtlsdr_12ch_30min.log`) | 174 | 171 | 2 | 315 | 0 |
| Lime balanced, 3-minute (`docs/results/logs/output/lime_balanced_3min.log`) | 59 | 52 | 0 | 0 | 0 |
| Lime balanced + assistance, 3-minute (`docs/results/logs/output/lime_balanced_agnss_3min.log`) | 39 | 34 | 0 | 0 | 0 |
| Lime balanced + assistance, 30-minute (`docs/results/logs/output/lime_balanced_agnss_30min.log`) | 568 | 564 | 0 | 0 | 0 |

The old/default Lime setup used AGC, roughly 3.5 acquisition threshold, 51 taps,
and band edge 0.45. Sweep families varied acquisition/tracking parameters,
2/4 Msps in v2 (`docs/results/logs/sweep_v2_runs`), and 2/5/10 Msps, 51/101 taps,
0.45/0.70/0.90 band edge and AGC in v3 (`docs/results/logs/sweep_v3_runs`).
The early summary selected 2 Msps, AGC off, 101 taps and band edge 0.70 from
this saved candidate (`docs/results/logs/sweep_v3_runs/cfg_sr2M_taps101_band70_agcF.conf`).
This improved tracking starts, not NAV or position success. The longer assisted
run was reported to produce zero NMEA bytes; its original output files are local
runtime artifacts rather than a guarantee that every curated log has an NMEA peer.

Assistance XML loaded PRNs 28 and 31 plus UTC/ionosphere models; the
ten-minute assisted log (`docs/results/logs/output/lime_agnss_10min.log`) explicitly
records this but also a malformed NMEA pathname/permission error. It and the
Chicago three-minute attempt (`docs/results/logs/output/lime_agnss_3min_chicago.log`)
have zero tracking/NAV counts and should not be promoted to successful signal
controls. The curated assistance (`docs/results/assist`) is historical, reported as
GPS week 2419 in the later software audit, and is unsuitable as current live data.

**Interpretation/limits.** RTL NAV demonstrates a viable reception/decoder path
in those experiments. It does not prove Lime's RF input or a position fix. Loading
XML did not repair the early Lime tracking failures. RF interference, filtering,
clock stability and tracking configuration were hypotheses in the
[original summary](GNSS_SDR_PROJECT_SUMMARY.md), not isolated causes. Its blanket
“Lime cannot hold lock/decode NAV” conclusion is superseded by November's RX1_H
recordings below. Early durations are experiment labels; exit codes were not
consistently retained, so none are invented here.

### April 28–May 20: clock snapshots, gain, Doppler, IF and orientation trials

These exploratory families are kept in their original locations because saved
configs/scripts/logs contain paths into them. A directory date identifies the
historical run label; it is not a newly verified clock reading.

| Purpose and setup | Observed result and evidence | Limits |
| --- | --- | --- |
| April 28 external 10 MHz selection using LimeUtil, followed by Soapy probes | 09:05:28-labelled check (`output/clock_checks/lime_refclk_10mhz_20260428_090528.log`) and 22:14:51 retry (`output/clock_checks/lime_extref_retry_20260428_221451.log`) print ADF state 0 and found gateware 2.12 versus expected 2.23. | Soapy `clock_locked=true` describes CGEN, not ADF lock. The nominal 30.72 MHz printout is not a precision oscillator measurement. |
| April 29 clean Lime configuration | Run (`runs/lime_diagnostic_clean_20260429_204045/run.log`): 8 starts, 3 losses, zero bit sync/NAV/position; last printed receiver time 32 s. | Short historical live result; no sustained external-lock series. |
| May 2 file-source trials and May 5 raw/external-clock drift comparisons | Raw replay (`runs/raw_drift_test_20260505_054124/run.log`): 47 starts/44 losses through 6 min, zero NAV. Completed external-clock-labelled replay (`runs/extclk_drift_test_20260505_071652/run.log`): 30/29 through 4 min, zero NAV. Earlier attempt (`runs/extclk_drift_test_20260505_070749/run.log`) fails because the IQ filename does not exist. May 2 replay (`runs/file_source_20260502_080526/run.log`): 19/15 through 2 min 35 s, zero NAV. | Filenames/preceding setters do not verify external discipline or isolate frequency drift; the missing-file attempt is invalid as a signal test. |
| May 11 gain-sweep launch attempts, 45 combinations × 180 s planned | 02:50:52 launch (`runs/historical_launch_logs/gain_sweep_20260511_025052.log`) and 02:54:54 launch (`runs/historical_launch_logs/gain_sweep_20260511_025454.log`) print ADF state 1, then a line-220 arithmetic error (`0` newline `0`) at the first combination and an empty results table. | “SWEEP COMPLETE” is misleading; the referenced result directories are absent in this checkout. The startup lock snapshot is not streaming telemetry. |
| May 11–14 gain families | [May 14 04:29:32 CSV](results/local_evidence/runs/gain_sweep_20260514_042932/results.csv) and master log (`runs/sweep_master.log`) preserve 25 gain/IF combinations: tracking starts but zero bit sync/NAV/fixes in the CSV. Example gain=15, IF=6 reports actual total gain 45 dB, 23 starts/18 losses, score 5. Sweep script (`scripts/gain_sweep.sh`). | Score rewards start/loss counts; it is not a NAV or accuracy metric. Other gain directories include partial/failed launches; do not infer completion from directory presence. |
| May 14 baseline and diagnostics | Base (`runs/base_test_20260514_032239/run.log`): 16/13, last time 79 s. Diagnostic (`runs/diag_20260514_033417/run.log`): 47/43, last time 217 s. Both zero bit sync/NAV/position. | No immutable hardware/wiring validation comparable to November capture readbacks. |
| May 15 Doppler-aided Lime and RTL comparison | Lime 05:26:45 (`runs/doppler_20260515_052645/run.log`): 67/67 through 22 min 15 s; 05:55:09 (`runs/doppler_20260515_055509/run.log`): 16/15 through 199 s; both zero NAV. RTL 06:09:41 (`runs/rtl_doppler_20260515_060941/run.log`): 67 starts, 66 losses, 1 bit sync, 47 NAV, zero position messages. Doppler helper (`scripts/compute_doppler.py`). | Helper defaults to UIUC while other configs use Chicago; historical assistance freshness/week handling was suspect. No isolated proof Doppler aiding fixes Lime. |
| May 19 RX2-labelled, offset-LO and saved-IQ trials | RX2 test (`runs/rx2_test_20260519_040558/run.log`): 12/5, zero NAV. Offset LO (`runs/lo_offset_20260519_045841/run.log`): 36/29 through 114 s, zero NAV. File replay (`runs/filesource_rx2_20260519_051415/run.log`): 4/2 through 24 s, zero NAV. | `rx2` names and `chan=1` do not prove a selected physical RF socket. The 05:11:26 (`runs/filesource_rx2_20260519_051126/run.log`) and 05:11:30 (`runs/filesource_rx2_20260519_051130/run.log`) attempts could not connect their flowgraphs. |
| May 20 CFAR/focused tracking, FLL pull-in and IF sign | CFAR-labelled live log (`runs/cfar_20260520_043147/run.log`): 18/18 through 898 s. Focused 05:04:25 (`runs/focused_20260520_050425/run.log`): 84/83 through 898 s. Pull-in (`runs/test1_pullin_20260520_052918/run.log`): 2/2 through 125 s. Negative IF (`runs/test2_if_minus_20260520_054004/run.log`): zero starts through 132 s. All zero bit sync/NAV/position. | A label saying CFAR is not evidence the installed receiver enabled it. Later source/log audit established `Acquisition_1C.pfa` is the relevant switch. |
| May 20 original/conjugated/swapped-IQ variants at ±500 kHz IF | [Summary](results/local_evidence/runs/conj_results.txt), runner (`scripts/run_conj_test.sh`), and representative replay (`runs/conj_orig_IF500000_20260520_064246/run.log`) exist. Summary rows contain repeated newline-separated zeros; these logs print only 1 s of receiver time despite a 60 s input. | Malformed aggregation and incomplete progress prevent selecting a validated IQ orientation from this series. November's documented capture/replay establishes a working +500 kHz path instead. |
| May 20 last saved live decoding attempt | 06:55:36 log (`runs/bitsync_fix_20260520_065536/run.log`) prints LNAW/`chan=1`, duplicate Lime plugin registration, 2 Msps, 1574.92 MHz, total gain 45 dB; 4 starts, 3 losses, zero bit sync/NAV, stops at 68 s with `^C`. | The 15-minute launch/history and preceding reference setter described in the [handoff](RX1H_BASELINE.md) are not a completed 15-minute run or verified clock lock. No immutable config snapshot for this live run. |

Additional original capture folders remain under IQ captures (`iq_captures`),
May captures (`captures`), and IQ from Alex (`iq_from_alex`). The supplied
artifacts do not establish a documented known-good independent GPS control for the
Alex data. Legacy F9T workflow (`f9t/README_F9T_EPHEMERIS_RUN.md`) describes
EVK/ZED-F9T UBX → convbin → RINEX NAV → assistance XML; saved F9T runs (`f9t/assist_runs`)
and assistance backups (`assist/backups`) preserve provenance. This cleanup
did not validate every UBX conversion or assert current freshness of those files.

### November 8: software-first replay of the April recording

**Purpose/setup.** Reproduce the symptom without a live USB stream using
offline runner (`scripts/run_offline_baseline.sh`) and
template (`configs/lime_offline_baseline.conf`). The archived input is
April 28 IQ (`iq_captures/lime_l1/lime_baseline_no_10mhz_20260428_044448.dat`),
928,049,648 bytes, assumed CF32/2 Msps/1575.42 MHz, nominal duration **58.003103 s**.
Metadata is inferred from the historical capture setup, not embedded in this file.
Acquisition: 1 ms, CFAR `pfa=0.001`, blocking offline mode, default lock tests,
no assistance, no repetition.

**Measured.** The 02:21:47 UTC attempt's
[summary](results/local_evidence/runs/offline_baseline_Vw5RO5Ja/summary.json) records child exit 0
but `completed=false`: GNU Radio could not create its home FFT-wisdom lock and the
flowgraph never connected. The 02:22:17 UTC
[completed replay](results/local_evidence/runs/offline_baseline_sgt38Nyw/summary.json) records exit
0, 58 s final receiver time, CFAR enabled, **20 acquisitions/starts, 13 losses,
0 bit sync, 0 NAV, 0 position messages, 0 NMEA bytes**.

**Interpretation/limits.** This reproduces failure from saved samples, independent
of a new live USB stream, but cannot separate bad/weak samples, false acquisitions
or tracking behavior. The later RX1_H success supersedes a universal claim that
Lime recordings cannot decode NAV. The [software handoff](SOFTWARE_FIRST_DEBUG.md)
also establishes that `use_CFAR_algorithm=true` alone is not the installed
acquisition switch, and `max_lock_fail`, not `max_code_lock_fail`, is consumed
for this tracking code-lock limit. Longer tracks after relaxed failure limits
are not proof of stronger signal.

### November 8: verified RX1_H capture and acquisition sensitivity

**Purpose/setup.** Establish one reproducible driver-reported H input, isolate
system LimeSuite 20.10, and save IQ before changing receiver processing. See
capture script (`scripts/capture_rx1h_baseline.py`),
launcher (`scripts/run_rx1h_baseline.sh`), and [handoff](RX1H_BASELINE.md).
User executed live captures; later analysis used files only.

The 03:38:36-labelled first attempt (`runs/rx1h_baseline_20261108_033836_SOAd6t/run.log`)
read antenna/rate successfully but aborted before IQ creation, exit **1**, because
the validator required exact floating-point equality to 2,000,000 samples/s.
Readback was **1,999,999.9809265137 samples/s**, a difference of
**−0.0190734863 samples/s**. The corrected validator allows ±1 sample/s (0.5 ppm)
and rejects non-finite values. This is numerical validation, not measured clock accuracy.

Both corrected captures requested source channel 0/LNAH, 2 Msps, LO
1,574,920,000 Hz, manual gain calls matching the old setup, and discarded the
first second. Before/after readbacks: one source channel/index 0, LNAH,
**1,999,999.9809265137 samples/s**, **1,574,919,990.234375 Hz**, **45 dB** total gain
(TIA **12**, LNA **27**, PGA **6** dB). Bandwidth returned −1, not a measured
physical filter bandwidth. The successful captures each returned exit **0**:

| Capture label | Saved CF32 IQ | Evidence |
| --- | --- | --- |
| 2026-11-08 03:41:30 | 60,000,000 complex samples, **480,000,000 bytes**, nominal 30 s | [summary](results/local_evidence/runs/rx1h_baseline_20261108_034130_Y7gMFe/summary.json), [before](results/local_evidence/runs/rx1h_baseline_20261108_034130_Y7gMFe/before_capture.json), [after](results/local_evidence/runs/rx1h_baseline_20261108_034130_Y7gMFe/after_capture.json), log (`runs/rx1h_baseline_20261108_034130_Y7gMFe/run.log`) |
| 2026-11-08 03:53:09 | 180,000,000 complex samples, **1,440,000,000 bytes**, nominal 90 s | [summary](results/local_evidence/runs/rx1h_baseline_20261108_035309_7qbMJ8/summary.json), [before](results/local_evidence/runs/rx1h_baseline_20261108_035309_7qbMJ8/before_capture.json), [after](results/local_evidence/runs/rx1h_baseline_20261108_035309_7qbMJ8/after_capture.json), log (`runs/rx1h_baseline_20261108_035309_7qbMJ8/run.log`) |

Logs report successful RX calibration and no stream errors. Summaries check finite,
nonzero-variance beginning/middle/end windows; the more detailed
[30 s IQ analysis](results/local_evidence/runs/rx1h_baseline_20261108_034130_Y7gMFe/iq_analysis.json)
and [90 s IQ analysis](results/local_evidence/runs/rx1h_baseline_20261108_035309_7qbMJ8/iq_analysis.json)
are preserved. These do not independently prove uninterrupted sampling or reference lock.

**30 s measured replay.** GPS L1 is **+500 kHz** relative to nominal LO, so use
`InputFilter.IF=500000`, not zero or the old negative sign. A
[1 ms / 250 Hz-bin replay](results/local_evidence/runs/offline_baseline_LUhwbthK/summary.json)
completed with exit **0** but **zero acquisitions/starts, bit sync and NAV**.
The [4 ms / 125 Hz-bin replay](results/local_evidence/runs/rx1h_offline_4ms_rnuld_e8/summary.json),
same CFAR `pfa=0.001`, produced **22 starts, 10 losses, 2 bit-sync events and 4 NAV
subframes**. PRNs 21/22 decoded SF2/SF3 and tracked about 0.49/0.54–29.88 s without
loss on those channels; reported final-ten-second median C/N0 was about
**38.8/36.7 dB-Hz**. See [decoded satellites](results/local_evidence/runs/rx1h_offline_4ms_rnuld_e8/decoded_satellites.json)
and the [capture/tracking analysis](RX1H_BASELINE.md).

The working 4 ms config (`configs/lime_rx1h_offline_4ms.conf`) uses 12 GPS L1
channels, one acquisition at a time, ±10 kHz Doppler search, blocking acquisition,
101-tap filter with passband edge 0.70, PLL 40 Hz, DLL 2 Hz, FLL 10 Hz and FLL
pull-in enabled; assistance is off. Exact per-run snapshots take precedence over
mutable templates. The 4 ms summary records completion but does not store an
explicit exit-status field; do not infer one from a neighboring run.

**Interpretation.** Usable GPS and sustained NAV-capable Lime tracking are established
for this recording. Multiple settings/path choices differ from the early setup,
so the result does not isolate one cause of the historical failures.

### November 8: 90 s replay, PRN21 ephemeris, and four-observation PVT trials

**Purpose/setup.** Give the verified RX1_H path more NAV time. The
90 s baseline snapshot (`runs/rx1h_offline_90s_1i1wopzh/config_used.conf`)
changes only the IQ filename from the working 30 s config.

**Measured.** [Baseline summary](results/local_evidence/runs/rx1h_offline_90s_1i1wopzh/summary.json):
**56 starts, 44 losses, 6 bit sync, 36 NAV subframes**, PRNs 5/12/21/22 represented,
native ephemerides only 5/12 in that replay, **0 position messages/NMEA bytes**.
[Tracking segments](results/local_evidence/runs/rx1h_offline_90s_1i1wopzh/tracking_segments.json)
record PRN5 holding about **88.6 s**, PRN21 **89.4 s**, PRN12's final track
**67.3 s**, and PRN22's two roughly 25–26 s segments.

The localhost NAV audit (`scripts/audit_offline_nav.py`) returned exit **0**,
capturing **43** messages with SF1–5 from all four PRNs:

| PRN | IODC | SF2 / SF3 IODE | Health | Native audit ephemeris |
| --- | ---: | --- | ---: | --- |
| 5 | 49 | 49 / 49 | 0 | Yes |
| 12 | 48 | 48 / 48 | 0 | Yes |
| 21 | **983** | **215 / 215** | 0 | No |
| 22 | 23 | 23 / 23 | 0 | Yes |

Primary records: NAV messages (`runs/nav_audit_9dvjj0co/nav_messages.json`),
[audit summary](results/local_evidence/runs/nav_audit_9dvjj0co/summary.json),
native XML (`runs/nav_audit_9dvjj0co/gps_ephemeris.xml`).
The [handoff](RX1H_90S_RESULTS.md) identifies local 0.0.16's full-IODC-versus-IODE
comparison: **983 differs from 215, but `983 & 255 == 215`**. This implementation
matches the rejection; installed-binary source equivalence remains unproven.

**Experimental data workaround.** Recovery script (`scripts/recover_nav_ephemeris.py`)
decodes the saved NAV bits using local field definitions, cross-validates **37
fields** against each native PRN5/12/22 record, and adds PRN21 with its true
IODC=983/IODE=215 retained. Recovered XML (`runs/nav_audit_9dvjj0co/recovered_ephemeris.xml`)
and [provenance](results/local_evidence/runs/nav_audit_9dvjj0co/recovered_ephemeris.provenance.json)
are retrospective assistance for this recording, not current live data or a
receiver software fix. No receiver-position prior was supplied for these replays.

| Replay / primary summary | Setup | Measured result |
| --- | --- | --- |
| [Recovered ephemeris](results/local_evidence/runs/rx1h_recovered_eph_9x5ti6tk/summary.json) | Load the four-entry XML; retain general PRN scan | 57 starts/45 losses, 5 bit sync, 38 NAV; no native fix |
| [Four PRNs](results/local_evidence/runs/rx1h_four_prn_axlbe7v2/summary.json) | Restrict acquisition to 5/12/21/22, dump observations | 7/3, 5 bit sync, 41 NAV; **1,835** four-observation epochs = **36.7 s**, TOW **14064.000–14100.680**; no fix |
| [3° mask](results/local_evidence/runs/rx1h_pvt_lowmask_cs0kpzfz/summary.json) | Only new setting `PVT.elevation_mask=3.0` versus focused replay | 6/2, 4 bit sync, 43 NAV; **2,435** four-observation epochs = **48.7 s**, TOW **14052.000–14100.680**; no fix |
| [Trace follow-up](results/local_evidence/runs/rx1h_pvt_trace_euacgtrs/summary.json) | Logging follow-up | 7/3, 5 bit sync, 41 NAV; **1,301** four-observation epochs = **26.02 s**; no fix/additional console solver reason |

All four summaries have zero position messages and zero NMEA bytes. NAV counts
differ across replays because acquisition scheduling differs; the audit's native
PRN22 XML does not contradict its absence in the original 90 s baseline.

**Independent consistency check.** [Saved four-satellite least-squares calculation](results/local_evidence/runs/rx1h_four_prn_axlbe7v2/independent_position_check.json)
uses broadcast satellite clocks/relativity and Earth rotation, no receiver-position
prior and no atmospheric corrections. At TOW 14064 its output is
**41.88077677449905°, −87.64382637537237°, ellipsoidal height 309.21850310917944 m**,
clock bias **−81.65617257892339 ms**, GDOP **7.078573665004747**. PRN5 is about
**4.27–4.51°** across sampled epochs and is excluded by the normal 15° mask.
This is neither an accuracy validation nor a native PVT fix: four measurements
have no redundancy and positions vary by tens of metres or more. Signed coarse
pseudoranges can arise from the arbitrary receiver clock origin and alone do not
diagnose a clock/reference fault.

### November 8: first-epoch reconstruction and blocked native confirmation

**Purpose/setup.** Extract the first focused-replay four-valid epoch and trace
the local RTKLIB point solver. Diagnostic script (`scripts/diagnose_first_pvt_epoch.py`)
uses epoch **2650**, byte offset **593600**, **224 bytes** (four channels × seven
little-endian doubles). All RX times are GPS TOW **14064.000 s**. Exact
[epoch JSON](results/local_evidence/runs/first_epoch_pvt_20261108_4/epoch.json) and
bytes (`runs/first_epoch_pvt_20261108_4/epoch.bin`) are saved.

| PRN | Saved pseudorange, m |
| --- | ---: |
| 5 | 959807.918615606 |
| 12 | −3570239.595129443 |
| 21 | −1832723.892999736 |
| 22 | −464318.149914169 |

**Measured reconstruction.** Local conversion propagates all four satellites;
WN=396 expands to **2444**, Toe=Toc=**14400 s**, RX−Toe=**−336 s**, within the
local ±7201 s selection allowance. Starting at ECEF zero, iteration 0's least
squares succeeds. Iteration 1 begins at
**(130766.199849495, −5151117.821045178, 4786432.041062787) m**, clock bias
**−23654352.592151921 m**. PRN elevations are **1.797421352°**, **58.147161664°**,
**27.267272705°**, **14.171253275°** for 5/12/21/22 respectively.

| Same saved epoch | Result |
| --- | --- |
| 15° from zero (`runs/first_epoch_pvt_20261108_4/native_path_trace.log`) | PRN5 and PRN22 rejected; **2 satellites, 5 equations, 7 required**; solver return **0**, status **0** |
| 3° from zero (`runs/first_epoch_pvt_20261108_4/existing_3deg_trace.log`) | PRN5 still rejected; **3 satellites, 6 equations, 7 required**; solver return **0**, status **0** |
| 3° with independent-position seed (`runs/first_epoch_pvt_20261108_4/existing_3deg_seeded_diagnostic.log`) | Converges after four iterations, **4 satellites, 7 equations**; solver return **1**, `SOLQ_SINGLE=5`; LLH **41.880810573°, −87.644068692°, 256.807 m**, clock **−81.656300 ms** |

These are solver return values, not process exit codes or new native receiver
fixes. The original focused replay's
internal log directory (`runs/rx1h_four_prn_axlbe7v2/internal`) records
`03:54:24.00: point pos error ()` at the same TOW; the detailed rejection is
from local-source reconstruction. The first failed selection is PRN5 elevation,
then `nv < NX`; final chi-square/GDOP validation is not reached. The error text
`lack of valid sats ns=5/6` misleadingly prints equation count as `ns`.

**Interpretation.** This resolves the earlier handoff's unspecified solver failure
for this reconstructed epoch. The 15° geometry remains insufficient near the
solution; the 3° case additionally suffers premature filtering at an intermediate
position. A coarse initializer computed from observations, followed by final mask
and validity checks, is a proposed functional correction, not an implemented fix.
The seeded control demonstrates sensitivity to initialization only.

The [full diagnosis](RX1H_FIRST_EPOCH_PVT.md),
[verification](results/local_evidence/runs/first_epoch_pvt_20261108_4/verification.json), and
[XML audit](results/local_evidence/runs/first_epoch_pvt_20261108_4/xml_audit.json) preserve the limits:
CN0 and several upstream flags are absent from the seven-double dump; ephemeris
conversion leaves certain RTKLIB metadata at defaults; assistance `tow=14088` was
decoded later than the tested epoch and loaded retrospectively. XML regeneration
is byte-identical; removing added PRN21/restoring map count 4→3 restores semantic
identity. Four fields are explicit zero defaults, and local FIT/AODO definitions
are not independent ICD validation. These caveats preclude an autonomous real-time
or independently validated ephemeris claim.

The logging-only patch (`runs/first_epoch_pvt_20261108_4/logging_only.patch`)
was used in a copied solver. The
error-propagation proposal (`runs/first_epoch_pvt_20261108_4/proposed_error_propagation.patch`)
fixes local pointer assignment `msg = msg_aux` rather than a caller-buffer copy;
it remains unapplied. The PVT-boundary logging proposal (`runs/first_epoch_pvt_20261108_4/proposed_boundary_logging.patch`)
is also not evidence of a running diagnostic receiver. `_1`/`_2` diagnostic
directories preserve compiler failures, `_3` the earlier 15° reconstruction,
and `_4` the three-case successful harness. `PVT.rtk_trace_level=4` alone did
not expose the local glog `VLOG` trace; saved harness commands use the glog route.

**Native build attempt.** Preparation script (`scripts/prepare_native_pvt_diagnostic.py`)
made a logging-only source copy with hardware adapters/tests and dependency
fetching disabled. [First status](results/local_evidence/runs/native_pvt_confirmation_20261108_1/status.json)
and [recheck status](results/local_evidence/runs/native_pvt_confirmation_recheck/status.json) both
record **CMake return code 1**, receiver built/executed **false**, behavior changed
**false**. Configure log (`runs/native_pvt_confirmation_20261108_1/configure.log`)
and [dependency probes](results/local_evidence/runs/native_pvt_confirmation_20261108_1/dependency_probes.json)
show missing `pugixml.hpp`, `google/protobuf/message.h`, and `protoc`, with empty
cached dependency-source directories. The guard stops at
`OFFLINE_DEPENDENCY_BLOCKER: pugixml-1.12 needs GIT_REPOSITORY; fetching is forbidden`.
No native diagnostic replay or continuity comparison resulted.

**Configuration-only audit.** [Audit result](results/local_evidence/runs/pvt_configuration_support_audit_20261108/result.json)
and [report](RX1H_CONFIGURATION_WORKAROUND_AUDIT.md) found no supported PVT seed
through existing help/examples/source. `AGNSS_ref_location` serves visibility and
acquisition; `init_latitude_deg` and related keys belong to `front-end-cal`;
mode/dynamics/receiver-clock correction are not verified initial-position fixes.
Version check exited **0**, help **1** without starting a receiver. No new replay
was performed for this audit.

The later audit refines “missing libraries”: **runtimes exist; development inputs
are missing**. PugiXML runtime is **1.12.1-1**, Protobuf runtime
**3.12.4-1ubuntu7.22.04.6**. Needed are matching complete headers, link-time
discovery files or explicit versioned-library paths, and compatible `protoc`
(plus its compiler runtime if dynamically required). Do not mix Protobuf 3.19.4
headers/generated code with the installed 3.12.4 runtime. Resolving these confirmed
blockers does not guarantee the full receiver build will succeed.

### November 8–9: remote reference audit and one raw-status connection

**Purpose/setup.** Determine whether external lock could be checked remotely
without a competing device open. The [audit](LIMESDR_EXTERNAL_REFERENCE_AUDIT.md)
and [remote procedure](LIMESDR_REMOTE_REFERENCE_CHECK.md) distinguish metadata,
an existing owner's register getter, and hardware-affecting new opens. Standard
unmodified GNSS-SDR/Osmosdr exposes no periodic ADF status route; its ordinary
status/monitor outputs and Soapy CGEN/LO sensors are not ADF lock telemetry.

The reported host snapshot at **2026-11-09T00:36:18Z** found no USB holder or
scan failures, with idle SoapySDRServer PID 1343 listening on TCP 55132 and no
established TCP client. This is a handoff-recorded snapshot; its original pasted
JSON was not found as a separate artifact. It is not proof of continuing idleness.

**Measured controlled diagnostic, 2026-11-09T00:46:13Z** (November 8 18:46:13 CST):
one guarded low-level FX3 connection to serial **0009061C01502715**, library
**22.09.0-ge829d3ed**, returned **HW4/FW4/protocol1/gateware2.23**. Board registers
0/1/2/3 returned **0x000e/0x0002/0x0017/0x0004**; `0x00c8` returned **0x0002**,
raw bit 1 high. Guard/helper returned **0** and closed cleanly. See
[summary](results/local_evidence/runs/extref_once_20261109T004414Z_1bph5bsj/summary.json),
[guard](results/local_evidence/runs/extref_once_20261109T004414Z_1bph5bsj/guard.json),
packet/status log (`runs/extref_once_20261109T004414Z_1bph5bsj/diagnostic.jsonl`),
and [result report](LIMESDR_REFERENCE_DIAGNOSTIC_RESULT.md).

**Interpretation/limits.** This supersedes old 2.12 identity for that measured
connection, not evidence of a firmware update by the test. Standard reported
2.23 maps bit 1 to ADF MUXOUT, but its current programming was unknown, so a
single high pin level was inconclusive about external lock/control selection.
The FPGA binary's provenance was not independently authenticated. Constructor
traffic was not captured; low-level FX3 opening can reset USB endpoints. There
were no post-constructor ADF/DAC writes and no stream. Thus the later known-config
low series does not contradict an earlier unknown-config high snapshot.

### November 13: executed controlled idle external-reference test

**Purpose/setup.** Test digital lock indication after one explicit, known ADF4002
programming transaction, using the same exclusive connection through cleanup.
Prepared November 9; **executed by the user November 13**. The
[original plan](LIMESDR_CONTROLLED_IDLE_TEST_PLAN.md) and
[build manifest](results/local_evidence/runs/extref_idle_prepared_20261109T012546Z_95hauim6/build_manifest.json)
retain preparation-time statements “not executed” / `hardware_execution_approved=false`.
They are historical preparation records, superseded as execution status by the
actual [guard](results/local_evidence/runs/extref_idle_prepared_20261109T012546Z_95hauim6/guard.json)
and test log (`runs/extref_idle_prepared_20261109T012546Z_95hauim6/test.jsonl`),
which match the user-supplied result in this chat. Do not rerun the completed
one-shot directory: its exclusive attempt marker and logs now exist.

The Python launcher (`scripts/run_lime_external_reference_test.py`) verifies
prepared hashes and host-root ownership checks, then launches the
C++ helper (`scripts/lime_external_reference_test.cc`). No owners, scan
failures, attached interface drivers or USB metadata errors were recorded;
the device negotiated 5000 Mbit/s. One FX3 connection used local LimeSuite
22.09.0-ge829d3ed and matched HW4/FW4/GW2.23. This was idle: no receiver stream,
RF capture, RFIC initialization or RF configuration was requested.

Configuration: **10 MHz reference**, nominal **30.72 MHz VCTCXO feedback**,
**R=125**, **N=384**, **80 kHz** phase-detector comparison, digital-lock MUXOUT
code **001** in both initialization/function latches, **LDP=0**. Exact ordered
24-bit words: **0x1f8093, 0x1f8092, 0x0001f4, 0x018001**, sent via SPI target
0x30 / protocol command 0x31. This selects ADF discipline of the onboard oscillator;
it is not replacement of the oscillator by a direct 10 MHz RFIC clock.

**Measured sequence (UTC).**

| Event / criterion | Recorded result |
| --- | --- |
| Guard start | **2026-11-13T01:11:57.248630+00:00** |
| ADF programming result | **01:11:57.286898Z**, status **0**; transaction reported success; latch readback unavailable |
| Settling | **30 s**, samples at nominal t=0…29 s |
| Evaluation | Nominal t=30…330 s, **301 scheduled reads spanning 300 s**, all **301 completed** |
| Status | Every evaluation sample **0x0000**, monitored bit `(raw >> 1) & 1` **low**; **301 unlocked samples** |
| Errors/timing | **0** read errors, missing slots, requests >250 ms late, or completion gaps >1.5 s |
| Acquisition indications | **0 low-to-high transitions**; first-high and three-consecutive-high times **null**; no high observed during settling either |
| Baseline write | **01:17:27.288045Z**, status **0**, return to **DAC control at saved code 125** |
| Baseline verification | **01:17:28.288725Z**, reported DAC **125**, successful raw read **0x0000**, baseline consistent **true**, oscillator-frequency verified **false** |
| Connection close | **01:17:28.288881Z**, close recorded; no owners or scan failures afterward |
| Launcher finish | **2026-11-13T01:17:28.539867+00:00** |
| Exit | **4**: observation criteria failed; no interruption or test exception |

The helper's exit 0 requires a complete high window with no recorded read/timing
gaps and successful cleanup. Here, **301 low samples caused exit 4**. Empty
stderr (`runs/extref_idle_prepared_20261109T012546Z_95hauim6/test.stderr`)
and a blank summary error string do not mean the lock criterion passed.
The nine offline self-test scenarios (`runs/extref_idle_prepared_20261109T012546Z_95hauim6/self_test.jsonl`)
checked software accounting/cleanup before this execution; they were not RF tests.

**Meaning and limits.** The run **did not demonstrate external-reference lock**,
measure oscillator frequency, or test GNSS reception. Acknowledged programming
does not independently verify the physical ADF latches or the electrical reference
signal. The low status series leaves **the reference signal, PLL configuration,
and lock-status reporting as open questions**. The 1 Hz cadence is sampled evidence,
not a continuous electrical trace. Cleanup disabled ADF control in favor of DAC
code 125; it did not restore an unknown exact prior ADF state or verify DAC voltage.
No causal link to the November PVT failure follows from this idle clock test.

## Where to resume and what not to infer

1. Preserve 90 s IQ (`runs/rx1h_baseline_20261108_035309_7qbMJ8/rx1h.cf32`),
   focused observations (`runs/rx1h_four_prn_axlbe7v2/observables.dat`),
   focused config (`runs/rx1h_four_prn_axlbe7v2/config_used.conf`), the
   3° config (`runs/rx1h_pvt_lowmask_cs0kpzfz/config_used.conf`), and their
   experimental NAV provenance as the regression set. Independent-position
   calculations and standalone seeded successes must remain labelled as such.
2. Resolve the native build dependency gap before claiming a native rejection
   trace, unaided initialization repair, or continuous fixes. Keep the logging,
   caller-error correction and functional initialization proposal distinct.
3. For clock work, start from the completed low-status result and documented DAC
   end state. A source setter, reference readback, Soapy CGEN/LO lock, a historical
   high MUXOUT sample, or successful NAV does not prove sustained external lock.
   Prepare any new hardware experiment separately; none was run in this cleanup.
4. For a future RF comparison, independently establish actual wiring/channel,
   antenna power route, reference setup and loaded driver stack. The November
   capture proves driver-reported LNAH plus usable signals in that recording,
   not every historical or future setup. Avoid treating additional gain sweeps
   as prerequisites for investigating the already reproducible PVT rejection.

The raw IQ, runtime outputs, some source dependencies and most November files are
local working-tree material, much of it untracked or ignored. A clone containing
only tracked Git files will not contain this complete experiment state. Large IQ
was not reprocessed or rehashed for this documentation task. Previously saved
preservation hashes are evidence of the original experiments, not fresh physical
measurements. Exact exit statuses not explicitly retained above remain unverified.

## Organization and preservation decisions

This cleanup creates only this document. It moves the original project summary
from `docs/GNSS_SDR_PROJECT_SUMMARY.md` to
[GNSS_SDR_PROJECT_SUMMARY.md](GNSS_SDR_PROJECT_SUMMARY.md), without changing its
contents. It moves the two otherwise unreferenced root gain-sweep launch logs to
historical launch logs (`runs/historical_launch_logs`), preserving their
names and contents. Their embedded absolute references to absent run directories
were already unresolved; moving the logs neither repairs nor changes those records.

Other historical reports stay in docs (`docs`): their relative sibling and
`../runs`/`../output` links must keep working. Scripts stay in
scripts (`scripts`) because launchers derive the project root from their
own location and prepared manifests hash exact source paths. Configs and run
directories stay in place because templates, helper scripts, JSON provenance,
build metadata and saved commands contain exact paths into them. Examples include
the 30 s IQ filename in the working config, fixed focused/audit paths in the epoch
diagnostic, and the external-reference manifest's exact binary/helper paths.
The curated assistance/config/script/log groups and F9T backups already have
useful grouping and are preserved. Empty root RINEX/NMEA files and other outputs
are retained rather than guessed to be expendable.

Existing content, unrelated working-tree material, installed software and hardware
were left untouched. No deletion, commit, push, installation or hardware experiment
is part of this cleanup.
