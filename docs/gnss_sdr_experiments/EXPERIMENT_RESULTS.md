# GNSS-SDR experiments: starting context

> GitHub publication: links below use the repository archive layout. Small text evidence is included; IQ recordings, full observables, source/build copies, binaries and large per-epoch outputs remain on hft02. A clone alone cannot reproduce the experiment without those preserved local inputs.

## Current state and next unresolved experiment

Evidence reconciled on **2026-11-13**. The goal is live GPS L1 C/A reception on
`hft02`, followed eventually by receiver/satellite/status output to a dashboard.
The latest saved LimeSDR recording demonstrates sustained navigation-message
decoding. **No native GNSS-SDR PVT fix has been demonstrated in the November
replays. External-reference lock has not been demonstrated.** These are separate
open questions; the clock result does not explain the measured software rejection.

The latest **stock 3° baseline replay**, using the installed receiver and unchanged
90-second input/configuration, completed with **exit 0**, **45 decoded NAV
subframes**, **2,435 four-valid-pseudorange epochs**, and **no reported/saved native
PVT fix**. Every four-valid epoch has a matching native point-position error with
an empty reason. This confirms stock receiver failure, not the specific standalone
elevation-filtering cause. See the [new run summary](results/local_evidence/runs/stock_rx1h_90s_3deg_20261113T033819Z_eg_8pwsd/summary.json)
and the stock baseline section below. The run retains the experimental PRN21 XML
and supplies no receiver coordinates. No diagnostic build or config change was
part of this replay.

The follow-up **TOW 14052.000 error-path audit** finds an error-text propagation
defect in the available 0.0.16 source: three `estpos()` failure paths write a
local buffer, then assign its address to a local pointer instead of copying the
text to the caller. Native empty parentheses are consistent with that defect,
but do not identify which failure occurred. Native computed elevations and
post-filter membership remain unavailable. See the error-path audit section
below and its [evidence bundle](results/local_evidence/runs/point_pos_error_14052_audit__kio7sl6/native_evidence_and_missing_fields.json).

A subsequent **host-level prerequisite check for the requested native TOW
14052 diagnostic** found no usable diagnostic receiver or complete local
development dependencies. All four header preprocessing probes failed and
`protoc` was absent. Work stopped before source edits, configuration, build or
replay, as requested. This is a fresh read-only availability check, not another
failed diagnostic build. See [status](results/local_evidence/runs/native_14052_dependency_check_n17mm09y/build_status.json)
and the dependency-check section below. The native failure branch and computed
elevations at 14052.000 remain unestablished.

The latest **exact-TOW-14052 standalone comparison** now tests a coordinate-free
initialization candidate. With the saved stock observations and experimental
PRN21 XML, the unchanged solver rejects PRN5 at **1.72138° on iteration 1**,
leaving **ns=3, nv=6 < NX=7**. Deferring elevation rejection until an
observation-derived provisional position exists, then recomputing with the
original **3°** mask and unchanged final validation, solves **2435/2435** saved
four-valid epochs (14052.000–14100.680) in both cold and sequential harness modes.
All four final elevations pass; the **15° control still fails** honestly.
This is **reconstructed library evidence, not native receiver confirmation**.
It remains dependent on the experimental PRN21 XML. Position scatter is
**55.52 m 3D RMS about its mean**; four ranges provide no redundant residual
check, and no surveyed accuracy reference is available.

See the exact-epoch report (hft02 local artifact: `docs/RX1H_14052_BOOTSTRAP_RESULTS.md`),
[metrics](results/local_evidence/runs/epoch14052_bootstrap_dvazj6li/window_summary.json), and
[separate native diagnostic/functional patches and build-replay plan](results/local_evidence/runs/epoch14052_bootstrap_dvazj6li/native_plan/README.md).
No full native build was retried; compatible PugiXML/Protobuf development files
remain missing. The next software experiment is native **diagnostics-only**
confirmation at 14052, before applying the separately tested behavior candidate.
The full first-epoch selected native ephemeris and post-filter state are still
missing. No supported installed-version configuration-only seed was found; see
[the configuration audit](RX1H_CONFIGURATION_WORKAROUND_AUDIT.md).

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
Curated configs (hft02 local artifact: `docs/configs_used`), sweep scripts (hft02 local artifact: `docs/scripts_used`),
receiver logs (hft02 local artifact: `docs/results/logs/output`), and harvest logs (hft02 local artifact: `docs/results/logs/rtl_harvest`)
preserve the early experiments. Dates embedded in logs/configured receiver time
must not automatically be treated as wall-clock capture timestamps.

**Measured.** Counts below were checked against the saved console strings
`Tracking of GPS`, `Loss of lock`, `tracking bit synchronization locked`,
`New GPS NAV message received`, and `Position at`.

| Run / supporting log | Tracking starts | Losses | Bit sync | NAV | Position messages |
| --- | ---: | ---: | ---: | ---: | ---: |
| RTL initial (hft02 local artifact: `docs/results/logs/output/rtlsdr_run.log`) | 20 | 18 | 2 | 36 | 0 |
| RTL baseline recheck (hft02 local artifact: `docs/results/logs/output/rtl_baseline_recheck.log`) | 196 | 193 | 3 | 427 | 0 |
| RTL long (hft02 local artifact: `docs/results/logs/output/rtlsdr_long_run.log`) | 66 | 62 | 2 | 96 | 0 |
| RTL 12-channel long (hft02 local artifact: `docs/results/logs/output/rtlsdr_12ch_long_run.log`) | 113 | 109 | 2 | 214 | 0 |
| RTL 12-channel 30-minute (hft02 local artifact: `docs/results/logs/output/rtlsdr_12ch_30min.log`) | 174 | 171 | 2 | 315 | 0 |
| Lime balanced, 3-minute (hft02 local artifact: `docs/results/logs/output/lime_balanced_3min.log`) | 59 | 52 | 0 | 0 | 0 |
| Lime balanced + assistance, 3-minute (hft02 local artifact: `docs/results/logs/output/lime_balanced_agnss_3min.log`) | 39 | 34 | 0 | 0 | 0 |
| Lime balanced + assistance, 30-minute (hft02 local artifact: `docs/results/logs/output/lime_balanced_agnss_30min.log`) | 568 | 564 | 0 | 0 | 0 |

The old/default Lime setup used AGC, roughly 3.5 acquisition threshold, 51 taps,
and band edge 0.45. Sweep families varied acquisition/tracking parameters,
2/4 Msps in v2 (hft02 local artifact: `docs/results/logs/sweep_v2_runs`), and 2/5/10 Msps, 51/101 taps,
0.45/0.70/0.90 band edge and AGC in v3 (hft02 local artifact: `docs/results/logs/sweep_v3_runs`).
The early summary selected 2 Msps, AGC off, 101 taps and band edge 0.70 from
this saved candidate (hft02 local artifact: `docs/results/logs/sweep_v3_runs/cfg_sr2M_taps101_band70_agcF.conf`).
This improved tracking starts, not NAV or position success. The longer assisted
run was reported to produce zero NMEA bytes; its original output files are local
runtime artifacts rather than a guarantee that every curated log has an NMEA peer.

