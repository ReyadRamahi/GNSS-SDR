#!/usr/bin/env python3
"""Inspect decoded GPS issue-of-data fields from file replay via localhost only."""
import argparse
import json
from pathlib import Path
import socket
import subprocess
import tempfile


def protobuf_fields(data):
    """Read the scalar/string fields in the locally installed nav_message.proto."""
    pos = 0

    def varint():
        nonlocal pos
        value = shift = 0
        while pos < len(data) and shift < 70:
            byte = data[pos]
            pos += 1
            value |= (byte & 127) << shift
            if byte < 128:
                return value
            shift += 7
        raise ValueError("Malformed protobuf varint")

    fields = {}
    while pos < len(data):
        tag = varint()
        number, wire = tag >> 3, tag & 7
        if wire == 0:
            fields[number] = varint()
        elif wire == 2:
            length = varint()
            if pos + length > len(data):
                raise ValueError("Truncated protobuf string")
            fields[number] = data[pos:pos + length].decode("ascii")
            pos += length
        else:
            raise ValueError(f"Unexpected wire type {wire}")
    return fields


def decode(data):
    fields = protobuf_fields(data)
    bits = fields.get(5, "")
    if fields.get(1) != "G" or len(bits) != 300 or set(bits) - {"0", "1"}:
        raise ValueError("Expected GPS LNAV 300-bit subframe")

    def unsigned(*slices):
        return int("".join(bits[start - 1:start - 1 + length] for start, length in slices), 2)

    record = {"prn": fields[3], "subframe": unsigned((50, 3)),
              "tow_next_subframe_s": unsigned((31, 17)) * 6,
              "nav_message": bits}
    if record["subframe"] == 1:
        record.update(iodc=unsigned((83, 2), (211, 8)), health=unsigned((77, 6)))
    elif record["subframe"] == 2:
        record["iode_sf2"] = unsigned((61, 8))
    elif record["subframe"] == 3:
        record["iode_sf3"] = unsigned((271, 8))
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    text = args.config.read_text()
    if "SignalSource.implementation=File_Signal_Source" not in text or "Osmosdr_Signal_Source" in text:
        parser.error("Only file-source replay is permitted")
    project = Path(__file__).resolve().parents[1]
    run = Path(tempfile.mkdtemp(prefix="nav_audit_", dir=project / "runs"))
    (run / "internal").mkdir()
    records = []
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as listener:
        listener.bind(("127.0.0.1", 0))
        listener.settimeout(0.2)
        port = listener.getsockname()[1]
        text += f"\nNavDataMonitor.enable_monitor=true\nNavDataMonitor.client_addresses=127.0.0.1\nNavDataMonitor.port={port}\n"
        (run / "config_used.conf").write_text(text)
        command = ["timeout", "--signal=INT", "--kill-after=10s", "180s", "gnss-sdr",
                   "--config_file=" + str(run / "config_used.conf"), "--log_dir=" + str(run / "internal")]
        print("Offline NAV audit:", run, flush=True)
        with (run / "run.log").open("w") as log:
            process = subprocess.Popen(command, cwd=run, stdout=log, stderr=subprocess.STDOUT)
            try:
                while True:
                    try:
                        data, _ = listener.recvfrom(65535)
                        records.append(decode(data))
                    except socket.timeout:
                        if process.poll() is not None:
                            break
                status = process.wait()
            finally:
                if process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
    (run / "nav_messages.json").write_text(json.dumps(records, indent=2) + "\n")
    summary = {}
    for prn in sorted({r["prn"] for r in records}):
        chosen = [r for r in records if r["prn"] == prn]
        summary[prn] = {key: sorted({r[key] for r in chosen if key in r})
                        for key in ["subframe", "iodc", "iode_sf2", "iode_sf3", "health"]}
        summary[prn]["messages"] = len(chosen)
    result = {"exit_status": status, "nav_messages": len(records), "satellites": summary}
    (run / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
    if status or not records:
        raise SystemExit("NAV audit failed or received no monitor messages; inspect run.log")


if __name__ == "__main__":
    main()
