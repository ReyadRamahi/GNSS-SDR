#!/usr/bin/env python3
"""Fail-closed host ownership guard for one explicitly authorized FX3 diagnostic.

Default only prints effects. --run requires an existing output directory with
the compiled diagnostic named read_lime_reference_once. No retries or settings.
"""
import argparse
from datetime import datetime, timezone
import errno
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys

sys.dont_write_bytecode = True
from inspect_lime_owner import usb_devices

LIBRARY = Path("/usr/local/lib/libLimeSuite.so.22.09.0")
LIBRARY_SHA256 = "0afd2a9b2d8afe2823ce316683a3d40c36a116adf1648f6ad86a99da770c10be"
SERIAL = "0009061C01502715"


def ownership_scan(node):
    """Match character device number as well as path, including mount aliases."""
    target = node.stat()
    if not stat.S_ISCHR(target.st_mode):
        raise RuntimeError("USB node is not a character device")
    owners, failures = [], []
    for process in Path("/proc").iterdir():
        if not process.name.isdigit():
            continue
        try:
            for fd in (process / "fd").iterdir():
                try:
                    meta = fd.stat()  # Metadata only, never open the device.
                    if stat.S_ISCHR(meta.st_mode) and meta.st_rdev == target.st_rdev:
                        owners.append({"pid": int(process.name), "fd": fd.name,
                                       "target": os.readlink(fd)})
                except OSError as error:
                    if error.errno not in (errno.ENOENT, errno.ESRCH):
                        failures.append({"path": str(fd), "error": str(error)})
        except OSError as error:
            if error.errno not in (errno.ENOENT, errno.ESRCH):
                failures.append({"path": str(process), "error": str(error)})
    return owners, failures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    plan = {
        "connection": "one FX3 ConnectionRegistry::makeConnection; no retries",
        "library": str(LIBRARY), "serial": SERIAL,
        "unavoidable_effects": [
            "Factory discovery temporarily opens/closes USB descriptor handles before the one claimed FX3 connection.",
            "FX3 Open can send CMD_USB_FIFO_RST with payload 0x01 to reset bulk endpoints.",
            "Constructor reads identity and checks gateware versions; mismatch messages do not trigger an update.",
            "On legacy LimeSDR hardware <4 the installed constructor automatically initializes Si5351C; historical target hardware is 4. Actual hardware identity is recorded after open.",
        ],
        "constructor_packet_logging": "Unavailable until the constructor returns; constructor effects are identified from inspected source/runtime identity, not a complete bus trace.",
        "post_open_reads": ["device identity", "BBIC 0x0000, 0x0001, 0x0002, 0x0003", "raw BBIC 0x00c8"],
        "exclusions": ["LMS_Init", "LMS_Open/DetectRefClk", "Soapy device creation", "clock selection", "ADF4002 programming", "RF settings", "capture/stream start", "firmware update"],
        "interpretation": "post-open raw observation only; no claim about untouched state or external lock without map/MUXOUT evidence",
    }
    if not args.run:
        print(json.dumps(plan, indent=2))
        return 0
    if args.output is None or not args.output.is_dir():
        parser.error("--run requires a prepared existing --output directory")
    out = args.output.resolve()
    report = {"utc": datetime.now(timezone.utc).isoformat(), "plan": plan,
              "owners": [], "scan_failures": [], "diagnostic_started": False}

    def save():
        (out / "guard.json").write_text(json.dumps(report, indent=2) + "\n")

    try:
        if os.geteuid() != 0:
            raise RuntimeError("Requires host root metadata access; no attempt made")
        if Path("/proc/1/comm").read_text().strip() not in ("systemd", "init"):
            raise RuntimeError("Host PID view not established")
        if hashlib.sha256(LIBRARY.read_bytes()).hexdigest() != LIBRARY_SHA256:
            raise RuntimeError("Inspected LimeSuite library changed")
        binary = out / "read_lime_reference_once"
        manifest = json.loads((out / "build_manifest.json").read_text())
        if hashlib.sha256(binary.read_bytes()).hexdigest() != manifest["binary_sha256"]:
            raise RuntimeError("Prepared diagnostic binary changed")
        devices, errors = usb_devices(SERIAL)
        report["usb_devices"], report["usb_errors"] = devices, errors
        if errors or len(devices) != 1 or devices[0].get("node_error"):
            raise RuntimeError("Unique accessible USB target not established")
        device = devices[0]
        node = Path(device["node"])
        before = node.stat()
        sysfs = Path(device["sysfs"])
        kernel_drivers = [str(p / "driver") for p in sysfs.parent.glob(sysfs.name + ":*")
                          if (p / "driver").exists()]
        report["kernel_interface_drivers"] = kernel_drivers
        if kernel_drivers:
            raise RuntimeError("USB interface already has a driver; stopping")
        report["owners"], report["scan_failures"] = ownership_scan(node)
        report["ownership_scan_completed_utc"] = datetime.now(timezone.utc).isoformat()
        if report["owners"] or report["scan_failures"]:
            raise RuntimeError("SDR owner found or ownership scan incomplete; stopping")
        after = node.stat()
        if (before.st_ino, before.st_rdev, before.st_ctime_ns) != (after.st_ino, after.st_rdev, after.st_ctime_ns):
            raise RuntimeError("USB node changed during ownership check")
        if (sysfs / "serial").read_text().strip() != SERIAL:
            raise RuntimeError("USB serial changed")
        # Reserve the single attempt before launching; never reuse this directory.
        with (out / "attempt_reserved").open("x") as marker:
            marker.write(datetime.now(timezone.utc).isoformat() + "\n")
        report["diagnostic_started"] = True
        save()
        # No timeout/signal/automatic retry: the helper uses normal USB timeouts
        # and releases its connection through RAII on all ordinary error paths.
        with (out / "diagnostic.jsonl").open("x") as stdout, (out / "diagnostic.stderr").open("x") as stderr:
            result = subprocess.run([str(binary), "--run-authorized-once"],
                                    stdout=stdout, stderr=stderr, check=False,
                                    env={"PATH": "/usr/bin:/bin", "LANG": "C", "TZ": "UTC"})
        report["returncode"] = result.returncode
        report["finished_utc"] = datetime.now(timezone.utc).isoformat()
        save()
        print(json.dumps(report, indent=2))
        print((out / "diagnostic.jsonl").read_text(), end="")
        print((out / "diagnostic.stderr").read_text(), end="", file=sys.stderr)
        return result.returncode
    except (OSError, ValueError, RuntimeError, KeyError) as error:
        report["stopped_reason"] = str(error)
        save()
        print(json.dumps(report, indent=2))
        return 10


if __name__ == "__main__":
    raise SystemExit(main())