Assistance XML loaded PRNs 28 and 31 plus UTC/ionosphere models; the
ten-minute assisted log (hft02 local artifact: `docs/results/logs/output/lime_agnss_10min.log`) explicitly
records this but also a malformed NMEA pathname/permission error. It and the
Chicago three-minute attempt (hft02 local artifact: `docs/results/logs/output/lime_agnss_3min_chicago.log`)
have zero tracking/NAV counts and should not be promoted to successful signal
controls. The curated assistance (hft02 local artifact: `docs/results/assist`) is historical, reported as
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
| April 28 external 10 MHz selection using LimeUtil, followed by Soapy probes | 09:05:28-labelled check (hft02 local artifact: `output/clock_checks/lime_refclk_10mhz_20260428_090528.log`) and 22:14:51 retry (hft02 local artifact: `output/clock_checks/lime_extref_retry_20260428_221451.log`) print ADF state 0 and found gateware 2.12 versus expected 2.23. | Soapy `clock_locked=true` describes CGEN, not ADF lock. The nominal 30.72 MHz printout is not a precision oscillator measurement. |
| April 29 clean Lime configuration | [Run](results/local_evidence/runs/lime_diagnostic_clean_20260429_204045/run.log): 8 starts, 3 losses, zero bit sync/NAV/position; last printed receiver time 32 s. | Short historical live result; no sustained external-lock series. |
| May 2 file-source trials and May 5 raw/external-clock drift comparisons | [Raw replay](results/local_evidence/runs/raw_drift_test_20260505_054124/run.log): 47 starts/44 losses through 6 min, zero NAV. [Completed external-clock-labelled replay](results/local_evidence/runs/extclk_drift_test_20260505_071652/run.log): 30/29 through 4 min, zero NAV. [Earlier attempt](results/local_evidence/runs/extclk_drift_test_20260505_070749/run.log) fails because the IQ filename does not exist. [May 2 replay](results/local_evidence/runs/file_source_20260502_080526/run.log): 19/15 through 2 min 35 s, zero NAV. | Filenames/preceding setters do not verify external discipline or isolate frequency drift; the missing-file attempt is invalid as a signal test. |
| May 11 gain-sweep launch attempts, 45 combinations × 180 s planned | [02:50:52 launch](results/local_evidence/runs/historical_launch_logs/gain_sweep_20260511_025052.log) and [02:54:54 launch](results/local_evidence/runs/historical_launch_logs/gain_sweep_20260511_025454.log) print ADF state 1, then a line-220 arithmetic error (`0` newline `0`) at the first combination and an empty results table. | “SWEEP COMPLETE” is misleading; the referenced result directories are absent in this checkout. The startup lock snapshot is not streaming telemetry. |
| May 11–14 gain families | [May 14 04:29:32 CSV](results/local_evidence/runs/gain_sweep_20260514_042932/results.csv) and [master log](results/local_evidence/runs/sweep_master.log) preserve 25 gain/IF combinations: tracking starts but zero bit sync/NAV/fixes in the CSV. Example gain=15, IF=6 reports actual total gain 45 dB, 23 starts/18 losses, score 5. [Sweep script](../../scripts/gain_sweep.sh). | Score rewards start/loss counts; it is not a NAV or accuracy metric. Other gain directories include partial/failed launches; do not infer completion from directory presence. |
| May 14 baseline and diagnostics | [Base](results/local_evidence/runs/base_test_20260514_032239/run.log): 16/13, last time 79 s. [Diagnostic](results/local_evidence/runs/diag_20260514_033417/run.log): 47/43, last time 217 s. Both zero bit sync/NAV/position. | No immutable hardware/wiring validation comparable to November capture readbacks. |
| May 15 Doppler-aided Lime and RTL comparison | Lime [05:26:45](results/local_evidence/runs/doppler_20260515_052645/run.log): 67/67 through 22 min 15 s; [05:55:09](results/local_evidence/runs/doppler_20260515_055509/run.log): 16/15 through 199 s; both zero NAV. RTL [06:09:41](results/local_evidence/runs/rtl_doppler_20260515_060941/run.log): 67 starts, 66 losses, 1 bit sync, 47 NAV, zero position messages. [Doppler helper](../../scripts/compute_doppler.py). | Helper defaults to UIUC while other configs use Chicago; historical assistance freshness/week handling was suspect. No isolated proof Doppler aiding fixes Lime. |
| May 19 RX2-labelled, offset-LO and saved-IQ trials | [RX2 test](results/local_evidence/runs/rx2_test_20260519_040558/run.log): 12/5, zero NAV. [Offset LO](results/local_evidence/runs/lo_offset_20260519_045841/run.log): 36/29 through 114 s, zero NAV. [File replay](results/local_evidence/runs/filesource_rx2_20260519_051415/run.log): 4/2 through 24 s, zero NAV. | `rx2` names and `chan=1` do not prove a selected physical RF socket. The [05:11:26](results/local_evidence/runs/filesource_rx2_20260519_051126/run.log) and [05:11:30](results/local_evidence/runs/filesource_rx2_20260519_051130/run.log) attempts could not connect their flowgraphs. |
| May 20 CFAR/focused tracking, FLL pull-in and IF sign | [CFAR-labelled live log](results/local_evidence/runs/cfar_20260520_043147/run.log): 18/18 through 898 s. [Focused 05:04:25](results/local_evidence/runs/focused_20260520_050425/run.log): 84/83 through 898 s. [Pull-in](results/local_evidence/runs/test1_pullin_20260520_052918/run.log): 2/2 through 125 s. [Negative IF](results/local_evidence/runs/test2_if_minus_20260520_054004/run.log): zero starts through 132 s. All zero bit sync/NAV/position. | A label saying CFAR is not evidence the installed receiver enabled it. Later source/log audit established `Acquisition_1C.pfa` is the relevant switch. |
| May 20 original/conjugated/swapped-IQ variants at ±500 kHz IF | [Summary](results/local_evidence/runs/conj_results.txt), [runner](../../scripts/run_conj_test.sh), and [representative replay](results/local_evidence/runs/conj_orig_IF500000_20260520_064246/run.log) exist. Summary rows contain repeated newline-separated zeros; these logs print only 1 s of receiver time despite a 60 s input. | Malformed aggregation and incomplete progress prevent selecting a validated IQ orientation from this series. November's documented capture/replay establishes a working +500 kHz path instead. |
| May 20 last saved live decoding attempt | [06:55:36 log](results/local_evidence/runs/bitsync_fix_20260520_065536/run.log) prints LNAW/`chan=1`, duplicate Lime plugin registration, 2 Msps, 1574.92 MHz, total gain 45 dB; 4 starts, 3 losses, zero bit sync/NAV, stops at 68 s with `^C`. | The 15-minute launch/history and preceding reference setter described in the [handoff](RX1H_BASELINE.md) are not a completed 15-minute run or verified clock lock. No immutable config snapshot for this live run. |

