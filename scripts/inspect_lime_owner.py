#!/usr/bin/env python3
"""Print host process/USB ownership metadata without opening an SDR or device node.

Run in the normal SSH terminal. No SDR libraries, signals, ptrace, socket
connections, device opens, or filesystem writes are used. ss, when available,
only lists the kernel's socket metadata. Output is a non-atomic snapshot.
"""

import argparse
from datetime import datetime, timezone
import errno
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess


def read_text(path):
    return path.read_text(errors="replace").strip()


def process_identity(path):
    # comm may contain spaces and parentheses. Remaining fields start at field 3.
    fields = read_text(path / "stat").rsplit(")", 1)[1].split()
    return {"start_ticks": int(fields[19]), "state": fields[0],
            "ppid": int(fields[1])}


def usb_devices(serial, sysfs=Path("/sys/bus/usb/devices")):
    devices = []
    errors = []
    for entry in sorted(sysfs.glob("*")):
        try:
            if not (entry / "idVendor").exists():
                continue
            if (read_text(entry / "idVendor"), read_text(entry / "idProduct")) != ("1d50", "6108"):
                continue
            if read_text(entry / "serial") != serial:
                continue
            bus = int(read_text(entry / "busnum"))
            dev = int(read_text(entry / "devnum"))
            node = Path(f"/dev/bus/usb/{bus:03d}/{dev:03d}")
            item = {"sysfs": str(entry), "serial": serial, "node": str(node),
                    "speed_mbps": read_text(entry / "speed")}
            try:
                meta = node.stat()  # Metadata only: never open the USB node.
                item["node_is_character_device"] = stat.S_ISCHR(meta.st_mode)
                item["device_number"] = [os.major(meta.st_rdev), os.minor(meta.st_rdev)]
            except OSError as exc:
                item["node_error"] = str(exc)
            devices.append(item)
        except OSError as exc:
            errors.append({"sysfs": str(entry), "error": str(exc)})
    return devices, errors


def scan_processes(nodes, proc=Path("/proc")):
    owners = {}
    candidates = []
    denied = []
    scan_errors = []
    for entry in sorted((p for p in proc.iterdir() if p.name.isdigit()), key=lambda p: int(p.name)):
        pid = int(entry.name)
        try:
            comm = read_text(entry / "comm")
            if re.search(r"gnss-sdr|SoapySDRServer|gqrx|sdrangel|lime", comm, re.I):
                candidates.append({"pid": pid, "comm": comm})
            for fd in (entry / "fd").iterdir():
                try:
                    target = os.readlink(fd)
                except OSError as exc:
                    if exc.errno in (errno.ENOENT, errno.ESRCH):
                        continue
                    raise
                if target in nodes:
                    owners.setdefault(pid, []).append({"fd": fd.name, "target": target})
        except PermissionError:
            denied.append(pid)
        except OSError as exc:
            if exc.errno not in (errno.ENOENT, errno.ESRCH):
                scan_errors.append({"pid": pid, "error": str(exc)})
    return owners, candidates, denied, scan_errors


