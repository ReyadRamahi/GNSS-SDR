**Remote-only reference check. Current ADF4002 lock cannot yet be established.**

**Later controlled result:** the user subsequently authorized one connection.
It completed and closed cleanly, reporting gateware **2.23** and raw
`0x00c8 = 0x0002` after opening. MUXOUT configuration remains unknown, so lock
is inconclusive. See [the result](LIMESDR_REFERENCE_DIAGNOSTIC_RESULT.md).
The procedure below records the preceding remote-only phase; its no-open
restriction was relaxed only for that completed, single-connection diagnostic.

**Pre-diagnostic host evidence:** the user supplied an elevated snapshot dated
`2026-11-09T00:36:18Z`. The scan reported no permission failures or other scan
errors, and no holder of `/dev/bus/usb/002/007` for the target serial.
`SoapySDRServer` PID 1343 is the systemd service
`soapyremote-server.service`, with arguments `/usr/bin/SoapySDRServer --bind`.
It has no reported USB FD and listens on TCP 55132; no established TCP client
appears in its socket snapshot. Its established Unix sockets are not evidence
of an SDR client. Both LimeSuite versions and both LMS7 plugins are mapped in
the process, which shows module loading, not an open Lime or selected driver.

This snapshot supplies no existing Lime connection or active Lime stream to
reuse for status reads. It does not measure lock. The FD scan is a point-in-time
path-based observation, not an absolute exclusion of races or alternate device
mount paths. Nothing in this result authorizes opening the device.

This procedure replaces the onsite next step in the earlier audit. No physical
inspection, second SDR connection, stream interruption, hardware setting,
download, installation, or driver patch is required or performed here.

**Run this first in the normal host SSH terminal**

```bash
cd /home/rrama28/gnss
python3 scripts/inspect_lime_owner.py
```

The script uses Python's standard library and the installed `ss` command. It
finds the current USB bus/device address from serial `0009061C01502715`, scans
`/proc/*/fd` symlink targets for holders of that node, and prints JSON. For
each holder it reports executable/arguments, PID start ticks, loaded SDR
library mappings, stdout/stderr destinations, regular log-file candidates,
cgroup/namespaces, and socket metadata. It never opens `/dev/bus/usb`, imports
an SDR library, connects to a control socket, signals a process, uses ptrace,
reads a pipe/terminal payload, or writes a file. `ss` lists kernel metadata;
it does not send an application command.

If relevant metadata is denied, the same read-only collection can be run
with the host account's existing administrative access:

```bash
sudo /usr/bin/python3 /home/rrama28/gnss/scripts/inspect_lime_owner.py
```

If the USB owner is a server, or a known receiver has no direct USB descriptor,
also inspect its PID (substitute the real numeric PID):

```bash
python3 scripts/inspect_lime_owner.py --pid 12345
ps -p 12345 -o pid,ppid,lstart,etimes,stat,comm,args
```

Repeat `--pid` for an identified server/client pair. A connected remote SDR
client may own a network socket while only the server owns the USB FD. A
named receiver process alone is not proof that it is the Lime's receiver.
Inspect the server's established socket peer to locate its current client;
do not start a client to discover it. Empty socket output may reflect socket
permissions or another network namespace. Empty USB-owner output likewise
does not prove availability. A USB FD holder is evidence of an open device,
not by itself proof of interface claim or active streaming.

If the host uses containers, the collection needs the host's PID/device view
and access to the relevant process metadata. Escalating inside this chat's
isolated process namespace would not supply that view.

**Determine whether the actual owner already publishes a useful status**

Use the reported `exe`, `argv`, maps and socket lines, rather than assuming a
specific receiver is running. `argv` identifies the selected configuration
and, for a Python owner, its script. Read those exact files; do not execute
the receiver, its launcher, or its help/probe mode to inspect it. A current
configuration file is supporting evidence only: it may have changed since
the process read it.

For an identified GNSS-SDR configuration, this command reads its current file:

```bash
rg -n '^[[:space:]]*(SignalSource[^.]*\.|GNSS-SDR\.telecommand_|Monitor\.|.*Monitor\.)' /absolute/path/from/argv.conf
```

The following results are established for software present in this workspace:

