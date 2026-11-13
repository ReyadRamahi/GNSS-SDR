# TOW 14052.000: reconstructed initialization failure and candidate

> GitHub publication: links below use the repository archive layout. Small text evidence is included; IQ recordings, full observables, source/build copies, binaries and large per-epoch outputs remain on hft02. A clone alone cannot reproduce the experiment without those preserved local inputs.

2026-11-13 UTC. **Standalone reconstruction, not native GNSS-SDR success.**
All new evidence is in [the scratch directory](results/local_evidence/runs/epoch14052_bootstrap_dvazj6li).
The installed receiver, packages, configurations, RF hardware and saved inputs
were not changed. No download, installation, native receiver build, new RF capture,
commit or push was performed.

## Exact epoch and provenance

The source is the **latest stock replay's** observables.dat (hft02 local artifact: `runs/stock_rx1h_90s_3deg_20261113T033819Z_eg_8pwsd/observables.dat`),
not the earlier 14064 reconstruction. Record index **2050**, byte offset **459200**,
is the first record with all four pseudorange-valid flags. Its 224 bytes were
copied to epoch14052.bin (hft02 local artifact: `runs/epoch14052_bootstrap_dvazj6li/epoch14052.bin`);
[epoch14052.json](results/local_evidence/runs/epoch14052_bootstrap_dvazj6li/epoch14052.json) retains every
saved field. Every channel has RX TOW exactly **14052.000**, finite fields and
valid-pseudorange flag **1**. Channel order is 5, 12, 21, 22.

| PRN | Saved transmit/interpolated tag (s) | Pseudorange (m) | Valid flag |
|---|---:|---:|---:|
| 5 | 14051.996768176508 | 968876.308168820 | 1 |
| 12 | 14052.011901261272 | -3567908.370005769 | 1 |
| 21 | 14052.006086997626 | -1824835.980243431 | 1 |
| 22 | 14052.001575158074 | -472220.510892355 | 1 |

These signed ranges are preserved. The available native `prange()` rejects zero,
not every negative value; the reconstruction does not replace them with nominal
positive ranges or substitute Doppler/phase from another epoch.

The harness uses the [experimental assistance XML](results/local_evidence/runs/nav_audit_9dvjj0co/recovered_ephemeris.xml),
[broadcast ionosphere XML](results/local_evidence/runs/nav_audit_9dvjj0co/gps_iono.xml), and options from
the [documented 3° replay configuration](results/local_evidence/runs/rx1h_pvt_lowmask_cs0kpzfz/config_used.conf).
The XML is the assistance actually requested at replay startup. Ephemerides are
not measurements at precisely 14052: their applicability is checked by the
native ephemeris selector. All four have WN 396 (adjusted to full week 2444 by
the local conversion), Toe/Toc 14400, age **-348 s**, health 0 and accuracy 0.
The native selector accepts them; satellite positions and clocks are computed
successfully. Their saved NAV `tow=14088` is later than the target epoch: this is
explicitly a **preloaded, experimentally recovered assistance** experiment, not
proof of unassisted availability at 14052.

| PRN | XML IODE2 / IODE3 | XML IODC | Converted RTK IODE / IODC / health |
|---|---|---:|---|
| 5 | 49 / 49 | 49 | 0 / 0 / 0 |
| 12 | 48 / 48 | 48 | 0 / 0 / 0 |
| 21 | 215 / 215 | 983 | 0 / 0 / 0 |
| 22 | 23 / 23 | 23 | 0 / 0 / 0 |

The zero converted issue fields follow the available GPS conversion, which does
not copy those XML fields. There is one converted entry per PRN, so selection is
unambiguous in this reconstruction. The XML audit finds **only PRN21 was added**;
every existing field for PRNs 5/12/22 is textually unchanged. All numerical
ephemeris fields in the stock run's final XML equal the experimental assistance.
See [navigation_input_audit.json](results/local_evidence/runs/epoch14052_bootstrap_dvazj6li/navigation_input_audit.json).
**Every successful candidate test below still depends on that experimental PRN21 XML.**

### What is missing for an exact native reconstruction

The stock log records a PRN5 ephemeris update immediately before the failure but
does not serialize its full selected state. Equality of the end-of-run XML to
assistance does not prove equality at that earlier instant. Per-channel CN0 and
additional tracking/NAV flags are also absent from the observables dump; the
harness leaves them at default values and the configured SNR mask is disabled.
It copies all saved range-valid flags and requires the four healthy ephemerides.
It does **not** establish the actual native boundary membership, native initial
state or post-filter membership. Source equivalence of the local 0.0.16 tree to
the packaged 0.0.16-1 executable is not established. These omissions prevent
claiming that the reconstructed branch was the stock receiver's actual branch.

## Reconstruction method and first failure

[epoch_window_harness.cc](../../scripts/epoch_window_harness.cc) calls the available
`insert_obs_to_rtklib()`, `eph_to_rtklib()` and `pntpos()` implementations. It
parses the ionosphere XML dynamically, uses GPS-only Single positioning,
Broadcast ionosphere, Saastamoinen troposphere, disabled SNR masks, GDOP limit
30, the adapter's default measurement weighting, and elevation mask **3°**.
The UTC model does not enter this GPS-only position calculation. No coordinates
are supplied. Initial ECEF is **(0,0,0)** and all seven initial least-squares
states, including the receiver clock in metres, are zero.

