# Installed receiver: no supported configuration-only PVT seed established

The installed `/usr/bin/gnss-sdr` reports **0.0.16**, and its package is
**0.0.16-1 amd64**. Existing local help, installed examples, and both local
0.0.16 source copies do not establish a supported configuration option that
loads a coarse receiver position into its initial PVT solve. No comparison
configuration was created, and no recording replay or build attempt was run
for this audit. The existing 3-degree mask and all receiver settings are intact.

## Candidate settings and their actual consumers

| Candidate | Evidence of support | What the available source consumes it for | PVT initialization conclusion |
| --- | --- | --- | --- |
| `GNSS-SDR.AGNSS_ref_location` | Literal is present in the installed executable; existing project examples use it; parsed by `control_thread.cc:181` | Computes satellite visibility, puts acquisition in standby, prioritizes satellites and starts acquisition (`control_thread.cc:893–917`) | No call supplies it to the PVT solver or `rtk.sol.rr`. Acquisition assistance does not establish a PVT position seed. |
| `GNSS-SDR.init_latitude_deg`, `GNSS-SDR.init_longitude_deg`, `GNSS-SDR.init_altitude_m` | Present in installed `front-end-cal.conf`; the file explicitly names `front-end-cal` as its executable | Read by the separate calibration utility, `src/utils/front-end-cal/main.cc:531–533` | Not receiver PVT configuration. These literals are absent from the installed `gnss-sdr` binary and no receiver-source consumer was found. |
| `PVT.positioning_mode` | Installed examples, executable literal and adapter consumer (`rtklib_pvt.cc:449`) agree | Selects Single, Static, Kinematic, PPP_Static or PPP_Kinematic | All modes enter the initial `pntpos()` call in `rtkpos()` before subsequent mode-specific processing. Changing mode does not supply initial coordinates. |
| `PVT.enable_rx_clock_correction`, `PVT.max_clock_offset_ms` | Documented/parsed in local PVT adapter; executable literals present | Applied after a successful internal `get_PVT()` (`rtklib_pvt_gs.cc:2113`, then 2156 onward) | They cannot correct the first failed point-position initialization. |
| `PVT.dynamics_model` | Parsed at `rtklib_pvt.cc:524`; executable literal present | Enables motion-model processing | Does not seed the point solver. In this source, enabling dynamics can bypass the immediate return after `pntpos()` fails; Single mode can then return 1 with no newly valid point solution. That is not evidence of a genuine position fix and is not used as a workaround. |

The command-interface hot/warm-start coordinates also feed visibility and
acquisition ordering (`control_thread.cc:946–972`), not solver initialization.
No command-server operation was invoked.

## Where PVT actually gets its initial position

The local `Rtklib_Pvt` adapter constructs its RTKLIB processing options at
`rtklib_pvt.cc:750`. It sets position-source fields to constants and initializes
the `ru`/`rb` arrays to zeros, rather than reading receiver-coordinate properties.
These RTKLIB structure members are **not exposed configuration keys** here.
`rtkinit()` (`rtklib_rtkpos.cc:2651`) assigns a zero-initialized `sol_t` to
`rtk->sol`. `estpos()` (`rtklib_pntpos.cc:630`) copies `sol->rr[0..2]` into its
initial position estimate. The PVT wrapper's `set_rx_pos()` call occurs after
a solver return indicating success (`rtklib_solver.cc:952`); it is not a
configuration-based cold-start input.

Searching the adapter property bindings found no initial-coordinate binding;
the extracted suffix list is saved with this audit. Aliases such as
`GPS_L1_CA_PVT` are routed to the same `Rtklib_Pvt` adapter by
`gnss_block_factory.cc:1289`, so they do not establish an alternate initializer.

## What is verified about the installed version

`gnss-sdr --version` and `gnss-sdr --help` were executed with no receiver
configuration. They exit at flag handling; no receiver flowgraph was started.
Help lists no position-seeding command-line flag. The installed man page also
lists no such option. The help-only exit status is 1, with normal help text and
no receiver initialization; version exits 0.

