# First four-observation epoch: elevation filtering prevents the position solve

Native follow-up: [the isolated receiver build attempt](RX1H_NATIVE_CONFIRMATION.md)
is blocked by missing local PugiXML and Protocol Buffers development files.
No native diagnostic replay or initialization correction has been performed.

The earliest saved four-valid-observation epoch is GPS TOW **14064.000 s**.
The local GNSS-SDR 0.0.16 point-position code reproduces a failure at
`rescode()` / `estpos()`: after the first least-squares update, elevation
filtering leaves too few measurements. Satellite propagation and the first
least-squares step succeed. This is concrete evidence for investigating the
PVT initialization and elevation selection before changing RF or clocks.

The installed receiver's original log confirms a native failure at exactly
this epoch, but contains an empty reason. The detailed values below come from
an **isolated reconstruction using local source**, not newly instrumented
execution inside the installed receiver. The local source has not been proven
byte-for-byte equivalent to the installed Debian `gnss-sdr 0.0.16-1` binary.

All new outputs are in `runs/first_epoch_pvt_20261108_4/`. No RF capture,
network access, installation, installed-software edit or hardware operation
was performed. Original recording, observations, navigation and configuration
files have matching before/after SHA-256 hashes in `input_hashes.json`.
External-reference lock remains unverified; this software rejection supplies
no evidence that the clock is its cause.

## The exact saved inputs

Input: `runs/rx1h_four_prn_axlbe7v2/observables.dat`, from the existing 90-second
recording. Zero-based epoch index **2650**, byte offset **593600**, record size
224 bytes. Each channel has seven little-endian doubles; the layout is verified
against `hybrid_observables_gs.cc:835`. The complete values and extraction
location are in `epoch.json` and the exact 224 input bytes in `epoch.bin`.

All four channels report RX time **14064.000000000 s** and
`Flag_valid_pseudorange=1`:

| Channel | PRN | Interpolated transmit tag, s | Pseudorange, m | Ephemeris IODC / IODE2 / IODE3 | Health |
| --- | --- | --- | --- | --- | --- |
| 0 | 5 | 14063.996798425400 | 959807.918615606 | 49 / 49 / 49 | 0 |
| 1 | 12 | 14064.011909037403 | -3570239.595129443 | 48 / 48 / 48 | 0 |
| 2 | 21 | 14064.006113308871 | -1832723.892999736 | 983 / 215 / 215 | 0 |
| 3 | 22 | 14064.001548798635 | -464318.149914169 | 23 / 23 / 23 | 0 |

The dump does **not** save CN0 or the acquisition, tracking-symbol, NAV-word and
PLL-180-degree flags. Their exact values at the PVT boundary cannot be recovered
from these seven doubles. Source inspection shows that `compute_pranges()`
sets valid pseudorange only when its NAV-word flag is true; this is an inference
from code, not an independently recorded flag. Tracking lock and decoded NAV
are upstream prerequisites, not proof of a usable PVT measurement.

## Through the native PVT path

The local source establishes this sequence:

1. `rtklib_pvt_gs.cc:1994` accepts a GPS L1 C/A observation if the pseudorange
   flag is true, a matching-PRN ephemeris exists, signal is `1C`, and ephemeris
   health is zero. It inserts the observation without changing its range or
   timestamp. The internal solver runs before receiver-clock correction.
2. The original internal log, lines 176–181, records loading all four assistance
   ephemerides before tracking. They have WN=396 and Toe=14400. Before the first
   solver error, PRN5 also receives native ephemeris updates with the same week
   and Toe; the other three still have their assistance entries. The log does
   not snapshot every field of those PRN5 updates. The final replay map has
   numerically identical fields to the assistance map for all four PRNs.
3. `rtklib_solver.cc:530` converts each matching GPS observation and ephemeris;
   with four entries it calls `rtkpos()`. `insert_obs_to_rtklib()` preserves
   signed pseudoranges, uses RX time for observation time, and tags GPS L1 C/A.
   Thus there is no positive-pseudorange check rejecting the three negative
   values. They all enter residual formation in the isolated reconstruction.
4. `rtkpos()` calls `pntpos()`, which propagates satellites and calls `estpos()`.
   `rescode()` applies elevation, code availability, health/system exclusion,
   atmospheric-correction and measurement-variance checks. Four input entries
   do not guarantee four entries survive this stage.

