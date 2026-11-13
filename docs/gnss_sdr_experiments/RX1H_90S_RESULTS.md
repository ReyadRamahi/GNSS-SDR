# RX1_H 90-second recording: NAV works; native PVT remains unresolved

Follow-up: [the single-epoch PVT diagnosis](RX1H_FIRST_EPOCH_PVT.md) now
reproduces the first failure in the local solver source: elevation filtering
after the first position update leaves insufficient equations. It also explains
the existing 3-degree experiment's initialization failure. Original full
receiver replays still have no native PVT fix; the history below is preserved.

Capture: `runs/rx1h_baseline_20261108_035309_7qbMJ8/`. The user performed the
live capture. Subsequent agent work used only saved files and local software.
No installed receiver, driver, firmware, gateware, antenna-power or explicit
reference-clock setting was changed.

## Capture and unchanged replay

The capture saved 180 million finite complex samples (1.44 GB). Before/after
readbacks match: source channel 0, LNAH, approximately 2 Msps, LO
1574919990.234375 Hz, total gain 45 dB (TIA 12, LNA 27, PGA 6). No stream
errors were reported. This does not independently prove sample continuity or
external-reference lock.

`runs/rx1h_offline_90s_1i1wopzh/` uses the working 4 ms acquisition,
125 Hz Doppler bins, CFAR pfa 0.001, and +500 kHz IF. Its only change from the
successful 30 s replay configuration is the IQ filename. It produced 36 NAV
subframes from four PRNs, 56 tracking starts, 44 losses overall and no fix.
Many acquisition starts still do not correspond to useful tracks.

| PRN | Baseline track behavior | NAV result |
| --- | --- | --- |
| 5 | 88.6 s without logged loss | Repeated subframes 1–5 |
| 12 | Lost initial track; held final 67.3 s | Subframes 1–5 |
| 21 | 89.4 s without logged loss | Repeated subframes 1–5 |
| 22 | Two 25–26 s segments with loss/reacquisition | Partial NAV in this replay |

Tracking segments, IQ analysis and native replay counts are saved as JSON in
the capture/replay directories. Stable NAV-capable reception is now established
for this H-path recording; a current external-reference lock is not.

## A specific ephemeris rejection

`scripts/audit_offline_nav.py` replays a file source and receives its decoded
NAV monitor on localhost only. It installs nothing and contacts no external
service. Run `runs/nav_audit_9dvjj0co/` captured 43 messages, including all five
subframe types for PRNs 5, 12, 21 and 22. Acquisition timing can vary with
thread scheduling, so counts/PRN22 outcomes differ across replays.

The raw NAV monitor supplies these values:

| PRN | IODC | IODE in SF2/SF3 | Health | Native ephemeris emitted |
| --- | --- | --- | --- | --- |
| 5 | 49 | 49 / 49 | 0 | Yes |
| 12 | 48 | 48 / 48 | 0 | Yes |
| 21 | 983 | 215 / 215 | 0 | No |
| 22 | 23 | 23 / 23 | 0 | Yes |

The local 0.0.16 source at
`/home/rrama28/src/gnss-sdr-0.0.16/src/core/system_parameters/gps_navigation_message.cc:531`
compares the full IODC directly against IODE. IODC is a 10-bit field; IODE is
8 bits. PRN21's IODC low eight bits are 215 (`983 & 255`), consistent with both
IODE fields, but the full-value comparison rejects it. The observed rejection
matches this implementation.

The installed executable was not patched or rebuilt. An experimental
data-only workaround is isolated to the replay artifacts:

```bash
python3 scripts/recover_nav_ephemeris.py runs/nav_audit_9dvjj0co \
  --output runs/nav_audit_9dvjj0co/recovered_ephemeris.xml
```

This uses the received NAV bits and field definitions already on the machine.
It first cross-validates 37 decoded fields against each of the three native
ephemerides, then adds PRN21 while preserving IODC=983 and IODE=215. The XML
provenance is saved beside it. It is assistance data for this recording, not
for future live use. No approximate receiver position was supplied.

## Four observations still do not give a native receiver fix

| Diagnostic replay | Result |
| --- | --- |
| `runs/rx1h_recovered_eph_9x5ti6tk/` | Receiver accepted all four XML ephemerides; no fix |
| `runs/rx1h_four_prn_axlbe7v2/` | Restrict acquisition to the four decoded PRNs; four simultaneous valid observations for 36.7 s; no fix |
| `runs/rx1h_pvt_lowmask_cs0kpzfz/` | Diagnostic 3-degree elevation mask; four observations for 48.7 s; no fix |
| `runs/rx1h_pvt_trace_euacgtrs/` | Logging-only follow-up; no fix or additional console solver detail |

The focused replay's `observables.dat` contains the four pseudoranges and
timestamps. Its internal log reports repeated RTKLIB point-position errors.

An independent four-satellite least-squares consistency check, including
broadcast satellite clock/relativity and Earth rotation, produced positions
near 41.8807 N, 87.6439 W, close to the existing project's reference location.
That location was not used as a prior. Details are in
`runs/rx1h_four_prn_axlbe7v2/independent_position_check.json`.

This is not a GNSS-SDR PVT fix or an accuracy validation. Four measurements
provide no redundancy; atmospheric corrections were omitted, and sampled
positions vary by tens of metres or more.

The geometric check places PRN5 at only 4.27–4.51 degrees elevation. The
replay's default 15-degree PVT mask excludes it. Lowering the mask to 3 degrees
did not fully resolve PVT, so the mask is not the sole blocker. The remaining
native solver rejection is unresolved. Negative coarse pseudoranges also
appear in the observables; they can reflect the receiver's arbitrary clock
origin and are not, alone, evidence of an external-clock fault.

## Next work within the current restrictions

Retain this recording as a regression input. Investigate observable-to-RTKLIB
conversion and solver initialization using these saved four-observation
epochs. Do not treat additional RF captures, gain sweeps or reference-clock
changes as necessary before this software rejection is understood.