Installed examples were inspected separately from source examples. Selected
executable string matches corroborate that the existing AGNSS, mode, mask,
dynamics and clock-correction settings are compiled into this binary. String
presence alone does not prove a runtime consumer or the consumer's purpose.
The consumer paths above come from local 0.0.16 source, whose exact equivalence
to the Debian executable remains unproven. No guessed setting is promoted to
installed-version support based only on a source symbol or an accepted config
file: unknown config properties may simply be ignored.

The conclusion is therefore **no supported workaround could be established**,
not a claim to have exhaustively reverse-engineered every binary code path.
The conditional replay is not performed. There is no new native PVT result,
no supplied-coordinate replay and no new independent position calculation.
The existing proposed replay inputs still contain the experimental PRN21 XML;
this audit does not remove that dependency or demonstrate autonomous cold start.

## Exact missing development files for the diagnostic build

The runtimes are already present. More precisely than the earlier generic
"missing library" wording, CMake lacks the **development headers and link-time
discovery files**, not all runtime libraries. A compatible set matching this
machine is:

| Component | Existing runtime | Required local development files |
| --- | --- | --- |
| PugiXML **1.12.1** (`libpugixml1v5 1.12.1-1 amd64`) | `/usr/lib/x86_64-linux-gnu/libpugixml.so.1.12`, with `.so.1` symlink | `include/pugixml.hpp` and `include/pugiconfig.hpp` from the matching 1.12.1 development distribution. For automatic library discovery, an unversioned `libpugixml.so` link to the existing runtime, or a matching `libpugixml.a`; explicit CMake library-path selection can instead use the existing versioned shared library without adding a link. |
| Protocol Buffers **3.12.4** (`libprotobuf23 3.12.4-1ubuntu7.22.04.6 amd64`) | `/usr/lib/x86_64-linux-gnu/libprotobuf.so.23.0.4`, with `.so.23` symlink | Complete matching `include/google/protobuf/` headers, including `message.h`, `stubs/common.h`, generated-code support headers, and their included files; matching `bin/protoc`; standard `.proto` includes from that distribution. For automatic library discovery, an unversioned `libprotobuf.so` link to the existing runtime or a matching static library; explicit CMake library-path selection can use the versioned runtime. |
| Protocol Buffers compiler support | `libprotoc.so.23` is absent | If the supplied matching `protoc` is dynamically linked to it, provide its matching `libprotoc.so.23` runtime and resolved target from the same 3.12.4 build. A self-contained compiler would not require that separate library. |

The headers must be complete matching sets, not isolated copied header files.
Compiler-generated C++ and runtime headers/libraries must agree in version and
ABI. Compiled tools/libraries must be compatible with this amd64 Ubuntu system.
The equivalent development distributions are `libpugixml-dev` 1.12.1-1 and
`libprotobuf-dev` / `protobuf-compiler` / compiler runtime of the matching
3.12.4 Ubuntu build. These names identify compatibility; no package operation
was performed or requested.

The local GNSS-SDR source requires Protobuf >=3.0.0, so a complete 3.12.4 set
is sufficient for its declared version check. Its automatic fallback naming
PugiXML 1.12 / Protobuf 3.19.4 does not make those fallback versions mandatory.
Do not mix 3.19.4 headers or generated C++ with the existing 3.12.4 runtime.

Alternatively, complete existing local source distributions of these
dependencies could support a separate local build, but the cached directories
previously checked are empty. Further build/compile issues remain untested;
the table identifies confirmed missing development inputs, not a guarantee
that the rest of a full build will succeed. No build was retried.

## Audit artifacts

`runs/pvt_configuration_support_audit_20261108/` contains installed help and
version output, selected binary-string matches, the extracted local adapter
property suffixes, package/runtime details and inspected-file hashes. The
installed binary and inspected original source remain hash-identical. Saved
IQ, observation and navigation inputs were not edited.