| Actual owner/client | Existing status route |
| --- | --- |
| GNSS-SDR 0.0.16 with `Osmosdr_Signal_Source` | No ADF4002 register read or periodic external-lock log in the inspected source. Its optional TCP `status` command returns position/time/speed/course or absence of navigation data. It does not read the Lime. The ordinary UDP monitor transports GNSS measurements, not external-reference lock. |
| `scripts/capture_rx1h_baseline.py` or its saved copies | No control server or ADF reader. The logged RF readbacks and sample checks do not establish external lock. |
| gr-osmosdr 0.2.3 Soapy source | Holds `SoapySDR::Device *_device` privately and exposes no register/sensor getter in its public source API. The existing handle cannot be reached from a new shell Python process. |
| Already-running SoapyRemote 0.5.2 server | Its current client's existing control session supports hardware-info and named register reads through the server's `_dev`. This is useful only if that current client already has a supported way to invoke them. A listening server port alone is insufficient. No second remote client is proposed. |
| Another/custom owner | Inspect its exact script/source and documented control handlers for an existing read-only register getter or periodic raw ADF status publisher. Do not test an unidentified port with guessed commands. |

Local GNSS-SDR evidence:
command registration and status handler (`/home/rrama28/src/gnss-sdr-0.0.16/src/core/receiver/tcp_cmd_interface.cc:56`),
telecommand enable/default port (`/home/rrama28/src/gnss-sdr-0.0.16/src/core/receiver/control_thread.cc:147`),
Osmosdr adapter (`/home/rrama28/src/gnss-sdr-0.0.16/src/algorithms/signal_source/adapters/osmosdr_signal_source.cc:31`),
and public source API (`/usr/include/osmosdr/source.h:349`).
Installed Doxygen source also shows the private pointer in
`/usr/share/doc/gr-osmosdr/html/soapy__source__c_8h_source.html`.
Official matching sources confirm the
[gr-osmosdr private handle](https://github.com/osmocom/gr-osmosdr/blob/v0.2.3/lib/soapy/soapy_source_c.h)
and [SoapyRemote handlers](https://github.com/pothosware/SoapyRemote/blob/soapy-remote-0.5.2/server/ClientHandler.cpp).

The live executable, loaded mappings and any local changes still need matching
to these implementations. Package presence does not identify the running
program or establish an available service.

**Inspect only the current process's real logs**

Use regular log paths from the report, its command line or its service
configuration. Substitute an actual path, not a `/proc/PID/fd/N` path:

```bash
rx_log=/absolute/path/to/current/receiver.log
if [ -f "$rx_log" ]; then
    tail -n 400 -- "$rx_log" | rg -i 'ADF4002|MUXOUT|extref|external.*(clock|ref|lock)|gateware|firmware|hardwareVersion|0x0*c8|BBIC|overrun|overflow|stream'
fi
```

For a systemd-managed owner, its cgroup can identify the service. Existing
journal records can be read without contacting the receiver:

```bash
journalctl -b _PID=12345 --no-pager -n 300
```

Check records against the current process's start time: PIDs and log filenames
can be reused. If stdout/stderr targets a pipe or terminal, do not read that
FD; it could consume live data or input. Use the journal or the launcher's
regular log instead. An unavailable log is an access gap, not evidence of
absence of lock.

If that same owner already emits genuine periodic ADF observations, obtain
five minutes of new records without changing the producer:

```bash
if [ -f "$rx_log" ]; then
    timeout 300s tail -n 0 -F -- "$rx_log" |
        rg --line-buffered -i 'ADF4002|MUXOUT|extref|0x0*c8|BBIC|overrun|overflow|stream'
fi
```

`timeout` limits only the log reader; exit 124 is expected at five minutes.
For a journal producer use `journalctl -b -f -n 0 _PID=12345` under the same
reader-only timeout. Neither command creates observations that the receiver
does not already emit. A startup `LimeUtil --refclk` print from a launcher is
not a during-stream status sample, even when it shares the log pathname.

**If the existing owner exposes raw reads**

The installed Lime Soapy implementation can use
`existing_device.readRegister("BBIC", 0x00c8)`; a native owner can use
`LMS_ReadFPGAReg(existing_handle, 0x00c8, &word)`. These are operations for an
already-accessible object inside the owner, not standalone shell commands.
Do not call `Device.make`, `LMS_Open`, `LimeUtil`, or `SoapySDRUtil --probe`
to obtain an object. Do not enable a disabled service or modify a running
configuration.

Before interpreting the result:

1. Obtain board/gateware identity through that same existing interface's
   hardware-info getter or already-recorded startup identity. If available,
   read BBIC registers `0x0000`–`0x0003` individually through it: board ID,
   gateware version, gateware revision, hardware/BOM identity. Preserve raw
   values and match the exact image/build provenance to its register map.
   The version expected by a library is not the version actually loaded.
2. Establish that this gateware maps `PERIPH_INPUT_RD_0(1)` to ADF MUXOUT.
   Official [commit bc7a213](https://github.com/myriadrf/LimeSDR-USB_GW/commit/bc7a21343ddf67979ab246f0d597223fd9573e8e)
   added that mapping; its parent returned zero for the bit. No general
   minimum revision number is assumed here. A successful register read alone
   does not prove the status feature exists.
3. Establish from the current owner's setup/provenance that ADF MUXOUT is
   configured for digital lock detect. This input is not a readback of ADF
   latch configuration or of the DAC/ADF control selection. Without that
   provenance report a raw MUXOUT level, not proven external-reference lock
   or source selection. ADF SPI readback is unsupported in the installed
   LimeSuite; do not rewrite its latches merely to learn their configuration.
4. Through the already-supported interface request one observation per second
   for five minutes. Record UTC/monotonic time, raw `0xc8`, read success/error,
   `(word & 2) >> 1`, current owner identity, and receiver stream progress or
   stream error counters. Preserve exceptions as unknown, not zero or the
   last good value. Read-only requests still incur control-transfer latency;
   check the concurrent stream for overruns.

Only with those qualifications can all successful lock samples equal to 1
support “ADF lock observed at 1 Hz during this streaming interval.” Missing
samples or an unsupported map prevent that conclusion. Polling cannot exclude
shorter unlock events. CGEN/LO locks, nominal frequencies, sample activity and
navigation status are not substitutes for this measurement.

**Smallest specific gap if the owner is the unmodified GNSS-SDR stack**

There is no existing public register-reading path through this application's
gr-osmosdr wrapper, and attaching a debugger would pause it. Additional SSH
or root access alone cannot add the missing callback without changing the
running program. No debugger, injection, USB-FD duplication or new connection
is proposed.

The smallest targeted future instrumentation is a periodic read/log callback
in gr-osmosdr's `soapy_source_c`, where `_device` already exists. It would log
the board/gateware identity once, then `BBIC:0xc8`, errors and stream sample
progress about once per second, with no setters/open/init calls. It belongs
inside the owning source's existing execution/control path, not in a helper
that constructs a device. The exact loaded source/library must first be
identified. This is a wrapper patch and would require relaxing the current
no-patching restriction and a later approved restart to load it; none is
implemented or requested for execution now. It also cannot compensate for
gateware that lacks the status mapping or unknown ADF MUXOUT configuration.

If another owner already exposes the getter or periodic telemetry, the
smallest additional access is access to **that owner's existing supported
control session or current log**, plus current gateware/ADF setup provenance.
For an uninstrumented GNSS-SDR/gr-osmosdr owner, **current lock is not remotely
establishable under the unchanged no-patch/no-interruption/no-second-connection
constraints**.

**Current conclusion and smallest additional capability:** the supplied host
snapshot identifies no current Lime owner or active remote SDR client. There
is therefore no live status getter available through an existing connection
in the evidence supplied. More metadata privileges are not the missing step.
Under the unchanged existing-connection-only constraints, current lock remains
unobservable.

For current lock alone, the smallest additional operation would be one
explicitly authorized, exclusive diagnostic connection, followed only by
identity/status reads. It is not passive end-to-end: FX3 open can reset USB
endpoints; native `LMS_Open` also runs reference detection that writes FPGA
test-counter controls. No such open has been executed or recommended for
immediate execution. Gateware mapping and ADF configuration provenance would
still qualify interpretation of its raw MUXOUT reads.

For lock during future receiving, the needed capability is a status publisher
inside the next receiver's sole owning connection. A separately authored
diagnostic receiver using the already-installed native LimeSuite or direct
Soapy API could provide this without modifying installed drivers, but starting
or configuring it would be a new hardware-affecting operation outside this
read-only session. For the existing GNSS-SDR/gr-osmosdr stack the targeted
wrapper callback described above remains the minimal instrumentation change.
Neither a new client to TCP 55132 nor restarting the idle server would add
status telemetry to the current snapshot. No physical inspection is required
as the next step.
