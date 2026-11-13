**Prepared for approval only. No device connection or programming occurred during preparation.**

Target: LimeSDR-USB serial `0009061C01502715`, previously measured HW4/FW4,
protocol 1, gateware 2.23. This is an idle external-reference test, with no
receiver/capture/stream start, RFIC initialization, LO/gain/filter/channel
changes, firmware update, installation or download. Reading official source
and documentation online was used to review the operations.

The helper was compiled against the existing
`/usr/local/lib/libLimeSuite.so.22.09.0`. Its prepared launcher verifies hashes
of the binary, source, launcher, ownership helpers and library before running.
The installed drivers/libraries were not modified. Nine offline scenarios
passed: normal sampling accounting, read errors and missed slots, uncertain
programming, failed baseline return, read exception cleanup, failed initial
DAC read, interruption cleanup, failed initial status read, and failed logging. These tests
used a fake device/clock and opened no SDR.

**Concrete command proposed for approval**

From `/home/rrama28/gnss`:

```bash
sudo -n /usr/bin/python3 scripts/run_lime_external_reference_test.py \
  --execute \
  --output runs/extref_idle_prepared_20261109T012546Z_95hauim6
```

This command has **not** been executed. Omitting `--execute` only prints the
prepared plan. The prepared directory currently has no `attempt_reserved`
marker or hardware test log. The launcher creates an exclusive attempt marker
before execution and never reuses that directory or retries a connection.

**Ownership and one-connection procedure**

Immediately before launching the helper, the host-root launcher:

1. Resolves the current USB node from the exact serial in sysfs; requires one
   accessible character-device target and the host process view.
2. Stops if a USB interface driver is attached.
3. Scans all visible `/proc/*/fd` entries by character-device major/minor,
   including mount aliases. Any holder or non-transient scan error stops the
   test without opening the SDR. No existing process/service is interrupted.
4. Checks that node identity/serial did not change during the scan, records
   the scan time, then launches the helper. The USB interface claim is the
   final exclusion against a competing opener after the metadata check.

The helper makes one low-level FX3 `ConnectionRegistry::makeConnection` call,
without a retry, and keeps that same claimed connection through programming,
settling, sampling and the DAC-baseline return. Registry discovery internally
opens/closes temporary descriptor handles before making the claimed control
connection, as in the previously inspected path. There is no separate status
probe or reconnect. The existing Soapy server may remain listening; it must
not hold the USB device.

The FX3 constructor includes a USB bulk-control-endpoint reset and identity/
version reads. Constructor traffic cannot be captured by the per-connection
callback, which becomes available afterward. On the previously verified HW4
unit the legacy hardware-below-4 Si5351C initialization branch is not selected.
The helper checks the reviewed HW4/FW4/protocol-1/GW2.23 identity after opening
and refuses explicit test programming if it differs. This path does not call
native `LMS_Open`/reference detection, `LMS_Init` or Soapy device creation.

All subsequent host protocol traffic is logged. The callback permits identity,
FPGA and analog-parameter reads, and only the exact planned ADF and DAC write
payloads during their respective phases; other commands are blocked before
the library's Write call.

**Exact configuration operations and effects**

First, without changing a setting, read:

```cpp
uint8_t id = 0;
conn->CustomParameterRead(&id, &reported_dac_code, 1, nullptr);
conn->ReadRegister(0x00c8, raw_before_program);
```

Parameter 0 reports the firmware's remembered VCTCXO DAC code, **not** a direct
measurement of tuning voltage or a record of the previous control mode. For
the reviewed gateware controller this is an 8-bit code. Both reads must succeed
and the DAC code must be an integer in 0–255; otherwise stop before programming.
The pre-program raw bit remains uninterpreted because prior MUXOUT programming
is unknown. These reads are already after the connection constructor.

Build the ADF words with the installed `lime::ADF4002` class. Initialize its
frequency members before `SetDefaults()` because that method calculates
dividers. Set Fref=10 MHz and Fvco=30.72 MHz, then explicitly set:

```cpp
adf.SetReferenceCounterLatch(0, 0, 125);       // LDP=0, ABW=0, R=125
adf.SetNCounterLatch(0, 384);                 // charge-pump gain=0, N=384
adf.SetFunctionLatch(7, 7, 0, 0, 1);         // MUXOUT=001, digital lock detect
adf.SetFunctionLatchRgr(1, 0, 0, 0, 0);       // positive PD polarity; normal operation
adf.SetInitializationLatch(7, 7, 0, 0, 1);   // explicitly set MUXOUT here too
adf.SetInitializationLatchRgr(1, 0, 0, 0, 0);
```

The installed library generated this exact ordered sequence:

| Latch | 24-bit word |
| --- | --- |
| Initialization | `0x1f8093` |
| Function | `0x1f8092` |
| Reference counter | `0x0001f4` |
| N counter | `0x018001` |

One call sends the four words, most-significant byte first:

```cpp
conn->TransactSPI(0x30, words.data(), nullptr, 4);
```

SPI target `0x30` becomes LMS64C `CMD_ADF4002_WR` (`0x31`). The reviewed
gateware controller first places the oscillator DAC output into high impedance,
then writes those ADF latches. This selects ADF control of the onboard VCTCXO,
using the external 10 MHz input and a nominal 30.72 MHz feedback frequency;
10 MHz / 125 = 30.72 MHz / 384 = 80 kHz PFD comparison frequency. The operation
changes oscillator discipline and can cause phase/frequency settling.

MUXOUT code `001` is active-high digital lock detection. LDP=0 uses the chip's
three-PFD-cycle lock criterion. This differs from the software's three
consecutive 1 Hz samples used for reporting below. The remaining control
fields match LimeSuite's reviewed defaults. The words, write intent, transmitted
packet and return status are logged. There is no ADF latch readback in the
installed API; an acknowledged command is recorded as such, not described as
independent verification of every physical latch.