Additional original capture folders remain under IQ captures (hft02 local artifact: `iq_captures`),
May captures (hft02 local artifact: `captures`), and IQ from Alex (hft02 local artifact: `iq_from_alex`). The supplied
artifacts do not establish a documented known-good independent GPS control for the
Alex data. Legacy F9T workflow (hft02 local artifact: `f9t/README_F9T_EPHEMERIS_RUN.md`) describes
EVK/ZED-F9T UBX → convbin → RINEX NAV → assistance XML; saved F9T runs (hft02 local artifact: `f9t/assist_runs`)
and assistance backups (hft02 local artifact: `assist/backups`) preserve provenance. This cleanup
did not validate every UBX conversion or assert current freshness of those files.

### November 8: software-first replay of the April recording

**Purpose/setup.** Reproduce the symptom without a live USB stream using
[offline runner](../../scripts/run_offline_baseline.sh) and
[template](../../configs/lime_offline_baseline.conf). The archived input is
April 28 IQ (hft02 local artifact: `iq_captures/lime_l1/lime_baseline_no_10mhz_20260428_044448.dat`),
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
[capture script](../../scripts/capture_rx1h_baseline.py),
[launcher](../../scripts/run_rx1h_baseline.sh), and [handoff](RX1H_BASELINE.md).
User executed live captures; later analysis used files only.

The 03:38:36-labelled [first attempt](results/local_evidence/runs/rx1h_baseline_20261108_033836_SOAd6t/run.log)
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
| 2026-11-08 03:41:30 | 60,000,000 complex samples, **480,000,000 bytes**, nominal 30 s | [summary](results/local_evidence/runs/rx1h_baseline_20261108_034130_Y7gMFe/summary.json), [before](results/local_evidence/runs/rx1h_baseline_20261108_034130_Y7gMFe/before_capture.json), [after](results/local_evidence/runs/rx1h_baseline_20261108_034130_Y7gMFe/after_capture.json), [log](results/local_evidence/runs/rx1h_baseline_20261108_034130_Y7gMFe/run.log) |
| 2026-11-08 03:53:09 | 180,000,000 complex samples, **1,440,000,000 bytes**, nominal 90 s | [summary](results/local_evidence/runs/rx1h_baseline_20261108_035309_7qbMJ8/summary.json), [before](results/local_evidence/runs/rx1h_baseline_20261108_035309_7qbMJ8/before_capture.json), [after](results/local_evidence/runs/rx1h_baseline_20261108_035309_7qbMJ8/after_capture.json), [log](results/local_evidence/runs/rx1h_baseline_20261108_035309_7qbMJ8/run.log) |

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

The working [4 ms config](../../configs/lime_rx1h_offline_4ms.conf) uses 12 GPS L1
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
[90 s baseline snapshot](results/local_evidence/runs/rx1h_offline_90s_1i1wopzh/config_used.conf)
changes only the IQ filename from the working 30 s config.

**Measured.** [Baseline summary](results/local_evidence/runs/rx1h_offline_90s_1i1wopzh/summary.json):
**56 starts, 44 losses, 6 bit sync, 36 NAV subframes**, PRNs 5/12/21/22 represented,
native ephemerides only 5/12 in that replay, **0 position messages/NMEA bytes**.
[Tracking segments](results/local_evidence/runs/rx1h_offline_90s_1i1wopzh/tracking_segments.json)
record PRN5 holding about **88.6 s**, PRN21 **89.4 s**, PRN12's final track
**67.3 s**, and PRN22's two roughly 25–26 s segments.

The [localhost NAV audit](../../scripts/audit_offline_nav.py) returned exit **0**,
capturing **43** messages with SF1–5 from all four PRNs:

| PRN | IODC | SF2 / SF3 IODE | Health | Native audit ephemeris |
| --- | ---: | --- | ---: | --- |
| 5 | 49 | 49 / 49 | 0 | Yes |
| 12 | 48 | 48 / 48 | 0 | Yes |
| 21 | **983** | **215 / 215** | 0 | No |
| 22 | 23 | 23 / 23 | 0 | Yes |

Primary records: [NAV messages](results/local_evidence/runs/nav_audit_9dvjj0co/nav_messages.json),
[audit summary](results/local_evidence/runs/nav_audit_9dvjj0co/summary.json),
[native XML](results/local_evidence/runs/nav_audit_9dvjj0co/gps_ephemeris.xml).
The [handoff](RX1H_90S_RESULTS.md) identifies local 0.0.16's full-IODC-versus-IODE
comparison: **983 differs from 215, but `983 & 255 == 215`**. This implementation
matches the rejection; installed-binary source equivalence remains unproven.

**Experimental data workaround.** [Recovery script](../../scripts/recover_nav_ephemeris.py)
decodes the saved NAV bits using local field definitions, cross-validates **37
fields** against each native PRN5/12/22 record, and adds PRN21 with its true
IODC=983/IODE=215 retained. [Recovered XML](results/local_evidence/runs/nav_audit_9dvjj0co/recovered_ephemeris.xml)
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
the local RTKLIB point solver. [Diagnostic script](../../scripts/diagnose_first_pvt_epoch.py)
uses epoch **2650**, byte offset **593600**, **224 bytes** (four channels × seven
little-endian doubles). All RX times are GPS TOW **14064.000 s**. Exact
[epoch JSON](results/local_evidence/runs/first_epoch_pvt_20261108_4/epoch.json) and
bytes (hft02 local artifact: `runs/first_epoch_pvt_20261108_4/epoch.bin`) are saved.

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
| [15° from zero](results/local_evidence/runs/first_epoch_pvt_20261108_4/native_path_trace.log) | PRN5 and PRN22 rejected; **2 satellites, 5 equations, 7 required**; solver return **0**, status **0** |
| [3° from zero](results/local_evidence/runs/first_epoch_pvt_20261108_4/existing_3deg_trace.log) | PRN5 still rejected; **3 satellites, 6 equations, 7 required**; solver return **0**, status **0** |
| [3° with independent-position seed](results/local_evidence/runs/first_epoch_pvt_20261108_4/existing_3deg_seeded_diagnostic.log) | Converges after four iterations, **4 satellites, 7 equations**; solver return **1**, `SOLQ_SINGLE=5`; LLH **41.880810573°, −87.644068692°, 256.807 m**, clock **−81.656300 ms** |

