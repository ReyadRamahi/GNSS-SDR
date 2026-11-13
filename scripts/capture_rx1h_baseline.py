#!/usr/bin/env python3
"""One fixed RX0/LNAH capture. Hardware access requires --run."""

import argparse
import json
import math
from pathlib import Path

SERIAL = "0009061C01502715"
SOURCE_ARGS = f"numchan=1 soapy=0,driver=lime,serial={SERIAL},nchan=1"
RATE = 2_000_000
RATE_TOLERANCE_SPS = 1.0  # 0.5 ppm at 2 Msps; tolerate fractional-divider readback.
FREQUENCY = 1_574_920_000
MODULE = Path("/usr/lib/x86_64-linux-gnu/SoapySDR/modules0.8/libLMS7Support.so")
LIBRARY = Path("/lib/x86_64-linux-gnu/libLimeSuite.so.20.10-1")


def sample_rate_matches(actual_rate):
    return math.isclose(actual_rate, RATE, rel_tol=0.0, abs_tol=RATE_TOLERANCE_SPS)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="open/configure the radio and capture")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--seconds", type=int, choices=(30, 90), default=30, help="saved IQ duration; RF settings stay fixed")
    args = parser.parse_args()
    samples = RATE * args.seconds
    plan = {
        "source_args": SOURCE_ARGS,
        "rx_channel_index": 0,
        "reported_connector": "RX1_H",
        "antenna": "LNAH",
        "sample_rate_sps": RATE,
        "sample_rate_tolerance_sps": RATE_TOLERANCE_SPS,
        "center_frequency_hz": FREQUENCY,
        "gain_calls_db": {"set_gain": 15, "set_if_gain": 40, "set_bb_gain": 6},
        "gain_note": "Same call sequence as the most recent GNSS config, including rf_gain default 40. Historical total readback was 45 dB.",
        "bandwidth": "Driver initialization default; record readback; no bandwidth setter",
        "discard_initial_samples": RATE,
        "saved_samples": samples,
        "saved_duration_s": args.seconds,
        "expected_iq_bytes": samples * 8,
        "clock": "No explicit clock setter; initialization may affect prior state; external lock unverified",
        "driver_module": str(MODULE),
        "library": str(LIBRARY),
    }
    if not args.run:
        print(json.dumps(plan, indent=2))
        return
    if args.output is None or not args.output.is_dir():
        parser.error("--run requires an existing --output directory; use run_rx1h_baseline.sh")

    # Import/open only after the explicit hardware-access flag.
    import osmosdr
    import numpy as np
    from gnuradio import blocks, gr

    output = args.output.resolve()
    (output / "requested.json").write_text(json.dumps(plan, indent=2) + "\n")
    source = osmosdr.source(args=SOURCE_ARGS)

    # Confirm process-local isolation before applying the requested settings.
    maps = Path("/proc/self/maps").read_text()
    (output / "loaded_libraries.txt").write_text(maps)
    paths = {Path(line.split()[-1]).resolve() for line in maps.splitlines() if len(line.split()) >= 6 and line.split()[-1].startswith("/")}
    modules = {p for p in paths if p.name == "libLMS7Support.so"}
    libraries = {p for p in paths if p.name.startswith("libLimeSuite.so.")}
    if modules != {MODULE.resolve()} or libraries != {LIBRARY.resolve()}:
        raise RuntimeError(f"Unexpected Lime modules/libraries: {modules}, {libraries}; capture aborted")
    if source.get_num_channels() != 1:
        raise RuntimeError("Expected exactly one source channel")

    def readback():
        return {
            "source_channels": source.get_num_channels(),
            "rx_channel_index": 0,
            "antenna": source.get_antenna(0),
            "sample_rate_sps": source.get_sample_rate(),
            "center_frequency_hz": source.get_center_freq(0),
            "gain_db": source.get_gain(0),
            "gain_stages_db": {name: source.get_gain(name, 0) for name in source.get_gain_names(0)},
            "bandwidth_hz": source.get_bandwidth(0),
        }

    (output / "after_open.json").write_text(json.dumps(readback(), indent=2) + "\n")
    source.set_sample_rate(RATE)
    source.set_center_freq(FREQUENCY, 0)
    source.set_gain_mode(False, 0)
    source.set_gain(15, 0)
    source.set_if_gain(40, 0)
    source.set_bb_gain(6, 0)
    source.set_antenna("LNAH", 0)
    before = readback()
    (output / "before_capture.json").write_text(json.dumps(before, indent=2) + "\n")
    print("Readback before capture:", json.dumps(before), flush=True)
    if before["antenna"] != "LNAH":
        raise RuntimeError(f"Expected LNAH; antenna readback is {before['antenna']!r}")
    if not sample_rate_matches(before["sample_rate_sps"]):
        raise RuntimeError(f"Sample-rate readback {before['sample_rate_sps']} differs from {RATE} by more than {RATE_TOLERANCE_SPS} samples/s or is non-finite")
    if abs(before["center_frequency_hz"] - FREQUENCY) > 100:
        raise RuntimeError("Frequency readback differs by more than 100 Hz")
    if abs(before["gain_db"] - 45) > 1:
        raise RuntimeError("Gain readback differs from historical 45 dB by more than 1 dB")

    iq_file = output / "rx1h.cf32"
    graph = gr.top_block()
    skip = blocks.skiphead(gr.sizeof_gr_complex, RATE)
    head = blocks.head(gr.sizeof_gr_complex, samples)
    sink = blocks.file_sink(gr.sizeof_gr_complex, str(iq_file), False)
    graph.connect(source, skip, head, sink)
    try:
        graph.start()
        graph.wait()
    finally:
        graph.stop()
        graph.wait()
        sink.close()

    after = readback()
    (output / "after_capture.json").write_text(json.dumps(after, indent=2) + "\n")
    size = iq_file.stat().st_size
    stats = []
    if size >= 8 * 65536:
        iq = np.memmap(iq_file, dtype=np.complex64, mode="r")
        for offset in [0, max(0, len(iq) // 2 - 32768), len(iq) - 65536]:
            window = np.asarray(iq[offset:offset + 65536])
            stats.append({"offset_samples": offset, "finite": bool(np.isfinite(window).all()),
                          "std_i": float(window.real.std()), "std_q": float(window.imag.std()),
                          "rms": float(np.sqrt(np.mean(np.abs(window) ** 2)))})
    passed = (size == samples * 8 and after["antenna"] == "LNAH"
              and sample_rate_matches(after["sample_rate_sps"])
              and abs(after["center_frequency_hz"] - FREQUENCY) <= 100
              and abs(after["gain_db"] - before["gain_db"]) <= 1
              and len(stats) == 3
              and all(w["finite"] and w["std_i"] > 0 and w["std_q"] > 0 for w in stats))
    summary = {"path_and_sample_checks_passed": passed, "iq_bytes": size,
               "sampled_windows": stats,
               "limitation": "Readback and nonzero IQ do not establish GNSS reception, stream continuity, or external-reference lock. Inspect run.log for driver errors."}
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2), flush=True)
    if not passed:
        raise RuntimeError("Baseline path/sample checks failed")


if __name__ == "__main__":
    main()