def inspect_process(pid, proc=Path("/proc")):
    base = proc / str(pid)
    result = {"pid": pid, "errors": []}

    def collect(key, fn):
        try:
            result[key] = fn()
        except (OSError, ValueError, IndexError) as exc:
            result["errors"].append({"field": key, "error": str(exc)})

    collect("identity_before", lambda: process_identity(base))
    collect("comm", lambda: read_text(base / "comm"))
    collect("argv", lambda: [v.decode(errors="replace") for v in
                             (base / "cmdline").read_bytes().split(b"\0") if v])
    for key in ("exe", "cwd"):
        collect(key, lambda key=key: os.readlink(base / key))
    collect("cgroup", lambda: read_text(base / "cgroup").splitlines())
    collect("namespaces", lambda: {name: os.readlink(base / "ns" / name)
                                    for name in ("pid", "mnt", "net")})
    collect("loaded_sdr_maps", lambda: [line for line in read_text(base / "maps").splitlines()
                                        if re.search(r"lib(LimeSuite|LMS7Support|SoapySDR|remoteSupport)|libgnuradio-(osmosdr|limesdr|soapy)", line)])

    def descriptors():
        selected = []
        for fd in sorted((base / "fd").iterdir(), key=lambda p: int(p.name)):
            try:
                target = os.readlink(fd)
                mode = fd.stat().st_mode  # stat follows the link, but opens nothing.
                regular = stat.S_ISREG(mode)
                if fd.name in ("1", "2") or target.startswith(("/dev/bus/usb/", "socket:[")) or (
                    regular and re.search(r"\.log(?:\.|$)|\.(?:INFO|WARNING|ERROR)(?:\.|$)|\.jsonl$", target)
                ):
                    selected.append({"fd": fd.name, "target": target,
                                     "regular_file": regular})
            except OSError as exc:
                if exc.errno not in (errno.ENOENT, errno.ESRCH):
                    result["errors"].append({"fd": fd.name, "error": str(exc)})
        return selected

    collect("selected_fds", descriptors)
    collect("identity_after", lambda: process_identity(base))
    before, after = result.get("identity_before"), result.get("identity_after")
    result["same_process_during_inspection"] = (
        before["start_ticks"] == after["start_ticks"] if before and after else None)
    return result


def socket_metadata(pids):
    if not pids:
        return {"note": "No selected PID; no socket query needed."}
    if not shutil.which("ss"):
        return {"note": "ss is absent; nothing was installed."}
    records = []
    for options in ("-Hantup", "-Hanxp"):
        try:
            output = subprocess.run(["ss", options], capture_output=True, text=True,
                                    timeout=10, check=False)
            lines = [line for line in output.stdout.splitlines()
                     if any(f"pid={pid}," in line for pid in pids)]
            records.append({"command": ["ss", options], "matching_lines": lines,
                            "returncode": output.returncode, "stderr": output.stderr.strip()})
        except (OSError, subprocess.TimeoutExpired) as exc:
            records.append({"command": ["ss", options], "error": str(exc)})
    return {"queries": records,
            "note": "Kernel metadata only; no connection or command sent. Missing PID details/other network namespaces can hide sockets; empty results do not prove no interface exists."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial", default="0009061C01502715")
    parser.add_argument("--pid", type=int, action="append", default=[],
                        help="also inspect this known receiver PID; repeatable")
    args = parser.parse_args()
    if any(pid <= 0 for pid in args.pid):
        parser.error("--pid must be a positive integer")
    devices, usb_errors = usb_devices(args.serial)
    nodes = {d["node"] for d in devices}
    owners, candidates, denied, scan_errors = scan_processes(nodes)
    pids = sorted(set(owners) | set(args.pid))
    report = {
        "utc": datetime.now(timezone.utc).isoformat(), "observer_pid": os.getpid(),
        "boot_id": read_text(Path("/proc/sys/kernel/random/boot_id")),
        "usb_devices": devices, "usb_metadata_errors": usb_errors,
        "usb_fd_holders": [{"pid": pid, "fds": fds} for pid, fds in sorted(owners.items())],
        "named_candidates_not_proven_owners": candidates,
        "fd_scan_permission_denied_pids": denied, "fd_scan_other_errors": scan_errors,
        "processes": [inspect_process(pid) for pid in pids],
        "sockets": socket_metadata(pids),
        "limits": [
            "Run in the normal host SSH terminal. An isolated/container PID or mount view cannot establish host ownership.",
            "An open USB descriptor identifies an FD holder, not proof of interface claim or active streaming.",
            "No visible holder does not prove the device is idle; permissions, namespaces, process exits and USB re-enumeration can hide or race observations.",
            "No lock or gateware status is queried. No device node, process memory, pipe, terminal or socket payload is read.",
            "Do not read /proc/PID/fd/1 or fd/2 contents: they may be live pipes or terminals. Only their link targets are reported.",
        ],
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
