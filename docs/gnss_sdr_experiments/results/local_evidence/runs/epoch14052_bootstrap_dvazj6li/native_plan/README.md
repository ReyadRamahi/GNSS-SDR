# Native confirmation plan — prepared, not executed

> GitHub publication: links below use the repository archive layout. Small text evidence is included; IQ recordings, full observables, source/build copies, binaries and large per-epoch outputs remain on hft02. A clone alone cannot reproduce the experiment without those preserved local inputs.

No full receiver was built or replayed in this task. No files were uploaded,
packages installed, or external CI jobs started. Obtain approval **before**
external transfer, provisioning dependencies or executing on another machine.
The local solver translation units compiled, but the boundary wrapper/full link
remain unverified. The source is local GNSS-SDR 0.0.16; correspondence to every
Debian 0.0.16-1 packaging change is unproven.

## Build inputs and exact current blockers

Use an already provisioned x86-64 Ubuntu 22.04 environment compatible with the
local source and GNU Radio 3.10.1.1, GCC 11.4/C++17, CMake, Boost 1.74, glog/gflags,
BLAS/LAPACK, Armadillo, GnuTLS, MATIO, VOLK, Python3/Mako, plus the bundled
VOLK-GNSSSDR sources and required local cpufeatures source. Record actual versions
and source hashes; this list does not imply a full build has passed.

The specific missing development artifacts on hft02 are:

- PugiXML 1.12.1 `pugixml.hpp` **and** `pugiconfig.hpp`, matching the existing
  `libpugixml.so.1.12` runtime. An explicit CMake library path can avoid the absent
  unversioned `libpugixml.so` development link.
- The **complete** matching Protocol Buffers 3.12.4 C++ headers, including
  `google/protobuf/message.h` and `google/protobuf/stubs/common.h` and their
  transitive dependencies; the corresponding `protoc` 3.12.4 compiler; and
  `libprotoc.so.23` if that compiler dynamically requires it. The existing
  `libprotobuf.so.23.0.4` runtime alone is insufficient. The unversioned
  `libprotobuf.so` development link is also absent; an explicit library path is
  possible. Generated code must match the provided header/compiler version.

See the prior [host preflight](../../native_14052_dependency_check_n17mm09y/build_status.json)
and [native build report](../../../../../RX1H_NATIVE_CONFIRMATION.md).
No request to install these on hft02 is part of this plan. Additional blockers
could emerge after these confirmed prerequisites are supplied elsewhere.

## Sources, patches and order

Work in fresh copies of the full local
guarded source tree (hft02 local artifact: `runs/native_pvt_confirmation_recheck/source`), never the
installed receiver or that original copy. It contains old 14064 logging; replace
only the copied solver file with
pristine rtklib_pntpos.cc (hft02 local artifact: `runs/epoch14052_bootstrap_dvazj6li/build2/pristine_rtklib/rtklib_pntpos.cc`) and the copied
wrapper with pristine rtklib_solver.cc (hft02 local artifact: `runs/epoch14052_bootstrap_dvazj6li/native_plan/reference_source/src/algorithms/PVT/libs/rtklib_solver.cc`).
This establishes the exact patch baselines and removes old unconditional logging.
Retain the existing CMake no-fetch guard, and run the build worker with network
disabled. Missing dependencies must fail configuration; they must not trigger a
fetch or installation. No `cmake --install` target is allowed.

Apply with `patch --batch -p1 -i ABSOLUTE_PATCH_PATH` from each source root:

1. **Baseline profile:** [error_copy_only.patch](error_copy_only.patch),
   [baseline_native_logging.patch](baseline_native_logging.patch),
   [boundary_logging.patch](boundary_logging.patch), in that order.
2. First run the native baseline and compare the actual 14052 trace to the
   reconstructed failure. **Do not apply the functional candidate merely because
   a receiver still reports no fix.** If native rejection is different, stop and
   diagnose the logged path.
3. Only after confirming the same initialization/mask failure, make a separate
   candidate source root from the same pristine files. Apply
   [error_copy_only.patch](error_copy_only.patch),
   [provisional_position_only.patch](provisional_position_only.patch),
   [candidate_native_logging.patch](candidate_native_logging.patch), and
   [boundary_logging.patch](boundary_logging.patch), in that order.

The error copy is a diagnostics correction, not the behavior change. New detailed
logging is restricted to observation GPS TOW 14052.000 within 1 microsecond.
Existing ordinary receiver logging is unaffected. Both profiles apply cleanly:
[patch_apply_checks.json](patch_apply_checks.json). Both diagnostic solver units
compile with installed dependencies: [baseline compile log](baseline_compile_check.log),
[candidate compile log](candidate_compile_check.log). This is **not** evidence
that the full receiver compiles.

