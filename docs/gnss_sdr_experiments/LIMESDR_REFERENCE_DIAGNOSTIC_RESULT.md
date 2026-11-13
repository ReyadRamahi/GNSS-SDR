**One authorized diagnostic connection completed; raw indication is inconclusive.**

Measurement: 2026-11-08 18:46:13 CST (`2026-11-09T00:46:13Z`).
Target USB serial: `0009061C01502715`.

| Measurement after opening | Result |
| --- | --- |
| Device | LimeSDR-USB |
| Hardware / firmware / protocol | 4 / 4 / 1 |
| Gateware | **2.23**, target LimeSDR-USB |
| BBIC `0x0000` board ID | `0x000e` |
| BBIC `0x0001` gateware version | `0x0002` |
| BBIC `0x0002` gateware revision | `0x0017` = decimal 23 |
| BBIC `0x0003` hardware identity | `0x0004` |
| BBIC `0x00c8` raw peripheral input | **`0x0002`**, successful read |
| Raw bit 1 | **1** |
| External-reference lock conclusion | **Inconclusive: current ADF MUXOUT configuration is unknown.** |

These observations were taken **after the FX3 connection constructor**. There
was no measurement of the untouched state before opening, and no capture or
stream was started. This single sample does not establish sustained lock or
lock during receiver operation.

**Ownership and connection accounting**

Immediately before launch, a host-root guard scanned process descriptors by
the target character device's major/minor number, including alternate mount
paths. It found no holder, no metadata failures and no attached interface
driver. The completed scan preceded the helper launch in the same guarded
operation. The guard would have stopped on an owner or incomplete scan.

The helper made exactly one `ConnectionRegistry::makeConnection` call, with
FX3 and the exact serial as filters, and did not retry. Registry discovery
temporarily opens/closes descriptor handles internally before the single
claimed FX3 connection. The helper released that connection via
`freeConnection`; its close/completion records and return code were successful.
A subsequent host-root ownership scan again found no holder or scan errors.
No running server was stopped or restarted.

**Initialization effects and limits of the trace**

The pinned installed library was
`/usr/local/lib/libLimeSuite.so.22.09.0`, reporting
`22.09.0-ge829d3ed`, ABI `22.09-1`. No Soapy modules were loaded into the
diagnostic. The low-level path avoided native `LMS_Open`/reference detection,
`LMS_Init`, RF configuration and stream setup.

The inspected FX3 open path resets USB bulk endpoints using
`CMD_USB_FIFO_RST` with payload `0x01` when bulk control is available, then
reads identity and checks versions. This is the unavoidable open-path effect;
it is documented from the implementation, **not a direct capture of constructor
traffic**. The installed per-connection packet callback is available only
after construction. The automatic legacy Si5351C initialization branch applies
to hardware below 4 and is not selected for the returned hardware 4 identity.
See the [matching FX3 source](https://github.com/myriadrf/LimeSuite/blob/e829d3ede6222c1c0fc0e90dcd2050e50569e33d/src/ConnectionFX3/ConnectionFX3.cpp).

After construction, all protocol packets were recorded. Transmitted commands
were exclusively one `CMD_GET_INFO` (`0x00`) and six `CMD_BRDSPI_RD` (`0x56`)
requests. Unexpected post-constructor non-read commands were guarded against
before the library's Write call. No post-constructor ADF4002, oscillator DAC,
RFIC, board-register or firmware write was sent. The helper contained no
explicit clock-selection, ADF programming, RF setter, update or capture call.

**What the indication can and cannot mean**

Official gateware **2.23** source maps `PERIPH_INPUT_RD_0(1)` to
`led2_adf_muxout`; the status feature was documented starting with release
2.20. Thus the standard release matching the returned identity supports this
register interpretation. See the
[2.23 source](https://github.com/myriadrf/LimeSDR-USB_GW/blob/7b39e7fdf918dd95a013c4e8c5e20c7cb447ceb1/src/general_periph/synth/general_periph_top.vhd)
and [release history](https://github.com/myriadrf/LimeSDR-USB_GW/blob/7b39e7fdf918dd95a013c4e8c5e20c7cb447ceb1/Changelog.txt).
The FPGA image's binary provenance was not independently authenticated; this
is a match to its reported release identity and official register map.

The observed bit is therefore consistent with **ADF MUXOUT high** under that
map. ADF MUXOUT is programmable. No current latch/configuration provenance
establishes that it was configured for digital lock detect, and the installed
ADF SPI readback API is unsupported. A high MUXOUT input alone also does not
prove external-control selection. Accordingly this report makes **no claim
that the external reference is locked, selected, or sustained**.

Current measured gateware 2.23 supersedes the historical 2.12 identity for
assessing today's register support. No gateware or firmware update occurred
in this diagnostic; it does not establish when the historical version changed.

The requested diagnostic needs no additional configuration and is complete.
The remaining interpretive gap is current ADF configuration provenance. If
that cannot be recovered, establishing a known configuration would require a
separately authorized hardware operation, for example
`LMS_SetClockFreq(existing_handle, LMS_CLOCK_EXTREF, 10000000)`. That operation
writes ADF4002 divider/control latches, selects external-reference discipline,
and can change oscillator tuning with phase/frequency settling. It was not
performed. The authorized connection has already closed; no further connection
or configuration is authorized by this completed single-connection run.

**Saved evidence**

- [Summary](results/local_evidence/runs/extref_once_20261109T004414Z_1bph5bsj/summary.json)
- [Immediate ownership guard](results/local_evidence/runs/extref_once_20261109T004414Z_1bph5bsj/guard.json)
- Post-open identity, raw values, packets and closure (`runs/extref_once_20261109T004414Z_1bph5bsj/diagnostic.jsonl`)
- Post-close ownership check (`runs/extref_once_20261109T004414Z_1bph5bsj/ownership_after.json`)
- [Build command and hashes](results/local_evidence/runs/extref_once_20261109T004414Z_1bph5bsj/build_manifest.json)

The helper and guard were compiled/checked using installed tools only. The
no-argument helper branch was verified to exit without a connection, and the
ownership guard was checked against a held character-device descriptor. No
installed driver/library was modified; no downloads or installations occurred.
