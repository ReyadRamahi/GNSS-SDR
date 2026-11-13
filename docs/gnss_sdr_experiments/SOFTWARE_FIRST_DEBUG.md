# Software-first LimeSDR diagnosis

**Current result:** the 90 s RX1_H recording demonstrates sustained GPS NAV
tracking and decoded NAV from four PRNs using +500 kHz IF and 4 ms acquisition.
A specific 0.0.16 issue-of-data comparison rejects PRN21's ephemeris. An
isolated data-only workaround and focused replay produce four valid
observations, but native GNSS-SDR PVT still does not fix. No installed receiver
software or clock settings were changed. See
[RX1H_90S_RESULTS.md](RX1H_90S_RESULTS.md) for evidence and remaining work.
External-reference lock remains unverified. The notes below preserve the
earlier audit and archived-recording results.

Physical RF and reference-clock wiring is currently unknown. Do not interpret
configuration values or USB enumeration as proof of a physical connection.

## Checks completed without opening the radio

- Installed receiver: `/usr/bin/gnss-sdr`, version 0.0.16, package 0.0.16-1.
- SoapySDR: 0.8.1; gr-osmosdr package: 0.2.3-5build2 (library ABI 0.2.0).
- USB sysfs shows LimeSDR serial `0009061C01502715` at 5000 Mbit/s, behind
  several hubs. This confirms enumeration and negotiated link speed only.
- Two Lime modules are present. The system module links to LimeSuite 20.10;
  the `/usr/local` module links to LimeSuite 22.09. `/usr/local/bin/LimeUtil`
  also links to 22.09. Historical receiver logs report duplicate registration.
  The effect on actual receiver behavior has not been isolated.
- The execution sandbox exposes USB sysfs metadata but no `/dev/bus/usb`
  or serial nodes. No live receiver or device probe was run.
- Historical XML assistance is from GPS week 2419. It is unsuitable for a new
  live run. Offline acquisition/tracking below does not use assistance or the
  current wall-clock visibility prediction.

## Reproducible offline baseline

Run from the project root:

```bash
bash scripts/run_offline_baseline.sh
```

The default input is the archived `lime_baseline_no_10mhz_20260428_044448.dat`
capture. The template assumes CF32 IQ at 2 Msps centered on GPS L1, based on
the historical capture configuration. Those facts are not embedded in the IQ
file. An alternative file must have the same format, rate and center frequency:

```bash
bash scripts/run_offline_baseline.sh /absolute/path/to/capture.dat
```

The runner uses `File_Signal_Source`, never opens SDR hardware, creates a fresh
run directory, saves the exact config and metadata, and stores console logs,
internal logs, tracking dumps and `summary.json`. GNU Radio may also write its
normal FFT planning cache/lock under the user's home directory.

The baseline scans PRNs, uses a 1 ms acquisition interval with `pfa=0.001`,
blocks during offline acquisition, and keeps default lock-failure tests.
It does not repeat the recording or use ephemeris assistance. Its PVT output
is not a validated historical-position test; first assess bit sync and NAV.

Completed run: `runs/offline_baseline_sgt38Nyw/`:

| Measurement | Result |
| --- | --- |
| Last reported receiver time | 58 s |
| CFAR enabled in internal log | Yes |
| Positive acquisitions / tracking starts | 20 / 20 |
| Lock losses | 13 |
| Bit synchronization events | 0 |
| NAV messages | 0 |
| NMEA bytes | 0 |

This reproduces the symptom from saved samples without a live USB stream.
It does not distinguish corrupted/weak captured signals, false acquisitions,
or tracking-loop behavior. A known-good, documented GPS IQ recording is the
next useful software control. Replaying only Lime recordings cannot establish
that the receiver software or the historical RF setup is healthy.

The first sandbox attempt, `runs/offline_baseline_Vw5RO5Ja/`, failed while
creating GNU Radio's home-directory FFT wisdom lock. It never connected the
flowgraph. It is not a valid signal-processing result. The subsequent run
completed after allowing that cache access.

## Configuration corrections to carry into a future live baseline

- In GNSS-SDR 0.0.16, `Acquisition_1C.pfa` selects CFAR. The
  `Acquisition_1C.use_CFAR_algorithm=true` entry alone is not read as a switch.
- This tracking implementation reads `Tracking_1C.max_lock_fail` for the
  code-lock failure limit, not `Tracking_1C.max_code_lock_fail`.
- Do not compare time spent in tracking after changing failure limits as if
  it demonstrated a stronger signal. Compare lock metrics, bit sync and NAV.
- Verify the actual RF channel and antenna selection. `chan=1` in old source
  arguments and a filename containing `rx2` do not prove which socket was used.
- Establish actual IQ orientation before interpreting the offset-LO tests.
- The Doppler helper defaults to UIUC while receiver configs use Chicago;
  provide the real location explicitly. Its current age calculation also
  ignores the ephemeris week, so old XML may appear misleadingly fresh.
- Preserve the existing driver installations until a process-specific library
  isolation test is prepared; do not delete libraries or flash gateware yet.

## Details someone at the hardware must confirm

1. Exact Lime RF connector label and the complete antenna-to-Lime signal path.
2. Antenna model, mounting/location and sky view; every splitter, filter, LNA
   and cable; splitter insertion loss and which output reaches the Lime.
3. Active antenna/LNA power source and DC-pass route. Confirm that the feed
   intended for the Lime has appropriate DC isolation.
4. Whether a reference is physically connected; source model, output enabled,
   frequency and level; exact Lime clock connector and relevant jumper state.
5. Lime power supply and USB cable/hub arrangement, and whether other users or
   applications are sharing these devices before scheduling a live test.

## Later software checks that open or configure the device

A live probe can report antenna choices, gain ranges, firmware/gateware and
sensors, but device construction may initialize or calibrate the radio.
Treat this as a separate step after checking device ownership. A `clock_locked`
sensor may describe an internal PLL; it is not by itself proof of external
10 MHz reference lock. A reference-setting command actively changes state.

After the wiring is confirmed, use one verified RX input and driver stack,
read back sample rate/frequency/antenna/gain stages, and capture a bounded IQ
recording with timestamps and stream-error information. Compare the recording
offline before changing gain, clock, IF sign or tracking parameters one at a time.