These are solver return values, not process exit codes or new native receiver
fixes. The original focused replay's
internal log directory (hft02 local artifact: `runs/rx1h_four_prn_axlbe7v2/internal`) records
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

The [logging-only patch](results/local_evidence/runs/first_epoch_pvt_20261108_4/logging_only.patch)
was used in a copied solver. The
[error-propagation proposal](results/local_evidence/runs/first_epoch_pvt_20261108_4/proposed_error_propagation.patch)
fixes local pointer assignment `msg = msg_aux` rather than a caller-buffer copy;
it remains unapplied. The [PVT-boundary logging proposal](results/local_evidence/runs/first_epoch_pvt_20261108_4/proposed_boundary_logging.patch)
is also not evidence of a running diagnostic receiver. `_1`/`_2` diagnostic
directories preserve compiler failures, `_3` the earlier 15° reconstruction,
and `_4` the three-case successful harness. `PVT.rtk_trace_level=4` alone did
not expose the local glog `VLOG` trace; saved harness commands use the glog route.

**Native build attempt.** [Preparation script](../../scripts/prepare_native_pvt_diagnostic.py)
made a logging-only source copy with hardware adapters/tests and dependency
fetching disabled. [First status](results/local_evidence/runs/native_pvt_confirmation_20261108_1/status.json)
and [recheck status](results/local_evidence/runs/native_pvt_confirmation_recheck/status.json) both
record **CMake return code 1**, receiver built/executed **false**, behavior changed
**false**. [Configure log](results/local_evidence/runs/native_pvt_confirmation_20261108_1/configure.log)
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
[packet/status log](results/local_evidence/runs/extref_once_20261109T004414Z_1bph5bsj/diagnostic.jsonl),
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
and [test log](results/local_evidence/runs/extref_idle_prepared_20261109T012546Z_95hauim6/test.jsonl),
which match the user-supplied result in this chat. Do not rerun the completed
one-shot directory: its exclusive attempt marker and logs now exist.

The [Python launcher](../../scripts/run_lime_external_reference_test.py) verifies
prepared hashes and host-root ownership checks, then launches the
[C++ helper](../../scripts/lime_external_reference_test.cc). No owners, scan
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
[stderr](results/local_evidence/runs/extref_idle_prepared_20261109T012546Z_95hauim6/test.stderr)
and a blank summary error string do not mean the lock criterion passed.
The nine [offline self-test scenarios](results/local_evidence/runs/extref_idle_prepared_20261109T012546Z_95hauim6/self_test.jsonl)
checked software accounting/cleanup before this execution; they were not RF tests.

**Meaning and limits.** The run **did not demonstrate external-reference lock**,
measure oscillator frequency, or test GNSS reception. Acknowledged programming
does not independently verify the physical ADF latches or the electrical reference
signal. The low status series leaves **the reference signal, PLL configuration,
and lock-status reporting as open questions**. The 1 Hz cadence is sampled evidence,
not a continuous electrical trace. Cleanup disabled ADF control in favor of DAC
code 125; it did not restore an unknown exact prior ADF state or verify DAC voltage.
No causal link to the November PVT failure follows from this idle clock test.

### Stock 90-second replay: installed receiver, unchanged configuration, 3° mask

**Purpose/setup.** Run one baseline on `hft02` using the installed
`/usr/bin/gnss-sdr`, without a build, installation, download, new RF capture or
configuration change. The binary reports **0.0.16** and the host package query
reports **gnss-sdr 0.0.16-1 amd64**. Its SHA-256 is
`92bd1d9e38228b8663021056203c0d9a2241f2b9a1de103d64dc5ab752335fee`, matching the
previous installed-binary audit. A fresh scratch directory was created at
`/home/rrama28/gnss/runs/stock_rx1h_90s_3deg_20261113T033819Z_eg_8pwsd/`.
The directory label records preparation time; the actual receiver execution
times below come from the run status, not its directory name.

Required input paths were checked before execution:

- Configuration: `/home/rrama28/gnss/runs/rx1h_pvt_lowmask_cs0kpzfz/config_used.conf`.
  It selects `File_Signal_Source`, 2 Msps, +500 kHz IF, four channels pinned to
  PRNs 5/12/21/22, `RTKLIB_PVT` Single mode, and **`PVT.elevation_mask=3.0`**.
- IQ: `/home/rrama28/gnss/runs/rx1h_baseline_20261108_035309_7qbMJ8/rx1h.cf32`,
  **1,440,000,000 bytes / 180,000,000 complex samples**, nominal **90 seconds**.
- Ephemeris: `/home/rrama28/gnss/runs/nav_audit_9dvjj0co/recovered_ephemeris.xml`,
  the **experimental** four-entry map including PRN21.
- Ionosphere and UTC: `/home/rrama28/gnss/runs/nav_audit_9dvjj0co/gps_iono.xml`
  and `/home/rrama28/gnss/runs/nav_audit_9dvjj0co/gps_utc_model.xml`.

All required inputs were present and readable. The receiver was launched with
the original configuration path; the run's `config_used.conf` is a byte-identical
provenance copy. No coordinate prior was supplied. The exact receiver command,
executed once with stdin closed and stdout/stderr captured to `run.log`, was:

```bash
cd /home/rrama28/gnss/runs/stock_rx1h_90s_3deg_20261113T033819Z_eg_8pwsd
/usr/bin/timeout --signal=INT --kill-after=10s 180s /usr/bin/gnss-sdr \
  --config_file=/home/rrama28/gnss/runs/rx1h_pvt_lowmask_cs0kpzfz/config_used.conf \
  --log_dir=/home/rrama28/gnss/runs/stock_rx1h_90s_3deg_20261113T033819Z_eg_8pwsd/internal \
  </dev/null >run.log 2>&1
```

The saved [command and exit record](results/local_evidence/runs/stock_rx1h_90s_3deg_20261113T033819Z_eg_8pwsd/exit_status.json)
records start **2026-11-13T05:28:27.057524Z**, finish **05:28:34.692131Z**,
elapsed **7.634608 s**, and **exit status 0**. The timeout did not fire. The
file source announced **89.9 s** to process and the final console receiver-time
line reached **1 min 30 s**. Exit zero is completion evidence, not a position fix.

**Measured receiver output.** The [console log](results/local_evidence/runs/stock_rx1h_90s_3deg_20261113T033819Z_eg_8pwsd/run.log)
reports **5 tracking starts**, **1 loss-of-lock event**, **4 bit-sync events**, and
**45 decoded GPS NAV subframes**:

| PRN | NAV messages | Subframe types represented |
| --- | ---: | --- |
| 5 | 13 | 1, 2, 3, 4, 5 |
| 12 | 9 | 1, 2, 3, 4, 5 |
| 21 | 12 | 1, 2, 3, 4, 5 |
| 22 | 11 | 1, 2, 3, 4, 5 |

