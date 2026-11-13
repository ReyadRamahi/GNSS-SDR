#!/usr/bin/env python3
"""Prepared idle clock test. Default is a plan; --execute requires user approval.

The execute path checks host ownership immediately before one FX3 connection.
It programs ADF digital lock detect, samples idle status, and returns to a
documented DAC baseline on the same connection. No RF setup or stream start.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys

sys.dont_write_bytecode = True
from inspect_lime_owner import usb_devices
from run_lime_reference_once import ownership_scan, SERIAL


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="run ONLY after approval of this prepared test")
    parser.add_argument("--output", type=Path, required=True, help="prepared directory containing the reviewed binary and manifest")
    args = parser.parse_args()
    out = args.output.resolve()
    manifest = json.loads((out / "build_manifest.json").read_text())
    for name, digest in manifest["files_sha256"].items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest() != digest:
            raise RuntimeError(f"Prepared file changed: {name}; stop for review")
    binary = out / "lime_external_reference_test"
    if not args.execute:
        print((out / "plan.jsonl").read_text(), end="")
        print("Preparation only: no connection, programming, sampling or baseline write performed.")
        return 0
    report = {"utc": datetime.now(timezone.utc).isoformat(), "diagnostic_started": False,
              "owners": [], "scan_failures": [], "one_connection": True,
              "return_baseline": "pretest reported DAC code in DAC-control mode; not exact unknown prior state"}

    def save():
        (out / "guard.json").write_text(json.dumps(report, indent=2) + "\n")

    try:
        if os.geteuid() != 0:
            raise RuntimeError("Host-root access is needed for the ownership check")
        if Path("/proc/1/comm").read_text().strip() not in ("systemd", "init"):
            raise RuntimeError("Host PID view not established")
        devices, errors = usb_devices(SERIAL)
        report["usb_devices"], report["usb_errors"] = devices, errors
        if errors or len(devices) != 1 or devices[0].get("node_error"):
            raise RuntimeError("Unique accessible USB target not established")
        node = Path(devices[0]["node"])
        before = node.stat()
        sysfs = Path(devices[0]["sysfs"])
        drivers = [str(p / "driver") for p in sysfs.parent.glob(sysfs.name + ":*")
                   if (p / "driver").exists()]
        report["kernel_interface_drivers"] = drivers
        if drivers:
            raise RuntimeError("USB interface has a driver; stop")
        report["owners"], report["scan_failures"] = ownership_scan(node)
        report["ownership_scan_completed_utc"] = datetime.now(timezone.utc).isoformat()
        if report["owners"] or report["scan_failures"]:
            raise RuntimeError("Device owner found or ownership scan incomplete; stop")
        after = node.stat()
        if (before.st_ino, before.st_rdev, before.st_ctime_ns) != (after.st_ino, after.st_rdev, after.st_ctime_ns):
            raise RuntimeError("USB node changed during check")
        if (sysfs / "serial").read_text().strip() != SERIAL:
            raise RuntimeError("USB serial changed")
        with (out / "attempt_reserved").open("x") as marker:
            marker.write(datetime.now(timezone.utc).isoformat() + "\n")
        report["diagnostic_started"] = True
        save()
        child = None
        pending = []

        def forward(signum, _frame):
            # Do not terminate the launcher and orphan the child's cleanup.
            pending.append(signum)
            if child is not None and child.poll() is None:
                child.send_signal(signum)

        old_handlers = {sig: signal.signal(sig, forward) for sig in (signal.SIGINT, signal.SIGTERM)}
        try:
            with (out / "test.jsonl").open("x") as stdout, (out / "test.stderr").open("x") as stderr:
                child = subprocess.Popen([str(binary), "--execute-approved-idle-test"],
                                         stdout=stdout, stderr=stderr,
                                         env={"PATH": "/usr/bin:/bin", "LANG": "C", "TZ": "UTC"})
                for sig in pending:
                    if child.poll() is None:
                        child.send_signal(sig)
                report["returncode"] = child.wait()  # No timeout, forced kill or retry.
        finally:
            for sig, handler in old_handlers.items():
                signal.signal(sig, handler)
        report["forwarded_signals"] = pending
        report["finished_utc"] = datetime.now(timezone.utc).isoformat()
        report["owners_after_close"], report["scan_failures_after_close"] = ownership_scan(node)
        save()
        rows = [json.loads(line) for line in (out / "test.jsonl").read_text().splitlines()]
        report["summary"] = next((r for r in reversed(rows) if r.get("event") == "summary"), None)
        report["close_recorded"] = any(r.get("event") == "closed" for r in rows)
        save()
        print(json.dumps(report, indent=2))
        return report["returncode"]
    except (OSError, ValueError, RuntimeError, KeyError) as error:
        report["stopped_reason"] = str(error)
        save()
        print(json.dumps(report, indent=2))
        return 10


if __name__ == "__main__":
    raise SystemExit(main())