[prepare_epoch14052_harness.py](../../scripts/prepare_epoch14052_harness.py) copies
existing local units into scratch. Removing the four prior logging statements
recovers the recorded original `rtklib_pntpos.cc` hash
`b719ab021cc42226f11c825877200e65dd9df53d51057f65e02beb960375f922`.
The [successful build commands](results/local_evidence/runs/epoch14052_bootstrap_dvazj6li/build2/build_commands.json)
and [build log](results/local_evidence/runs/epoch14052_bootstrap_dvazj6li/build2/build.log) are retained.
The initial build attempt missed the local umbrella header in its copy glob;
that helper error was corrected before any solver test. The successful build
is **build2**, not the incomplete scratch-root build.

The original order is: initialize from `sol.rr`; compute geometry/elevation;
apply elevation mask; range correction; health/exclusion; atmosphere; residual;
append constellation-bias constraints; require `nv >= NX`; least squares;
update; convergence; `valsol()`. There is **no provision to delay the elevation
test while the initial position is still converging**. The reconstruction keeps
that order for its baseline. See the pristine local solver (hft02 local artifact: `runs/epoch14052_bootstrap_dvazj6li/build2/pristine_rtklib/rtklib_pntpos.cc`).

At iteration 0, the source's Earth-centre geometry convention returns 90° for
all four satellites. They pass, producing **ns=4, nv=7, NX=7**. The first
least-squares update succeeds, giving ECEF
**(130403.663207366, -5149593.485988078, 4785157.666000954) m**, clock
**-23655438.984529730 m**. This intermediate position yields:

| PRN | Iteration 1 elevation | Passes 3°? | Included in residual equations? |
|---|---:|---|---|
| 5 | 1.721378797° | No | No |
| 12 | 58.103683246° | Yes | Yes |
| 21 | 27.176934912° | Yes | Yes |
| 22 | 14.259101015° | Yes | Yes |

The **first failure is `nv=6 < NX=7` at iteration 1**, before another least-squares
call: three GPS observations plus three absent-constellation clock constraints.
The original message calls this `lack of valid sats ns=6`, but the printed 6 is
the **equation count**, not six satellites. See [baseline trace](results/local_evidence/runs/epoch14052_bootstrap_dvazj6li/baseline_first.log)
and [baseline result](results/local_evidence/runs/epoch14052_bootstrap_dvazj6li/baseline_first.jsonl).
The existing earlier harness, when given this newly extracted 14052 record,
independently gives the same geometry/count failure and an empty caller reason:
[existing-harness trace](results/local_evidence/runs/epoch14052_bootstrap_dvazj6li/baseline_existing_harness.log).
No 14064 observations or supplied-position result is used for this conclusion.

The empty reason is a separate source defect: `estpos()` writes its local
`msg_aux`, then executes `msg = msg_aux`, changing only a local pointer. The
baseline and candidate share the [bounded error-copy-only patch](results/local_evidence/runs/epoch14052_bootstrap_dvazj6li/build2/error_copy_only.patch):
`snprintf(msg, 128, "%s", msg_aux)` on the common failure exit. The native
caller allocates 128 bytes. This patch exposes insufficient equations, LSQ error
or divergence without changing solver decisions; direct `valsol()` error text is
left intact. An empty native reason alone still cannot distinguish these paths.

## One behavior change and its result

The [functional patch](results/local_evidence/runs/epoch14052_bootstrap_dvazj6li/build2/provisional_position_only.patch)
defers only elevation rejection when initial ECEF norm is zero. It iterates to
the existing `norm(dx) < 1e-4` convergence criterion using an observation-derived
provisional position, then **recomputes residuals with the original mask** and
requires another converged solve plus unchanged `valsol()` checks. It retains
health/exclusion, range/atmosphere models, weighting, `NX=7`, GDOP validation and
the shared original 10-iteration budget. A provisional result alone is never
returned as success; a nonzero previous solution retains normal masking.

At 14052, iterations **0–6** are provisional, with **ns=4, nv=7** throughout;
iteration **7** uses the configured **3°** mask, still **ns=4, nv=7**, converges
and passes native-library `valsol()`. No LSQ error or divergence occurs.

| PRN | Final configured-mask elevation | Passes 3°? |
|---|---:|---|
| 5 | 4.184817452° | Yes |
| 12 | 57.826873826° | Yes |
| 21 | 30.054682690° | Yes |
| 22 | 17.235804852° | Yes |

The standalone `pntpos()` return is **1**, status **5 / SOLQ_SINGLE**, four used
satellites, GDOP **7.09429**. Position is 41.8806790404°, -87.6437795635°,
ellipsoidal height 249.7504 m. See [candidate first-epoch trace](results/local_evidence/runs/epoch14052_bootstrap_dvazj6li/candidate_first.log)
and [result](results/local_evidence/runs/epoch14052_bootstrap_dvazj6li/candidate_first.jsonl).
This is a **library result**, not a native GNSS-SDR receiver fix.