Reuse the preserved [configure argument vector](../../native_pvt_confirmation_recheck/configure_command.json),
substituting only the new source/build directories and compatible existing
PugiXML/Protobuf prefix/include/library/compiler paths. Preserve all disabled
hardware adapters, simulator-install, test-fetch and dependency-rebuild options.
For example, after applying that vector with explicit paths:

```bash
cmake --build "$GNSS_NATIVE_BUILD" --target gnss-sdr --parallel 2
```

Save configuration/build stdout+stderr, commands, exits, source/patch hashes,
compiler/dependency versions and diagnostic binary hash. Do not replace
`/usr/bin/gnss-sdr`. The source CMake target places the receiver under the build
`src/main` directory; verify the actual executable and `--version` before replay.

## Approved-transfer inputs and replay

A proposed transfer manifest must include the full local source/bundled
subprojects, these patches, the saved 1.44 GB
90-second recording (hft02 local artifact: `runs/rx1h_baseline_20261108_035309_7qbMJ8/rx1h.cf32`),
[3-degree config](../../rx1h_pvt_lowmask_cs0kpzfz/config_used.conf), experimental
[ephemerides](../../nav_audit_9dvjj0co/recovered_ephemeris.xml),
[ionosphere](../../nav_audit_9dvjj0co/gps_iono.xml),
[UTC](../../nav_audit_9dvjj0co/gps_utc_model.xml), stock observables/logs and
[preservation hashes](../preservation.json). No transfer has been made.

If the approved destination uses different input paths, create a **new scratch
config**, changing only the four absolute IQ/XML filenames. Save a diff proving
only those paths changed. Keep Single mode, 3-degree mask, RF/IF/acquisition/
tracking settings and no supplied coordinates. The original config stays intact.
For the baseline and later candidate, use independent fresh working directories:

```bash
mkdir -p "$GNSS_NATIVE_RUN/internal"
cd "$GNSS_NATIVE_RUN"
/usr/bin/timeout --signal=INT --kill-after=10s 180s   "$GNSS_NATIVE_BINARY" --config_file="$GNSS_REPLAY_CONFIG"   --log_dir="$GNSS_NATIVE_RUN/internal" >replay.log 2>&1
GNSS_REPLAY_EXIT=$?
printf '%s\n' "$GNSS_REPLAY_EXIT" >exit_status.txt
```

Use absolute paths for the three variables, chosen fresh per run. Input hashes
must match before/after. Exit 0 alone is not position success. The 180 s bound
matches the previous stock command; a timeout is an incomplete replay, not a
solver diagnosis. No live source or antenna/reference settings are involved.

## Required observations and decisions

At exact 14052, the boundary records raw PRNs, RX/TX times, P, CN0, flags, raw
selected ephemeris identity/health. Solver input records the **actual** converted
observations, full converted orbit/clock parameters, computed satellite positions,
health/variance, starting receiver position, models and mask/GDOP options.
Each residual iteration logs state, all elevations and mask decisions, filtering
reasons, input n / surviving ns / equation nv / required NX, LSQ step norm,
failure message and final validation. This distinguishes:

- elevation rejection -> ns=3/nv=6 before LSQ;
- missing/invalid geometry, range/SNR, health/exclusion or atmosphere rejection;
- nonzero LSQ info;
- iteration exhaustion;
- final GDOP/chi-square rejection.

Native proof of the proposed cause requires the actual four input PRNs,
zero initial state, first update, PRN5 below 3 degrees, and ns=3/nv=6 at iteration
1. A different path overrides the reconstruction hypothesis. If acquisition
scheduling does not reproduce four inputs at 14052, report that mismatch rather
than relabeling another epoch as this one.

For a confirmed matching candidate, require the configured mask to reappear in
the trace before success and native final validation to pass. Inspect native
PVT outputs/status, satellite counts and continuity across all available later
epochs, not only a first solution. The saved raw observables may change after a
native fix because of receiver feedback; direct replay of fixed saved
observables does not test that loop. Retain ordinary native logs/NMEA/position
outputs and the new observables, and compare timing and positions to the
standalone result only as a consistency check. Four ranges lack redundant
residual validation; obtain surveyed coordinates before claiming accuracy.

The original 15-degree control should still report too few usable satellites;
keep it separate from the fixed-3-degree before/after comparison. All assisted
native tests remain dependent on the experimental PRN21 XML. No unassisted
cold-start or external-reference-lock claim is justified.
