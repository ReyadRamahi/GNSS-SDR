**External-reference audit — 2026-11-08. Current sustained ADF4002 lock is unknown.**

**Later controlled result:** one user-authorized connection measured hardware
4, firmware 4, gateware **2.23** and post-open raw `0x00c8 = 0x0002`. Current
MUXOUT configuration remains unknown, so external lock is inconclusive. See
[the diagnostic result](LIMESDR_REFERENCE_DIAGNOSTIC_RESULT.md). The original
read-only audit and its historical observations are retained below.

Scope: LimeSDR-USB serial `0009061C01502715`, external-reference selection and
lock only. No PVT/build investigation, device connection, receiver launch,
download to disk, installation, update, driver patch, or firmware change was
performed. Work consisted of installed-file inspection, historical-log reads,
USB sysfs metadata, and online documentation/source reads. This report is the
only workspace addition from this audit.

**Locally verified installation and historical evidence**

| Item | Evidence/result |
| --- | --- |
| System LimeSuite | Package `liblimesuite20.10-1` is `20.10.0+dfsg-5`; ELF library `/usr/lib/x86_64-linux-gnu/libLimeSuite.so.20.10.0`. |
| Local LimeSuite | `/usr/local/lib/libLimeSuite.so.22.09.0`; SONAME link `libLimeSuite.so.22.09-1`. |
| LimeUtil | `/usr/local/bin/LimeUtil` explicitly needs `libLimeSuite.so.22.09-1`. |
| Two Soapy modules | System `modules0.8/libLMS7Support.so` needs 20.10; `/usr/local/lib/SoapySDR/modules0.8/libLMS7Support.so` needs 22.09. `readelf -d` confirms the dependencies. |
| Soapy runtime | Installed SoapySDR package/library version 0.8.1. Both Lime modules import the base clock-source/reference-rate methods. No corresponding Lime overrides were found. |
| Base-method behavior | Local `libSoapySDR.so.0.8` disassembly shows `setClockSource` and `setReferenceClockRate` immediately return; source/list getters return empty values and reference-rate getter returns zero. These are unsupported defaults, not hardware observations. |
| USB metadata | Sysfs path `2-1.1.2`, VID/PID `1d50:6108`, serial above, speed `5000`, bus 2/device 7. Enumeration proves neither ownership nor external lock. |
| Current access limit | `/dev/bus/usb` is absent; `/proc` exposes only the isolated tool processes. Host receiver ownership cannot be established from this process view. No conclusion that the host radio is idle is justified. |

The two modules' presence does not identify which module a current receiver
loaded. The saved November RX1_H baseline has process maps showing system
20.10 isolation; that describes that historical process only. No plugins were
removed, and no search paths were changed in this audit.

Historical records contain both reported states:

- April clock check (`output/clock_checks/lime_refclk_10mhz_20260428_090528.log`),
  line 15: `ADF4002 Lock State: 0`; the same log reports gateware 2.12 while
  the utility expects 2.23.
- April retry (`output/clock_checks/lime_extref_retry_20260428_221451.log`),
  line 16: state 0 with the same mismatch.
- May sweep startup (`runs/sweep_master.log`), line 7: state 1, before the
  receiver runs. It is not a lock time series during streaming.

These records do not establish today's gateware or sustained lock. The
`30.72 MHz` message is consistent with either DAC-controlled or externally
disciplined operation of the onboard oscillator. The reference detector also
rounds a frequency estimate to a table; its displayed value is not a precision
frequency measurement or an external-lock measurement.

**Ownership and API effects**

Status can be read while streaming **through the existing owner's handle**,
provided its application exposes the read or is instrumented to perform it.
An independent process cannot borrow another process's Lime/Soapy object by
using the same serial number. Its own device construction is a new open.

