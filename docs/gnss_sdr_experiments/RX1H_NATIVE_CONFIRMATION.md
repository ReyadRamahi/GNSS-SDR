# Native confirmation: blocked by unavailable local build dependencies

Follow-up: [the installed configuration-option audit](RX1H_CONFIGURATION_WORKAROUND_AUDIT.md)
establishes no supported PVT position-seeding option. It also distinguishes
the existing versioned PugiXML/Protobuf runtimes from the missing development
headers, compiler and automatic link-time discovery files. No build was retried.

No diagnostic receiver binary was built, and no new receiver replay was run.
The prior standalone solver reproduction remains a standalone result. Native
confirmation of its rejection, a coordinate-free initialization correction,
and subsequent-epoch native continuity are **not yet established**.

## Work performed

`scripts/prepare_native_pvt_diagnostic.py` created the separate source copy
`runs/native_pvt_confirmation_20261108_1/source/` from the existing local
GNSS-SDR 0.0.16 tree, excluding its old build and Git metadata. The installed
receiver package is 0.0.16-1; source equivalence to that binary remains unproven.

The copy has only the prepared PVT boundary logging and solver logging changes.
The error-message copying correction is retained as a separate, **unapplied**
patch. No initialization or measurement-validity behavior was changed.

Configuration disabled receiver hardware adapters, test suites, simulator
installation and optional dependency rebuilds. A separate CMake guard refuses
every dependency declaration that specifies Git, URL or other repository
fetching. The guard permits the existing bundled VOLK-GNSSSDR source to be
declared for a local build. No compilation/install target was invoked.

## Exact blocker and evidence

The new `configure.log` ends with:

```text
Could NOT find PUGIXML (missing: PUGIXML_LIBRARY PUGIXML_INCLUDE_DIR)
OFFLINE_DEPENDENCY_BLOCKER: pugixml-1.12 needs GIT_REPOSITORY; fetching is forbidden
```

The source build normally declares a dependency-fetch fallback here. The guard
failed configuration before that fallback could execute. No fetch was attempted.

Independent compiler preprocessing probes also failed:

```text
fatal error: pugixml.hpp: No such file or directory
fatal error: google/protobuf/message.h: No such file or directory
```

`protoc` is absent from PATH and the usual installed locations checked. The
previous tree's `build/thirdparty/pugixml/` and
`build/thirdparty/protobuf/` contain **zero regular files**. Their separate
prefix directories contain old CMake download recipes and stamp metadata,
not usable dependency source, headers, compiler or built libraries.
Only the Protocol Buffers runtime `libprotobuf.so.23` was found; that does not
supply the development headers or schema compiler required for this build.
No cached package or alternate usable dependency copy was found in the local
locations searched. `dependency_probes.json` records the exact probes/results.

GNU Radio, Boost, glog/gflags, BLAS/LAPACK, Armadillo, GnuTLS and MATIO were found
by the guarded configuration. VOLK-GNSSSDR is not installed separately, but its
source is bundled locally; it is not the demonstrated missing-source blocker.

## Consequences for the requested comparison

The planned before/after comparison must retain the existing 3-degree mask,
reapply that mask to the final solution, and initialize without known receiver
coordinates. The original 15-degree case must remain a separate comparison.
Neither comparison was performed in a native diagnostic build because the
required receiver could not be built from the available dependencies.

Consequently, this attempt supplies no new native TOW 14064.000 input snapshot,
ephemeris snapshot, initial position, solver options, rejection detail, residuals,
satellites-used history or fix-continuity record. Those remain the specific
missing native evidence; the earlier standalone results are not substituted.
The prepared logging is still available for a build when the necessary
development files are available locally under the stated restrictions.

There is **no new successful native replay**. The saved 3-degree and 15-degree
configurations both load the experimental `recovered_ephemeris.xml` containing
PRN21. Any future success using those unchanged inputs would still depend on
that workaround; this attempt does not establish unassisted native ephemeris
or position success. The earlier geometry evidence still indicates insufficient
usable satellites for the 15-degree four-PRN case, but was not newly confirmed
in the requested native build. External-reference lock remains unverified.

## Artifacts and reproduction

All new artifacts are under `runs/native_pvt_confirmation_20261108_1/`:

- `source/`: separate logging-only source copy.
- `patches/`: boundary logging, solver logging, the separate unapplied error-copy
  proposal, and the CMake dependency-fetch guard.
- `configure_command.json` and `configure.log`: exact native configuration attempt.
- `dependency_probes.json`: missing-header/tool and empty-cache evidence.
- `status.json`: configuration failed; receiver not built/executed; behavior unchanged.
- `input_hashes.json`: original IQ, observations, navigation, configurations,
  inspected original source and `/usr/bin/gnss-sdr` hash-identical before/after.

Reproduce the preparation, probes and guarded configuration from the project
root with an output directory that does not yet exist:

```bash
python3 scripts/prepare_native_pvt_diagnostic.py \
  --output runs/native_pvt_confirmation_recheck
```

Configuration is bounded to 120 seconds and each compiler probe to 15 seconds.
The script reports configuration status without invoking a receiver, download,
installation or hardware operation. No replay command is presented as runnable:
there is no native diagnostic executable from this attempt.