The GPS ephemeris converter in this source copies the orbit, clock, TGD and
times, but leaves RTKLIB `iode`, `iodc`, `svh` and `sva` at their zero defaults.
The upstream PVT gate checks XML health. The reconstruction logs both original
XML identifiers and these converted values so they are not mistaken for one
another. All XML health values here are zero, so this omission is not the
demonstrated failure.

## Time, ephemeris selection and satellite positions

All observations have the same RX timestamp. Raw WN=396 expands to GPS week
**2444** using the local `adjgpsweek()` logic and current host date. All four
ephemerides have Toe=Toc=14400 s, making RX time minus Toe **-336 s**. Native
GPS ephemeris selection allows an absolute difference up to **7201 s** and
finds one matching candidate per satellite. A future Toe is not automatically
an expired or inapplicable ephemeris.

The experimental assistance contains message `tow=14088`, 24 seconds after
this epoch. It was decoded later in this same recording and loaded in advance
for the experiment. This is retrospective assistance, not a demonstration of
real-time ephemeris availability. It causes no week-boundary adjustment here.
The workaround is still needed for PRN21 because native NAV validation rejects
its full IODC=983 against 8-bit IODE=215, despite `983 & 255 == 215`.

`time_checks.json` verifies that each saved range matches
`c * (RX_time - interpolated_transmit_tag)` to floating-point precision.
The signed apparent travel times reflect the coarse receiver clock origin.
RTKLIB uses `RX_time - P/c`, then satellite-clock correction, to propagate each
satellite. Its trace reports these finite, nonzero ECEF positions:

| PRN | Satellite X, m | Y, m | Z, m | Clock correction, ns | Health returned |
| --- | --- | --- | --- | --- | --- |
| 5 | -6091227.788 | -22656402.806 | -12600550.608 | -237776.496 | 0 |
| 12 | -9815942.413 | -15929079.032 | 18539776.775 | -597531.069 | 0 |
| 21 | 2462161.022 | -26276974.257 | -2744718.553 | 315601.204 | 0 |
| 22 | 10480958.336 | -23595706.204 | -6609881.147 | 121876.632 | 0 |

No missing-ephemeris, zero-position, health, code-availability, SNR-mask or
ionosphere/troposphere failure precedes the demonstrated rejection. SNR masks
are disabled by the saved PVT adapter configuration; the missing CN0 snapshot
does not affect this reconstruction's rejection. The native trace records
satellite variance 5.760 m² for all four.

## The earliest failed check and why the 3-degree replay also fails

Native `rtkinit()` initializes the receiver position to ECEF (0,0,0). At
iteration 0, the source handles that origin with nominal 90-degree elevations;
all four ranges pass. It builds seven equations: four measurements plus three
constraints for unused constellation clock offsets. The seven-unknown
least-squares step succeeds.

Iteration 1 starts at ECEF
**(130766.199849495, -5151117.821045178, 4786432.041062787) m**,
clock bias **-23654352.592151921 m**. This is an intermediate position.

| PRN | Elevation at iteration 1 | Saved 15° mask | Existing diagnostic 3° mask |
| --- | --- | --- | --- |
| 5 | 1.797421352° | Reject | Reject |
| 12 | 58.147161664° | Keep | Keep |
| 21 | 27.267272705° | Keep | Keep |
| 22 | 14.171253275° | Reject | Keep |

The **first failed check** is `elaux < opt->elmin` for PRN5 in
`rtklib_pntpos.cc:460`. In the 15° case PRN22 subsequently fails that check too.
The resulting **solver failure** is `nv < NX` in `estpos()`:

- 15°: `ns=2`, `nv=5`, `NX=7`; return 0.
- Existing 3°: `ns=3`, `nv=6`, `NX=7`; return 0.

The original error string misleadingly prints `nv` under the name `ns`, so
`lack of valid sats ns=5` means five equations, not five satellites.
Neither an LSQ matrix error nor the final chi-square/GDOP validation is reached
at iteration 1. The saved native log's first failure is line 581:
`03:54:24.00: point pos error ()`, exactly TOW 14064.000.

A third call of this **same epoch**, with the existing 3° mask unchanged,
initializes only the receiver position from the previously saved independent
estimate. The unchanged local point-position solver then converges after four
iterations, returns 1 / `SOLQ_SINGLE=5`, and uses all four satellites. Its
reported LLH is 41.880810573 N, -87.644068692 E, 256.807 m, clock bias
-81.656300 ms. This seeded calculation is an initialization diagnostic. It is
**neither an independent position validation nor a native GNSS-SDR PVT fix**.

This establishes two separate limitations: the normal 15° configuration has
insufficient above-mask geometry even near the independent solution (PRN5 is
about 4.27°); the 3° experiment additionally fails because the unrefined first
position update places PRN5 below its mask. No lower mask was tested.