The receiver explicitly logs loading all four assistance ephemerides. This does
not establish native acceptance of PRN21's decoded ephemeris without the workaround.
It also prints an `unrecognized XML syntaxFile: ./gps_almanac.xml` warning for
the unprovided optional default almanac in the fresh working directory. The
configured ephemeris/iono/UTC inputs loaded successfully; no default almanac was
created or substituted.

**First four valid observations and native rejection.** The native
observables dump (hft02 local artifact: `runs/stock_rx1h_90s_3deg_20261113T033819Z_eg_8pwsd/observables.dat`)
is **1,004,640 bytes / 4,485 epochs**, interpreted with the already documented
four-channel, seven-double layout. There are **2,435 consecutive epochs** with
all four `Flag_valid_pseudorange` values equal to 1, spanning TOW
**14052.000–14100.680**, nominal **48.7 s** at 20 ms cadence. The first is
zero-based epoch **2050**, byte offset **459200**. All four RX times are
**14052.000 s**:

| Channel | PRN | Interpolated transmit tag, s | Saved pseudorange, m | Valid-pseudorange flag |
| --- | --- | ---: | ---: | ---: |
| 0 | 5 | 14051.996768176508 | 968876.308168820 | 1 |
| 1 | 12 | 14052.011901261272 | -3567908.370005769 | 1 |
| 2 | 21 | 14052.006086997626 | -1824835.980243431 | 1 |
| 3 | 22 | 14052.001575158074 | -472220.510892355 | 1 |

Exact values are retained in [first-epoch JSON](results/local_evidence/runs/stock_rx1h_90s_3deg_20261113T033819Z_eg_8pwsd/first_four_valid_observations.json).
These are valid observation flags at the Observables output, **not proof that
four measurements survive PVT's elevation and other filters**. The stock logs
do not expose the final used-satellite count or individual rejection reasons.

The [native INFO log](results/local_evidence/runs/stock_rx1h_90s_3deg_20261113T033819Z_eg_8pwsd/internal/gnss-sdr.hft02.rrama28.log.INFO.20261113-052827.132453)
line **463** records the first solver failure:

```text
RTKLIB rtkpos error: 03:54:12.00: point pos error ()
```

This is the same GPS time-of-day as TOW 14052.000. Every four-valid epoch has a
matching native point-position error: **2,435 errors**, all with **empty reason
text**. There are **zero native position messages**, and no NMEA file or position
output file remains after exit. The NMEA printer was initialized, but initialization
of an output writer does not establish a fix. **No native PVT fix was reported or
saved.** Counts/window matching are saved in the
[observation summary](results/local_evidence/runs/stock_rx1h_90s_3deg_20261113T033819Z_eg_8pwsd/observation_window_summary.json)
and [native error records](results/local_evidence/runs/stock_rx1h_90s_3deg_20261113T033819Z_eg_8pwsd/native_pvt_errors.json).

**Interpretation/limits.** This run directly establishes that the stock receiver
decodes NAV and reaches four valid observation flags, yet reports point-position
failure throughout that interval. It does **not** directly confirm the standalone
elevation-filtering diagnosis: the stock log supplies no elevation, intermediate
position, filtered satellite list, residuals, or detailed solver failure condition.
The earlier standalone diagnosis remains prior evidence only.

The first four-valid epoch in this run is **14052.000**, not the earlier focused
run's **14064.000**. No identity of those acquisition histories is asserted. This
run also has four valid flags at TOW **14064.000** and a native empty-reason error
there (INFO line **1113**); its actual observations are saved separately in
[TOW 14064 JSON](results/local_evidence/runs/stock_rx1h_90s_3deg_20261113T033819Z_eg_8pwsd/tow_14064_observations.json).
Those measurements were not replaced by the earlier standalone inputs, and no
independent position or standalone solver was rerun.

**Outputs/preservation.** All new receiver outputs are in the fresh directory:
`run.log`, `internal/`, `observables.dat`, `tracking_ch_0.dat` through
`tracking_ch_3.dat`, and the receiver's saved `gps_ephemeris.xml`, `gps_iono.xml`
and `gps_utc_model.xml`. Run metadata, exact version/package output, first-epoch
observations, analysis and [summary](results/local_evidence/runs/stock_rx1h_90s_3deg_20261113T033819Z_eg_8pwsd/summary.json)
are stored alongside them. Before/after SHA-256 verification confirms that the
original config, IQ, three navigation inputs and installed binary are
[unchanged](results/local_evidence/runs/stock_rx1h_90s_3deg_20261113T033819Z_eg_8pwsd/input_hashes.json).
No earlier result was overwritten. Only this workspace report was updated;
the user-provided read-only document snapshot was not edited.

### Empty-error audit: first stock failure at GPS TOW 14052.000

**Scope/evidence.** This follow-up inspects the existing stock replay and local
source copies only. No receiver or standalone solver was executed; no IQ was
reprocessed, build attempted, configuration changed, or source patch applied.
The [native log](results/local_evidence/runs/stock_rx1h_90s_3deg_20261113T033819Z_eg_8pwsd/internal/gnss-sdr.hft02.rrama28.log.INFO.20261113-052827.132453)
line **463** remains the direct receiver evidence:

```text
RTKLIB rtkpos error: 03:54:12.00: point pos error ()
```

The prefix is GPS time-of-day corresponding to **TOW 14052.000**, not its
wall-clock execution time. The saved observation record is epoch **2050**, byte
offset **459200**. The audit independently checked those exact raw dump bytes
against the saved first-epoch JSON. A new
[native context extract](results/local_evidence/runs/point_pos_error_14052_audit__kio7sl6/native_first_failure_context.txt)
preserves the surrounding lines. All four assistance entries were loaded before
this epoch; PRN5 receives another ephemeris update at line **462**, immediately
before the first error, with Toe=14400 and WN=396. That line does not contain the
full updated ephemeris or all of its health/issue fields. The end-of-run XML is
not a complete PVT-boundary snapshot of this epoch.

**Where the text originates — source-level finding.** The inspected source is
the existing separate `native_pvt_confirmation_recheck/source/` tree. It already
contains the previously prepared logging-only changes, but was never built into
the stock executable. Its diagnostic additions explain shifted line numbers;
they do not constitute native receiver evidence. Exact source-to-installed-binary
equivalence is still unproven. The relevant unchanged algorithm and error-buffer
logic are preserved in [numbered source excerpts](results/local_evidence/runs/point_pos_error_14052_audit__kio7sl6/source_excerpts.txt):

1. `Rtklib_Solver::get_PVT()` calls `rtkpos()`. On return 0 it logs
   `RTKLIB rtkpos error: ` followed by `d_rtk.errbuf`. This is the stock log's
   `rtklib_solver.cc:898` emission point.
