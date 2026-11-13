# One RX1_H path-verification capture

**Latest result:** the user completed the 90 s capture. Offline replay now
demonstrates sustained NAV tracking and decoded NAV from four PRNs. A specific
0.0.16 ephemeris comparison rejects PRN21; an isolated data-only workaround
produces four valid observations but native PVT remains unresolved. See
[RX1H_90S_RESULTS.md](RX1H_90S_RESULTS.md) for the evidence and diagnostic runs.
External-reference lock remains unverified.

## Successful capture and GPS NAV decoding

`runs/rx1h_baseline_20261108_034130_Y7gMFe/` saved 60 million finite complex
samples (480 MB, nominally 30 s). Before and after capture the driver reported
channel 0 / LNAH, about 2 Msps, LO 1574919990.234375 Hz and gain 45 dB.
The log reports successful RX calibration and no stream errors. This does
not independently establish uninterrupted samples or external-reference lock.

The recording was replayed without opening hardware, assistance XML, or pinned
historical PRNs. GPS L1 is at +500 kHz relative to the nominal LO, so
`InputFilter.IF=500000` was used. This differs from the negative IF in the
historical focused config.

| Offline acquisition | Bit sync | NAV messages | Result location |
| --- | --- | --- | --- |
| 1 ms, 250 Hz Doppler bins, CFAR pfa 0.001 | 0 | 0 | `runs/offline_baseline_LUhwbthK/` |
| 4 ms, 125 Hz Doppler bins, same CFAR pfa | 2 | 4 | `runs/rx1h_offline_4ms_rnuld_e8/` |

The second replay decoded subframes 2 and 3 from GPS PRNs 21 and 22. Those
tracks ran from approximately 0.49/0.54 s to 29.88 s with no logged loss on
their channels. Median estimated C/N0 over the final 10 s was approximately
38.8 and 36.7 dB-Hz, respectively. Other channels still had losses; the overall
replay had 22 tracking starts and 10 losses. This establishes usable GPS signals
in this Lime capture and sustained NAV-capable tracking on two satellites.
It does not isolate a single cause of the earlier failures or provide a fix.

The working file-source configuration is `configs/lime_rx1h_offline_4ms.conf`.
Exact run configs, logs, summaries and tracking dumps are preserved. IQ
statistics and a PSD/tracking plot are in the capture folder as
`iq_analysis.json` and `rx1h_analysis.png`.

## Completed longer capture: duration only

A 90 s capture on the same RX1_H path would give the receiver more time to
collect full NAV subframe sets and find additional usable satellites. Only
two satellites decoded NAV in the 30 s recording; a standard unconstrained
position solution needs at least four usable satellites. More recording time
alone does not guarantee that additional satellites will become usable.

Passive preview:

```bash
bash scripts/run_rx1h_baseline.sh --seconds 90
```

Live command for a separately approved/manual run:

```bash
bash scripts/run_rx1h_baseline.sh --run --seconds 90
```

This retains the same driver, antenna, channel, rate, LO and gain requests.
It saves 1.44 GB, requires at least 1.96 GB free space, and limits the capture
process to 120 s plus at most 5 s forced cleanup. Opening still initializes
and calibrates the device as described below. No explicit clock or antenna
power setting is added. The user completed this capture. The agent performed
only subsequent offline replays and data analysis.

## First attempt: antenna readback succeeded, capture aborted

`runs/rx1h_baseline_20261108_033836_SOAd6t/` opened the matching device using
the isolated system 20.10 driver. Before streaming, it read back channel 0,
LNAH, 1999999.9809265137 samples/s, 1574919990.234375 Hz and 45 dB total gain
(TIA 12, LNA 27, PGA 6 dB). No IQ file was created.

The original script incorrectly required exact floating-point equality with
2000000 samples/s. It now allows an absolute difference of 1 sample/s
(0.5 ppm) both before and after capture, and rejects non-finite values. The
observed difference was only -0.0190734863 samples/s. This is a software
validation correction; it changes no requested hardware settings and does
not establish physical clock accuracy or external-reference lock. Original
run artifacts are preserved. The subsequent corrected capture is described above.

## Most recent saved GNSS-SDR live decoding run

The latest saved live receiver log is
`runs/bitsync_fix_20260520_065536/run.log`. More recent `offline_baseline_*`
folders contain file replays, not live receiver runs.

Shell history lines 1966–1974 identify the launch:

```bash
LimeUtil --refclk="serial=0009061C01502715" --fref=10000000
RUN_ID=$(date -u +%Y%m%d_%H%M%S)
RUN_DIR=~/gnss/runs/bitsync_fix_${RUN_ID}
SESSION=bitsync_fix_${RUN_ID}
mkdir -p "$RUN_DIR"
tmux new-session -d -s "$SESSION" "cd '$RUN_DIR' && timeout --signal=INT 15m gnss-sdr --config_file=$HOME/gnss/configs/limesdr_focused.conf"
tmux pipe-pane -o -t "$SESSION" "cat >> '$RUN_DIR/run.log'"
```