## Subsequent epochs and limitations

All 2,435 four-valid epochs from **14052.000 through 14100.680**, at 20 ms
spacing with no gaps, were tested. `cold` resets the state at every epoch;
`sequential` carries the successful position forward. Other settings are fixed.

| Reconstruction | Successful calls | Satellites | Final mask |
|---|---:|---|---|
| Baseline, cold | 0 / 2435 | 3 at failure | 3° |
| Baseline, sequential | 0 / 2435 | 3 at failure | 3° |
| Candidate, cold | 2435 / 2435 | 4 each | 3°, passed each time |
| Candidate, sequential | 2435 / 2435 | 4 each | 3°, passed each time |
| Candidate, first epoch, original 15° control | 0 / 1 | 3 after reapplying mask | 15° |

The 15° control reaches the provisional position but then rejects PRN5 at
4.18482°, giving ns=3/nv=6 and **no final fix**. It demonstrates that provisional
convergence does not bypass final masking. See [15° result](results/local_evidence/runs/epoch14052_bootstrap_dvazj6li/candidate_first_15deg.jsonl).
All harness **process exits are 0**, including failed position calls; solver
`result` and `status` in JSON, not process exit, determine success.

In sequential candidate results, GDOP is **7.03115–7.09429**, the minimum used
elevation is **4.18482°**, maximum absolute saved residual is **5.15e-5 m** and
maximum residual RMS is **2.71e-5 m**. These nearly zero residuals are expected
with four ranges/four effective unknowns: `nv==NX`, so the unchanged chi-square
test has **no redundant degrees of freedom** and its `nv>nx` branch is inactive.
GDOP validation remains active. These residuals do not demonstrate good accuracy.

Position scatter is substantial: **55.52 m 3D RMS** about the mean; local E/N/U
standard deviations **22.39 / 33.42 / 38.27 m**; maximum consecutive 20 ms
position step **16.83 m**; height range **144.55–360.87 m**. The historical
approximate latitude/longitude in [limesdr_focused.conf](../../configs/limesdr_focused.conf)
has no surveyed accuracy or reference height. Relative to it, the first solution
is **12.55 m** horizontally away, and the sequence spans **1.05–109.05 m**
horizontal differences (RMS 40.41 m). This is **consistency only**, not measured
absolute accuracy. No independent position solve was repeated or used as a seed.

These results support a coordinate-free **initialization candidate** for this
assisted four-GPS dataset, not durable RF lock, unassisted cold start, broad
receiver robustness or native continuous fixes. Native receiver clock feedback,
acquisition scheduling, ephemeris changes and output behavior are not simulated
by passing saved observables directly to `pntpos()`.

[window_summary.json](results/local_evidence/runs/epoch14052_bootstrap_dvazj6li/window_summary.json)
contains metrics; [window_commands.json](results/local_evidence/runs/epoch14052_bootstrap_dvazj6li/window_commands.json)
contains exact argument vectors, exits and elapsed times; the scratch directory
contains per-epoch JSONL files and first-epoch-only detailed traces.

## Reproduction and next native test

From the project root, create a fresh standalone output directory:

```bash
GNSS_EPOCH_OUT=$(mktemp -d "$PWD/runs/epoch14052_recheck_XXXXXX")
python3 scripts/prepare_epoch14052_harness.py --output "$GNSS_EPOCH_OUT"
"$GNSS_EPOCH_OUT/baseline_epoch_window" \
  runs/stock_rx1h_90s_3deg_20261113T033819Z_eg_8pwsd/observables.dat \
  runs/nav_audit_9dvjj0co/recovered_ephemeris.xml \
  runs/nav_audit_9dvjj0co/gps_iono.xml \
  "$GNSS_EPOCH_OUT/baseline.jsonl" first 3 >"$GNSS_EPOCH_OUT/baseline.log" 2>&1
"$GNSS_EPOCH_OUT/candidate_epoch_window" \
  runs/stock_rx1h_90s_3deg_20261113T033819Z_eg_8pwsd/observables.dat \
  runs/nav_audit_9dvjj0co/recovered_ephemeris.xml \
  runs/nav_audit_9dvjj0co/gps_iono.xml \
  "$GNSS_EPOCH_OUT/candidate.jsonl" sequential 3 >"$GNSS_EPOCH_OUT/candidate.log" 2>&1
```

The [native build/replay plan](results/local_evidence/runs/epoch14052_bootstrap_dvazj6li/native_plan/README.md)
provides separate error-copy, targeted diagnostics and functional patches. Both
patch profiles apply cleanly, and both diagnostic solver translation units
compile locally. The full receiver and boundary wrapper are **not built or run**.
PugiXML/Protobuf development prerequisites remain missing; no native build was
retried. Only a native trace can confirm the stock failure path. Uploads,
dependency installation or external execution require approval before proceeding.

[preservation.json](results/local_evidence/runs/epoch14052_bootstrap_dvazj6li/preservation.json)
confirms unchanged stock binary, observables, navigation inputs and configs, and
the saved 1.44 GB IQ hash still matches the prior stock replay manifest.