2. `rtkpos()` creates `char msg[128] = ""`, then calls `pntpos(..., msg)`.
   If that call fails, it formats `point pos error (%s)` using `msg`.
   `errmsg()` prefixes the solution time and copies the formatted text into
   `rtk.errbuf`. Its outer formatting does not generate a satellite rejection
   reason independently.
3. `pntpos()` explicitly clears `msg[0]` for nonempty input, propagates satellite
   positions, and calls `estpos(..., msg)`.
4. Three `estpos()` failure branches write their detailed reason into a local
   `char msg_aux[128]`. The common failure exit then executes **`msg = msg_aux`**.
   C++ passes that pointer by value: assigning it changes only the callee's
   pointer. It copies no bytes back into the caller's cleared buffer. Therefore
   `rtkpos()` can receive failure with `msg` still empty and print `()`.

This identifies a **source-level cause of lost diagnostic text**, separately
from the unresolved cause of the position failure in the installed receiver.
The observed native formatting is consistent with this code; it does not by
itself prove which branch the installed executable took.

| Local-source return path | Detailed text written | Destination | Expected caller text on this path |
| --- | --- | --- | --- |
| `rescode()` returns `nv < NX` | `lack of valid sats ns=%d` | Local `msg_aux` | Empty after the ineffective pointer assignment |
| `lsq()` returns nonzero `info` | `lsq error info=%d` | Local `msg_aux` | Empty |
| All `MAXITR=10` iterations are exhausted | `iteration divergent i=%d` | Local `msg_aux` | Empty |
| `pntpos()` receives `n <= 0` | `no observation data` | Caller `msg` | Nonempty |
| Converged estimate fails residual validation | `chi-square error ...` | Caller `msg` via `valsol()` | Nonempty |
| Converged estimate fails geometry validation | `gdop error ...` | Caller `msg` via `valsol()` | Nonempty |

The first row's `%d` argument is **`nv`, the equation count**, despite its `ns`
label. It must not be read as a satellite count. In this source `NX=7`, covering
position, receiver clock and three additional constellation clock offsets.
`ns` counts retained satellite measurements; `nv` also includes clock constraints.
The redundant pointer assignment on the converged path does **not** erase an
error already written by `valsol()` into the caller's buffer. Thus those validation
failures normally provide a reason in this implementation. This narrows the
source-based interpretation of blank text but is not a definitive exclusion of
paths in an unverified binary build. The four-channel GPS configuration also
cannot meet the `n >= 6` prerequisite for the RAIM retry. Velocity estimation
occurs only after successful position estimation; its failure is not what this
point-position error reports. The catalog is saved as
[source failure paths](results/local_evidence/runs/point_pos_error_14052_audit__kio7sl6/source_failure_paths.json).

**Which observations reached which stage.** The available source first gates
GPS L1 observations on the valid-pseudorange flag, matching PRN/signal and a
healthy ephemeris. It then converts them to RTKLIB observations, marking
`rcv=1`, and only invokes `rtkpos()` when more than three converted observations
exist. With exactly four configured GPS channels, the emitted solver error is
therefore consistent with **all four PRNs reaching the point-solver input**.
That membership/count is a **source-derived inference**, not a native dump of
the converted array. The native evidence directly records four Observables
flags and the solver failure; it does not record the array at the call boundary.

Within `rescode()` there are separate system, duplicate, geometric-distance,
elevation, code/pseudorange availability, satellite-exclusion, ionosphere and
troposphere rejection branches. Four inputs do not establish four retained
measurements or a least-squares call. At the first stock epoch:

| PRN | Native saved valid-pseudorange flag | Native computed elevation | Native result of requested 3° mask | Survives all native measurement filters |
| --- | ---: | --- | --- | --- |
| 5 | 1 | Not recorded | Not recorded | Not recorded |
| 12 | 1 | Not recorded | Not recorded | Not recorded |
| 21 | 1 | Not recorded | Not recorded | Not recorded |
| 22 | 1 | Not recorded | Not recorded | Not recorded |

The actual post-filter **`ns`**, equation count **`nv`**, iteration number,
least-squares return code and per-satellite `vsat` values at **14052.000** are
missing. The wrapper sets its public valid-observation count to **zero on any
`rtkpos()` failure**; that reset is not evidence that zero measurements survived.
The stock INFO log contains none of the `estpos`, `resprng`, `satazel error`,
`lack of valid sats`, `lsq error`, `iteration divergent`, `gdop error`,
`chi-square error`, `RTKLIB TRACE` or prepared PVT-boundary diagnostic records.
Tracking dumps do not supply the solver's current position/elevations. Absent
NMEA/position output and end-of-run navigation XML cannot recover these fields.
The [native evidence/missing-fields record](results/local_evidence/runs/point_pos_error_14052_audit__kio7sl6/native_evidence_and_missing_fields.json)
explicitly stores the unavailable fields as null.

**Prior standalone values, not native values for this epoch.** The already
saved [3° standalone trace](results/local_evidence/runs/first_epoch_pvt_20261108_4/existing_3deg_trace.log)
is for the other replay's **TOW 14064.000**, with its saved observations and an
ECEF-zero initialization. Its iteration-1 results are:

| PRN | Standalone-derived elevation at 14064.000 | 3° mask in that standalone solve |
| --- | ---: | --- |
| 5 | 1.797421352° | Reject |
| 12 | 58.147161664° | Pass |
| 21 | 27.267272705° | Pass |
| 22 | 14.171253275° | Pass |

That reconstruction retained **3 measurements / 6 equations**, failed `nv < 7`,
and printed the local reason while its caller buffer remained empty. This is
specific prior evidence for the elevation hypothesis and the error-copy defect.
It supplies **no observed native elevations or filter counts for TOW 14052.000**.
No new standalone calculation was made or transferred to the first stock epoch.

**Smallest diagnostic change, proposed only.** To distinguish the three
message-losing branches, replace just the common failure-exit pointer assignment
with a bounded copy into the existing caller's 128-byte buffer:

```cpp
std::snprintf(msg, 128, "%s", msg_aux);
```

This changes error reporting only. It does not change initialization, the 3° mask,
filtering, weights or solution validity. The earlier
[error-copy proposal](results/local_evidence/runs/first_epoch_pvt_20261108_4/proposed_error_propagation.patch)
already contains this fix plus removal of the redundant converged-path assignment;
it remains **unapplied**.

To test elevation filtering specifically, also add a bounded diagnostic for
**TOW 14052.000** at the native error branch: print the actual converted input
PRNs/count, configured mask, and each satellite's `ssat[sat-1].azel[1]`, `.vs`
and residual. The available `pntpos()` code populates those arrays even after
an `estpos()` failure. Log them before the wrapper resets its public observation
count. An early rejection before geometry leaves zero angle placeholders, so
zero must not be presented as a computed elevation; tag geometry-not-computed
and the rejected branch inside `rescode()` when necessary. A target-only record
just after `rescode()` returns can additionally capture **iteration, `x`, `ns`,
`nv`, `NX` and `vsat`**, without confusing equations with satellites. These are
the minimal additional observations needed to tie low elevation to the actual
native failure, rather than infer it from the earlier standalone solve.