## Existing diagnostics and the smallest justified corrections

`PVT.rtk_trace_level=4` did not expose these details because this local
RTKLIB `trace()` routes through glog `VLOG(level)`; its effective switch is
glog verbosity, such as `--vmodule=rtklib_rtkcmn=4`. The isolated harness enables
that verbosity and adds four logging statements in a copied `rtklib_pntpos.cc`.
`logging_only.patch` records every source change used for the experiment.

The empty caller error has a concrete source defect: `estpos()` assigns
`msg = msg_aux`, changing its local pointer instead of copying the error to the
caller. `proposed_error_propagation.patch` copies the failure string into the
128-byte caller buffer and removes the ineffective assignment on the converged
path. This is the smallest justified diagnostic correction. It was **not**
applied to installed software or to the solver used in these runs.

For the functional 3° experiment, the evidence supports supplying a valid
coarse initial receiver position before applying position-dependent elevation
filtering. A general unaided implementation would obtain that coarse position
from the observations, then reapply the configured mask and final validation.
The aided single-epoch control demonstrates why this is worth implementing;
it does not validate an unaided initializer. Merely skipping a fixed number of
iterations or reducing the mask again is not a justified production fix.
Retaining a 15° mask still requires at least four usable above-mask satellites;
an initializer cannot make this four-satellite epoch meet that condition.

For direct confirmation inside a receiver built from the matching installed
source, `proposed_boundary_logging.patch` and its separate working-copy file
log only TOW 14064.000: accepted observations, all available flags/CN0, selected
ephemeris identifiers/times/health, and converted RTKLIB entries. This patch
is a proposal, not compiled receiver code. Together with glog solver trace it
would close the remaining gap between the saved observables plus local-source
reconstruction and the exact original receiver's in-memory inputs. A new file
replay may acquire at different times; it must not silently substitute another
epoch for the saved one.

## Experimental XML audit

`xml.diff` and `xml_audit.json` specify the exact addition, including every
PRN21 field and value. The only changes from native `gps_ephemeris.xml` are
map count **3 → 4** and one appended `<item>` keyed **21**, containing all
40 serialized ephemeris fields. Existing PRN5/12/22 item fields and attributes
are unchanged. Removing PRN21 and restoring the count makes the **entire XML
tree semantically identical**, including archive metadata. Text serialization
changes indentation around the added item, not unrelated data.

The added orbit, clock, issue identifiers and flags are decoded from the latest
received SF1/2/3 for PRN21. WN=396, Toe=Toc=14400, IODC=983 and both IODEs=215
are retained; IODC is not falsified to bypass the comparison. `tow=14088` is the
maximum of those messages' next-subframe HOW tags. `satClkDrift`, `dtr`, `spare1`
and `spare2` are explicit zero defaults, not separately decoded measurements.
Every template child is overwritten; no orbital value is inherited from PRN5.

Regenerating into the new diagnostic directory produces **byte-identical**
experimental XML. The decoder cross-checks 37 fields against each native
PRN5/12/22 entry. Ionosphere and UTC files also match between the audit and
focused replay, and all original files remain hash-identical. The final replay
ephemeris map differs only in PRN21 number formatting, with no numeric changes.

This checks reproducibility against local definitions, not independent ICD
conformance: the local `GPS_L1_CA.h` places FIT/AODO bit slices inside its Toe
slice. The workaround follows those same definitions as native decoding.
Those two metadata fields are not copied by this GPS-to-RTKLIB conversion and
do not cause the measured elevation rejection. They remain an explicit limit
of calling the experimental navigation data independently validated.

## Reproduce without RF

From `/home/rrama28/gnss`, choose an output directory that does not exist:

```bash
python3 scripts/diagnose_first_pvt_epoch.py \
  --output runs/first_epoch_pvt_recheck
```

The script extracts one fixed epoch, audits XML, builds only the diagnostic
executable using installed compiler/libraries and existing local solver source,
then makes three bounded calls of that epoch. Compilation is limited to 120 s;
each solver process to 15 s. Exact compiler and execution arguments are saved
in JSON. The successful diagnostic is `runs/first_epoch_pvt_20261108_4/`;
directories ending `_1` and `_2` contain compiler failures during diagnostic
development, and `_3` contains the earlier 15°-only reconstruction. None are RF
captures. `verification.json` confirms expected branch outcomes and preserved
inputs. Original full receiver replays still have **no native PVT fix**.