Reviewed primary sources:
[installed-version ADF encoder](https://github.com/myriadrf/LimeSuite/blob/e829d3ede6222c1c0fc0e90dcd2050e50569e33d/src/ADF4002/ADF4002.cpp),
[installed-version protocol encoding](https://github.com/myriadrf/LimeSuite/blob/e829d3ede6222c1c0fc0e90dcd2050e50569e33d/src/protocols/LMS64CProtocol.cpp),
[gateware 2.23 controller](https://github.com/myriadrf/LimeSDR-USB_GW/blob/7b39e7fdf918dd95a013c4e8c5e20c7cb447ceb1/software/lms_ctr_app/main.c),
and [ADF4002 datasheet, MUXOUT/latch maps](https://www.analog.com/media/en/technical-documentation/data-sheets/ADF4002.pdf).

**Settling, five-minute sampling, and interpretation**

The monotonic epoch starts when the programming call returns successfully.
There is a **30-second settling interval**, with status sampled at nominal
t=0,1,…,29 seconds. Thirty seconds is a chosen observation allowance, not a
promise that lock will acquire by then. A failed or uncertain programming
return skips sampling and immediately attempts the documented DAC baseline.

The five-minute evaluation window then runs from nominal t=30 through t=330
seconds. It has **301 scheduled boundary samples at 1 Hz**, spanning 300
seconds. All reads use the same connection:

```cpp
conn->ReadRegister(0x00c8, raw);
// Only on a successful read after acknowledged known programming:
lock_sample = (raw & 0x0002) >> 1;
```

For each observation record wall-clock UTC, monotonic request/completion time,
scheduled slot, lateness, read status, raw word and interpreted sample or null.
Reads are scheduled against absolute monotonic times. Expired slots are logged
as missing; the helper does not burst catch-up reads or reuse old values.
Library errors and raw protocol packets are also retained.

The summary reports:

- First successful high sample after programming, with acquisition timing
  limited by observation cadence. If the first sample is high, the actual
  acquisition transition was not observed.
- First confirmation by three adjacent, successful high samples, without a
  completion interval above 1.5 seconds. This is a reporting criterion, not a
  redefinition of the chip's lock detector.
- Observed adjacent low-to-high transitions, every sampled low state, read
  errors, missing slots, requests over 250 ms late and completion gaps above
  1.5 seconds. Error/gap timestamps remain in the raw log; errors are unknown
  observations rather than unlocked states.
- Whether all scheduled five-minute observations completed successfully and
  high, and whether baseline return checks succeeded. Shorter unlock events
  between observations cannot be excluded. A low/error/gap is not hidden by a
  later lock acquisition.

The register interpretation is supported by the standard gateware 2.23
[MUXOUT mapping](https://github.com/myriadrf/LimeSDR-USB_GW/blob/7b39e7fdf918dd95a013c4e8c5e20c7cb447ceb1/src/general_periph/synth/general_periph_top.vhd)
and the explicit programming/ACK in this proposed test. This does not certify
the source's electrical compatibility, PRS10 discipline, or RF reception.

**Return to a documented baseline through the same connection**

Default end state is deliberately **DAC control using the reported pre-test
code D**, not “restore the previous external-reference state”:

```cpp
uint8_t id = 0;
double value = saved_pretest_code;
conn->CustomParameterWrite(&id, &value, 1, "");
```

The host packet is `CMD_ANALOG_VAL_WR` (`0x61`), one block with bytes
`00 00 00 D`. In the reviewed controller, that command internally writes the
ADF disable/ground-MUXOUT preset words
`0x1f81f3`, `0x1f81f2`, `0x0001f4`, `0x018001`, places the ADF charge pump in
high impedance, and enables the DAC at D. It does **not** write EEPROM or
restore unknown previous ADF latches. It removes external discipline and may
cause another oscillator phase/frequency transient. There are no RFIC setters.

After a successful baseline write, wait approximately one second in ordinary
completion, then read parameter 0 and raw `0x00c8` again. Report whether the
code equals D and MUXOUT bit 1 is low, as expected for that documented baseline.
This checks reported state consistency; it does not measure DAC voltage,
oscillator frequency, or exact restoration of the previous state. An interrupt
can shorten this verification pause.

Baseline return is attempted once after any ADF programming attempt, even if
the programming ACK fails or a later read throws. An ordinary SIGINT/SIGTERM
requests cleanup on the same connection; the launcher forwards it and waits
for the helper. Do not use a shell timeout or forced kill. SIGKILL, power loss,
or a lost USB connection can prevent baseline return. Failed baseline writes
or verification are reported as final state unknown, without retry/reconnect
or an invented claim of restoration. RAII then releases the connection.

**Artifacts and scope boundary**

Prepared artifacts are under
`runs/extref_idle_prepared_20261109T012546Z_95hauim6/`: build manifest/hashes,
compiler log, exact plan and offline test result. An approved run will add
`guard.json`, `attempt_reserved`, `test.jsonl` and `test.stderr`. The guard also
checks for USB holders after the helper exits. Exit 0 requires the complete
window high with no recorded timing/read gaps and successful baseline checks;
exit 4 preserves low/error/gap observations; aborted tests/baseline failures
return 3, fatal helper errors 2, and launcher/ownership failures 10. Exit codes
do not replace the timestamped evidence.

This test never starts a receiver. Monitoring during receiver streaming is a
separate future integration: configure and read status through the receiver's
sole owning connection. Do not run this idle utility alongside a receiver.

**Approval is pending for the concrete command above, including its ADF write
and final return to the documented DAC-control baseline.**