The old prepared PVT-boundary logging targets **14064.000**; it would miss the
first failure unless its target were changed to **14052.000**. Existing glog
verbosity could expose some internal traces, but does not fix the missing buffer
copy and is not itself a saved measurement. No logging flag, receiver, config or
source was changed for this audit. No build or new replay was attempted.

**Preservation.** The [audit preservation record](results/local_evidence/runs/point_pos_error_14052_audit__kio7sl6/preservation_hashes.json)
confirms unchanged hashes for the inspected original replay files, configuration,
ephemeris inputs, installed binary and source copies. IQ was not opened or replayed.
Only this report and new analysis artifacts were written. The stock replay still
depends on experimental PRN21 XML, supplies no receiver coordinates and has no
reported native PVT fix. No native elevation-filtering confirmation follows from
the existing empty-reason errors. No commit or push was made.

### Native TOW 14052 diagnostic request: blocked at local dependency check

**Purpose/outcome.** Check for an existing diagnostic receiver or an isolated
build with complete compatible dependencies before adding bounded error copying
and TOW-14052-only logging. Following the native build report, a fresh read-only
inventory was performed **on hft02 outside the restricted filesystem view** at
**2026-11-13T05:59:41.926098Z**. No usable native diagnostic receiver was found
in the searched locations. Required development inputs are still absent, so
work stopped **before changing a source copy, configuring/building GNSS-SDR or
running a replay**. No install, download, sudo, stock replacement, commit or push
was performed.

Evidence is saved in the fresh directory
`/home/rrama28/gnss/runs/native_14052_dependency_check_n17mm09y/`:

- [Host inventory](results/local_evidence/runs/native_14052_dependency_check_n17mm09y/host_inventory.json):
  searched paths, binary candidates, CMake cache entries, development files,
  package-cache/source-cache checks, compiler preprocessing results and access limits.
- [Preflight log](results/local_evidence/runs/native_14052_dependency_check_n17mm09y/preflight.log):
  exact missing-header diagnostics; this is not a GNSS-SDR build/replay log.
- [Package versions](results/local_evidence/runs/native_14052_dependency_check_n17mm09y/package_query.txt):
  installed stock receiver and dependency runtimes; missing development packages.
- [Build status](results/local_evidence/runs/native_14052_dependency_check_n17mm09y/build_status.json):
  explicitly records source edits, build and replay as not performed.

**Existing binary/build search.** The inventory covered accessible locations under
`/home/rrama28`, `/usr/local`, `/opt` and `/tmp`, standard system development
paths, and relevant archives in `/var/cache/apt/archives`. It excluded credential,
editor/plugin, Git, package-cache and generated dependency directories listed in
the JSON; unrelated protected service/container directories could not be read.
Thus this is a scoped availability result, not proof about every filesystem
location. The only matching non-stock ELF programs found were
`runs/first_epoch_pvt_20261108_3/first_pvt_epoch` and
`runs/first_epoch_pvt_20261108_4/first_pvt_epoch`: **standalone epoch harnesses**, not
native receiver executables. They were not run.

The two existing isolated receiver build directories
`runs/native_pvt_confirmation_20261108_1/build/` and
`runs/native_pvt_confirmation_recheck/build/` still cache missing PugiXML
development paths and contain no usable receiver. The original
`/home/rrama28/src/gnss-sdr-0.0.16/build/` cache also lists missing PugiXML,
Protobuf headers/libraries/compiler and VOLK-GNSSSDR library discovery. Its
`build/thirdparty/pugixml/` and `build/thirdparty/protobuf/` directories each
contain **zero regular files**. No matching local dependency archive or alternate
header/compiler set was found in the searched locations. The existing GPSTk
build cache does not supply these missing dependencies.

**Exact confirmed missing files.** The host compiler's `c++ -x c++ -E -` probes
each returned **1**, with fatal missing-include diagnostics:

| Required development input | Missing conventional path | Compatible version for existing runtime |
| --- | --- | --- |
| PugiXML public header | `/usr/include/pugixml.hpp` | 1.12.1 |
| PugiXML configuration header | `/usr/include/pugiconfig.hpp` | 1.12.1 |
| Protobuf public message header | `/usr/include/google/protobuf/message.h` | 3.12.4 |
| Protobuf support header | `/usr/include/google/protobuf/stubs/common.h` | 3.12.4 |
| Protobuf schema compiler | `/usr/bin/protoc`; also absent at `/usr/local/bin/protoc` and on PATH | 3.12.4 |

The Protobuf headers must come from the **complete matching header distribution**;
the two named files are confirmed missing examples, not a sufficient header set
by themselves. The inventory also found no alternate copies of these required
files under its search roots.

The versioned runtimes **do exist**:
`/usr/lib/x86_64-linux-gnu/libpugixml.so.1.12`
(`libpugixml1v5 1.12.1-1 amd64`) and
`/usr/lib/x86_64-linux-gnu/libprotobuf.so.23.0.4`
(`libprotobuf23 3.12.4-1ubuntu7.22.04.6 amd64`). The automatic link-time discovery
names `libpugixml.so` and `libprotobuf.so` are absent; explicit local CMake
library paths could use the existing versioned files once matching headers and
tools are available. If a future local `protoc` dynamically needs
`/usr/lib/x86_64-linux-gnu/libprotoc.so.23`, that compiler runtime is absent too.
No new runtime or headers were substituted. These are confirmed prerequisites;
later compile/link stages remain untested.

**Native result and limits.** There is **no new native TOW 14052 trace**, so this
attempt cannot identify the actual solver failure path, per-satellite elevations,
3° decisions, iteration or `ns/nv` counts. It does not promote the earlier
standalone elevation diagnosis to native confirmation. The stock executable's
SHA-256 still matches the previous stock baseline; configs and inputs were not
modified. The requested diagnostic would retain the same experimental PRN21 XML,
3° mask and no supplied coordinates, but that replay was not performed. No
fabricated build or replay log is presented in place of the preflight result.

## 2026-11-13: exact 14052 reconstruction and provisional-position candidate

**Scope.** This task built only isolated standalone epoch harnesses using existing
local dependencies. It did not retry a full receiver build or perform a new native
replay. Original configs, saved observations/NAV, IQ and the installed binary are
unchanged; [fresh hash checks](results/local_evidence/runs/epoch14052_bootstrap_dvazj6li/preservation.json)
include the 1.44 GB IQ against the prior stock-run manifest. No package changes,
downloads, sudo, upload, commit or push occurred.