This is historical evidence, not a command to rerun. The log ends after about
68 s with `^C`, although the launch allowed 15 minutes. The preceding clock
command has no saved result in that log. External-reference lock is unverified.

The log confirms arguments containing `serial=0009061C01502715,chan=1,antenna=LNAW`
and connection to the matching LimeSDR-USB. It reports 2 Msps, LO about
1574.92 MHz and total gain 45 dB. It provides no effective antenna readback or
physical RX-channel mapping. `RF Channels: 1` is a count, not evidence of RX2.
The current config matches those arguments, but this run did not save an
immutable config snapshot. `Channel0.satellite` etc. are GNSS processing
channels, not the Lime's RF connectors.

The manager reports splitter feeds on RX1_H and RX2_H. These correspond to the
H path (`LNAH`); `LNAW` requests another path. The actual old hardware selection
cannot be recovered from this log. The local GNSS-SDR Osmosdr adapter connects
source output 0; `chan=1` alone is not a verified RF-channel selection.

## Passive inspection versus live operation

File/history/log/header checks and `SoapySDRUtil --info` do not create a radio
instance. Setting `SOAPY_SDR_PLUGIN_PATH` alone adds a search path and does not
exclude the duplicate local plugin. A process-specific empty `SOAPY_SDR_ROOT`
together with the system plugin path was checked using `--info` and excludes
the local 22.09 module.

The installed Osmosdr API exposes `get_num_channels()`, `set_antenna()` and
`get_antenna(channel)`. The simplest useful live check is to explicitly use one
source/RX channel 0, set `LNAH`, and read it back in that same owning process
before and after capture. This verifies the driver-reported H path. Physical
cable routing and signal quality remain separate questions.

Creating the source opens and initializes hardware. The baseline requests
RX channel 0 (reported RX1_H), 2 Msps, LO 1574920000 Hz, manual gain using the
same calls as the historical config: total-gain request 15, IF call 40 (the
adapter's default `rf_gain`), BB call 6. Historical total readback was 45 dB;
the test aborts if it differs by more than 1 dB. It logs individual gain stages.
It does not call a bandwidth setter; initialization/calibration defaults apply,
and any available bandwidth readback is recorded. The old log's bandwidth -1
did not establish a physical filter bandwidth.

Opening/initialization and RX activation can reset defaults and calibrate the
device. No explicit clock-selection API, antenna-power control, TX stream,
firmware update, or persistent-setting write is requested. Initialization may
affect previous clock state: no external-clock preservation or lock is claimed.

## Exact proposed operation

Passive preview, already checked:

```bash
bash scripts/run_rx1h_baseline.sh
```

After approval, from `/home/rrama28/gnss`:

```bash
bash scripts/run_rx1h_baseline.sh --run
```

The live command checks for a GNSS-SDR process and a USB owner first, aborting
if an owner/error is reported. The USB node is currently `/dev/bus/usb/002/007`;
if it changes, revalidate the sysfs mapping before editing the runner. Other
users' handles may require an administrator to establish exclusive access.

The capture uses system SoapyLMS7/LimeSuite 20.10 throughout. Loaded library
paths are checked before requested RF settings are applied. This does not
replace, remove, or modify installed drivers.

It discards the first 1 s and saves 30 s (60 million CF32 samples, 480 MB).
The capture process has a 60 s wall-time limit plus at most 5 s forced cleanup.
No GNSS tracking/acquisition settings are changed because this step saves raw
source IQ for subsequent offline analysis; no decoding claim is made.

Output: `runs/rx1h_baseline_<UTC timestamp>_<unique suffix>/`, containing:

- `run.log`, `module_info.txt`, `loaded_libraries.txt`, and `exit_status.txt`.
- `requested.json`, `after_open.json`, `before_capture.json`, `after_capture.json`.
- Exact script copies and a clearly labeled current copy of the historical config.
- `rx1h.cf32` and `summary.json`.

## Success criteria

1. The selected serial matches the connection log, exactly one source channel
   is used (index 0), and only system LimeSuite 20.10/module paths are loaded.
2. Driver readback reports LNAH before and after capture, 2 Msps within an
   absolute tolerance of 1 sample/s (0.5 ppm), and frequency
   within 100 Hz of the requested LO. Total gain matches the historical 45 dB
   within 1 dB and remains consistent.
3. Exactly 480 MB of IQ is saved, sampled beginning/middle/end windows are finite
   with nonzero I/Q variance, and there are no reported stream/calibration errors.
   Inspect the log as well as the automatic summary; the wrapper cannot prove
   sample continuity or absence of unreported stream losses.

Passing establishes a reproducible, driver-reported RX1_H capture baseline.
It does not establish antenna-feed quality, GNSS NAV decode, a position fix,
or external-reference lock. Compare the saved IQ offline next, with its
documented +500 kHz GPS L1 offset; do not feed it into an IF=0 replay template.