Both release sources claim USB interface 0 in `ConnectionFX3::Open`. An
already-claimed interface normally makes another claim fail busy. After a
successful open, the FX3 path can send `CMD_USB_FIFO_RST` with payload `0x01`
when bulk control is available. Consequently even a low-level connection
constructor is not a passive status operation. The higher-level native open
also invokes reference detection, which writes FPGA test-control registers
`0x61` and `0x63`. A Soapy make/probe additionally calls device initialization,
enables channels, and sets gains; destruction disables channels. These paths
are unsuitable as a concurrent status monitor. See the
[20.10 FX3 source](https://github.com/myriadrf/LimeSuite/blob/v20.10.0/src/ConnectionFX3/ConnectionFX3.cpp),
[22.09 FX3 source](https://github.com/myriadrf/LimeSuite/blob/v22.09.0/src/ConnectionFX3/ConnectionFX3.cpp),
[native constructor](https://github.com/myriadrf/LimeSuite/blob/v22.09.0/src/API/LmsGeneric.cpp),
and [libusb interface-claim documentation](https://libusb.sourceforge.io/api-1.0/group__libusb__dev.html#gaee5076addf5de77c7962138397fd5b1a).

| Installed interface/operation | What it actually does |
| --- | --- |
| `LMS_ReadFPGAReg(existing_handle, 0x00c8, &word)` | Board-register read; decode `(word & 0x0002) >> 1` only with compatible gateware and known ADF MUXOUT configuration. Check return status before using the word. |
| C++ `IConnection::ReadRegister(0x00c8, word)` | Lower-level board-register read used by LimeUtil, on an already-owned connection. |
| Soapy `existing_device.readRegister("BBIC", 0x00c8)` | Installed Lime implementation routes to FPGA read, under its access mutex. It can report the same bit; creating a new Soapy device to call it introduces the open/init effects above. |
| Soapy `clock_locked` | LMS7002M CGEN PLL lock, not ADF4002. |
| Soapy channel `lo_locked` | LMS7002M RX/TX synthesizer lock, not ADF4002. |
| `LMS_GetClockFreq(..., LMS_CLOCK_REF, ...)` | Reports the RFIC reference-frequency value; does not establish external-reference selection or lock. |
| `LMS_GetClockFreq(..., LMS_CLOCK_EXTREF, ...)` | Unsupported external-reference read; returns failure. EXTREF is documented as write-only. |
| `ReadADF4002SPI` | Both installed libraries export it, but disassembly shows an unsupported-operation error and return `-1`. It is not a working lock getter. |
| `LMS_SetClockFreq(..., LMS_CLOCK_EXTREF, 10000000)` | Programs ADF4002 divider/latch values to discipline the onboard oscillator to the supplied 10 MHz reference. It changes hardware. Nonpositive EXTREF takes the disable/DAC path. |
| `LMS_VCTCXOWrite` / DAC write | Changes oscillator tuning/control; not a status check. |
| `LMS_Init` | Resets/configures/calibrates the RFIC and sets its rate. The traced base Init does not itself explicitly select EXTREF or write the oscillator DAC; do not describe it as necessarily disabling ADF lock. Startup still requires a subsequent lock observation. |
| `LimeUtil --refclk ... --fref=10000000` | Opens a low-level connection, writes four 24-bit ADF4002 words via SPI target `0x30`, then reads `0x00c8` once and releases the connection. It is a setter followed by a snapshot, without a sustained-lock wait. |

The installed LimeUtil binary confirms the last row: instructions around
`0x5d59` issue the SPI transaction; around `0x5d8a` they select register `0xc8`;
around `0x5dbd`/`0x5dcf` they shift right once and mask with 1. This matches
[release source](https://github.com/myriadrf/LimeSuite/blob/v22.09.0/LimeUtil/LimeUtil.cpp).
The source comment says “Bit 2”; the implemented mask is **zero-based bit 1**.

Register bit 1 is a view of the ADF **MUXOUT pin**, not an ADF configuration
readback. Its interpretation as lock requires MUXOUT to be configured for
lock detect. A successful setter alone establishes neither signal presence
nor lock. The Soapy register/sensor behavior is visible in
[20.10 Settings.cpp](https://github.com/myriadrf/LimeSuite/blob/v20.10.0/SoapyLMS7/Settings.cpp)
and [22.09 Settings.cpp](https://github.com/myriadrf/LimeSuite/blob/v22.09.0/SoapyLMS7/Settings.cpp).

**Important gateware qualification**

Official gateware commit
[`bc7a213`, 2019-01-29](https://github.com/myriadrf/LimeSDR-USB_GW/commit/bc7a21343ddf67979ab246f0d597223fd9573e8e)
added ADF MUXOUT to `PERIPH_INPUT_RD_0(1)`. Its parent drove that bit to zero.
The address is peripheral base `0xc0` plus offset 8. Current source confirms
the mapping in
[general_periph_top.vhd](https://github.com/myriadrf/LimeSDR-USB_GW/blob/master/src/general_periph/synth/general_periph_top.vhd)
and [periphcfg.vhd](https://github.com/myriadrf/LimeSDR-USB_GW/blob/master/src/spi/periphcfg.vhd).
This audit has not matched the historically installed 2.12 image to that
commit. Until the running gateware's mapping is established, a zero could
mean an unavailable status bit rather than an unlocked ADF4002. No update is
proposed as a prerequisite; the board LED is an alternative observation.

**Forum reports and official Soapy history**

- [10 MHz Ref Input, 2017–2018](https://discourse.myriadrf.org/t/10-mhz-ref-input/813):
  users describe GUI/C-API setup and the reference LED. The posted C examples
  call Init and perform writes; they are not passive probes. Electrical
  advice varies within the thread and is not an electrical specification for
  the unidentified onsite source.
- [Pothos LimeSDR-USB external clock setting, May 2018](https://discourse.myriadrf.org/t/pothos-limesdr-usb-external-clock-setting/2793):
  the UI exposes only Default, and the workaround programs ADF4002 separately.
- [Change LimeSDR Clock Source using SoapyLMS7, September 2019](https://discourse.myriadrf.org/t/change-limesdr-clock-source-using-soapylms7/5142):
  a user proposes adding the missing Soapy API. A proposal is not evidence
  that it was present in a release.
- Official commit
  [`b4def4af`](https://github.com/myriadrf/LimeSuite/commit/b4def4af1ba2395b860542280837a224a0d57f6c),
  authored 2023-02-13, adds `setReferenceClockRate` forwarding to EXTREF.
  [`aadce95c`](https://github.com/myriadrf/LimeSuite/commit/aadce95c84d3928e9a3883b158a6cbbf46a9937f),
  authored 2023-03-31, adds clock-source list/get/set and reference-rate
  getters. [PR #373](https://github.com/myriadrf/LimeSuite/pull/373) merged on
  2023-05-01. Both installed release baselines predate these changes, and the
  actual binaries confirm absence of the overrides. Even the newer getters
  return cached requested state; they are not external-lock sensors.

AI-generated screenshots were not used as evidence. No screenshot attachments
were available in this turn. Findings above come from original posts, official
source/history, installed binaries, and saved logs.

**Remote follow-up supersedes the earlier proposed test**

The user has no physical access. Onsite inspection and LED video are not
required next steps. The current procedure is
[LIMESDR_REMOTE_REFERENCE_CHECK.md](LIMESDR_REMOTE_REFERENCE_CHECK.md).
It supplies a host-side process/USB metadata collector, current-log and
control-interface checks, and the exact limits on obtaining repeated ADF
status through the existing owner's connection. No second connection,
interruption, hardware change, installation, download, or patch is authorized.

Remaining uncertainties include the actual current owner and loaded module,
current gateware/status mapping, ADF MUXOUT configuration and lock, and the
reported source's electrical compatibility. These do not make physical
inspection a prerequisite for the remote metadata and software checks.

**One concrete next step:** in normal host SSH, run
`python3 /home/rrama28/gnss/scripts/inspect_lime_owner.py` and return the JSON.
The collector opens no device node and sends no command to a receiver. If the
owner is the unmodified GNSS-SDR/gr-osmosdr stack, its existing public interfaces
do not expose ADF status; current lock then cannot be established under the
unchanged no-patch/no-interruption/no-second-connection constraints. The remote
procedure identifies the smallest specific future instrumentation or access
gap rather than requiring physical inspection.