**Inputs.** The actual stock replay's
observables (hft02 local artifact: `runs/stock_rx1h_90s_3deg_20261113T033819Z_eg_8pwsd/observables.dat`)
record 2050 / offset 459200 contains RX TOW exactly **14052.000** for all four
channels, range-valid flags 1, and PRNs **5,12,21,22**. All saved values were retained
in [epoch14052.json](results/local_evidence/runs/epoch14052_bootstrap_dvazj6li/epoch14052.json).
No 14064 measurements were substituted. The unchanged experimental assistance
contains healthy ephemerides with Toe/Toc 14400, WN 396 -> full week 2444 and age
-348 s; native-library ephemeris selection and satellite-position calculation
succeed. These are preloaded assistance, including later NAV tag 14088, not proof
of unassisted availability at that epoch. [Navigation audit](results/local_evidence/runs/epoch14052_bootstrap_dvazj6li/navigation_input_audit.json)
verifies PRN21 alone was added and all existing PRN5/12/22 XML fields stayed intact.

**First reconstructed failure.** Zero initial ECEF/clock -> iteration 0 ns=4/nv=7 ->
successful first LSQ update -> iteration 1 elevations PRN5 **1.721378797°**,
PRN12 **58.103683246°**, PRN21 **27.176934912°**, PRN22 **14.259101015°**.
Only PRN5 fails 3°. Then **ns=3 / nv=6 / required=7** fails before the next LSQ call.
The string `lack of valid sats ns=6` misleadingly prints the equation count.
[Full baseline trace](results/local_evidence/runs/epoch14052_bootstrap_dvazj6li/baseline_first.log)
and [JSON result](results/local_evidence/runs/epoch14052_bootstrap_dvazj6li/baseline_first.jsonl)
record the state/counts. The existing harness independently reproduces this exact
14052 failure with empty caller text; the separate bounded copy repair exposes
the reason without changing solver decisions.

**Candidate and continuity.** A [separate functional patch](results/local_evidence/runs/epoch14052_bootstrap_dvazj6li/build2/provisional_position_only.patch)
defers only the mask during zero-position bootstrap; after provisional convergence
it runs residual selection/solve with the original 3° options and existing final
validation. The shared 10-iteration limit remains. At 14052 provisional iterations 0–6
retain four satellites; configured-mask iteration 7 passes with elevations
**4.184817452°,57.826873826°,30.054682690°,17.235804852°** and ns=4/nv=7.
The [candidate trace](results/local_evidence/runs/epoch14052_bootstrap_dvazj6li/candidate_first.log)
shows `valsol()` and standalone `SOLQ_SINGLE` status5. No receiver coordinates
were supplied. The baseline fails **0/2435 successes**; the candidate succeeds
**2435/2435**, from 14052.000 to14100.680 without 20 ms gaps, both resetting at every
epoch and carrying position forward. The [original 15° control](results/local_evidence/runs/epoch14052_bootstrap_dvazj6li/candidate_first_15deg.jsonl)
rejects PRN5 after provisional convergence and reports insufficient equations.

**Quality limits.** Sequential residual RMS is at most 2.71e-5 m, maximum absolute
residual 5.15e-5 m, GDOP 7.03115–7.09429. With only four ranges, `nv==NX`; the unchanged
chi-square test has no redundant degrees of freedom. Nearly zero residuals do
not establish accuracy. Positions scatter 55.52 m RMS in 3D, with maximum 16.83 m
consecutive step and height 144.55–360.87 m. The historical approximate location
provides a consistency check only: 12.55 m horizontal difference at the first
solution, 1.05–109.05 m over the sequence; no surveyed coordinates/height are
available. An independent position calculation was not repeated or used as a seed.
[Metrics and counts](results/local_evidence/runs/epoch14052_bootstrap_dvazj6li/window_summary.json),
[exact commands/exits](results/local_evidence/runs/epoch14052_bootstrap_dvazj6li/window_commands.json),
[build commands](results/local_evidence/runs/epoch14052_bootstrap_dvazj6li/build2/build_commands.json)
and full report/reproduction (hft02 local artifact: `docs/RX1H_14052_BOOTSTRAP_RESULTS.md`) are retained.

**Still unverified.** No successful **native receiver** fix or native failure-path
confirmation is claimed. Missing full native selected ephemeris at the first
failure, native initial state/solver boundary, and post-filter trace prevent that
conclusion. Saved final XML equals the assistance numerically but cannot prove
first-epoch state. CN0/extra flags were not dumped; SNR masking is disabled in
the reconstructed setup. Native feedback and acquisition scheduling are outside
the harness. **All successful candidate tests depend on the experimental PRN21
XML**, and the available local source is not proven identical to the packaged
binary. External-reference lock remains unverified and was not tested here.

**Prepared next step.** [Native plan](results/local_evidence/runs/epoch14052_bootstrap_dvazj6li/native_plan/README.md)
separates error-copy repair, exact-TOW diagnostics and functional candidate.
Both native patch profiles apply cleanly; solver diagnostic units compile, but
the full receiver/boundary wrapper do not have a verified build. Matching
PugiXML 1.12.1 headers and Protobuf 3.12.4 headers/protoc (and libprotoc runtime if
needed) remain the confirmed local blockers. The plan uses preprovisioned
compatible dependencies elsewhere and network-disabled builds, then diagnoses
before changing behavior. It specifies inputs, replay command and logs to
separate filtering, LSQ, divergence and final-validation paths. No external
upload, provisioning or CI execution occurred; obtain approval first.

## Where to resume and what not to infer

1. Preserve 90 s IQ (hft02 local artifact: `runs/rx1h_baseline_20261108_035309_7qbMJ8/rx1h.cf32`),
   focused observations (hft02 local artifact: `runs/rx1h_four_prn_axlbe7v2/observables.dat`),
   [focused config](results/local_evidence/runs/rx1h_four_prn_axlbe7v2/config_used.conf), the
   [3° config](results/local_evidence/runs/rx1h_pvt_lowmask_cs0kpzfz/config_used.conf), and their
   experimental NAV provenance as the regression set. Independent-position
   calculations and standalone seeded successes must remain labelled as such.
2. Resolve the native build dependency gap before claiming a native rejection
   trace or continuous receiver fixes. The exact 14052 standalone bootstrap
   candidate now passes the saved 2435-epoch window, but does not establish native
   or unassisted cold-start success. Keep logging, caller-error correction and
   the tested functional candidate distinct.
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
[historical launch logs](results/local_evidence/runs/historical_launch_logs), preserving their
names and contents. Their embedded absolute references to absent run directories
were already unresolved; moving the logs neither repairs nor changes those records.

Other historical reports stay in [docs](..): their relative sibling and
`../runs`/`../output` links must keep working. Scripts stay in
[scripts](../../scripts) because launchers derive the project root from their
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
