"""gnss-sdr parameter sweep v2 — sample rate, taps, doppler step."""
import argparse
import os
import re
import signal
import subprocess
import time
from itertools import product
from pathlib import Path

CONFIGS_DIR = Path.home() / "gnss" / "configs"
OUTPUT_DIR = Path.home() / "gnss" / "output"
SWEEP_DIR = OUTPUT_DIR / "sweep_v2_runs"
BASE_TEMPLATE = CONFIGS_DIR / "limesdr_l1.conf"


def render_config(out_path, sample_rate, n_taps, doppler_step):
    text = BASE_TEMPLATE.read_text()
    sr_str = str(int(sample_rate))
    overrides = {
        r"^GNSS-SDR\.internal_fs_sps=.*$": f"GNSS-SDR.internal_fs_sps={sr_str}",
        r"^SignalSource\.sampling_frequency=.*$": f"SignalSource.sampling_frequency={sr_str}",
        r"^InputFilter\.sampling_frequency=.*$": f"InputFilter.sampling_frequency={sr_str}",
        r"^InputFilter\.number_of_taps=.*$": f"InputFilter.number_of_taps={n_taps}",
        r"^Acquisition_1C\.threshold=.*$": "Acquisition_1C.threshold=2.0",
        r"^Acquisition_1C\.doppler_step=.*$": f"Acquisition_1C.doppler_step={doppler_step}",
        r"^Acquisition_1C\.coherent_integration_time_ms=.*$": "Acquisition_1C.coherent_integration_time_ms=1",
        r"^Acquisition_1C\.bit_transition_flag=.*$": "Acquisition_1C.bit_transition_flag=false",
    }
    for pattern, replacement in overrides.items():
        text, n = re.subn(pattern, replacement, text, flags=re.MULTILINE)
        if n == 0:
            text += f"\n{replacement}\n"
    if "use_CFAR_algorithm_flag" not in text:
        text += "\nAcquisition_1C.use_CFAR_algorithm_flag=true\n"
    else:
        text = re.sub(r"^Acquisition_1C\.use_CFAR_algorithm_flag=.*$",
                      "Acquisition_1C.use_CFAR_algorithm_flag=true",
                      text, flags=re.MULTILINE)
    out_path.write_text(text)


def run_one(config_path, log_path, duration_s):
    proc = subprocess.Popen(
        ["gnss-sdr", "--config_file", str(config_path)],
        stdout=open(log_path, "w"), stderr=subprocess.STDOUT,
        cwd=str(OUTPUT_DIR), preexec_fn=os.setsid,
    )
    try:
        proc.wait(timeout=duration_s)
    except subprocess.TimeoutExpired:
        os.killpg(os.getpgid(proc.pid), signal.SIGINT)
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            proc.wait()
    time.sleep(2)


def newest_internal_log():
    candidates = list(Path("/tmp").glob("gnss-sdr*.log.INFO.*"))
    return max(candidates, key=lambda p: p.stat().st_mtime) if candidates else None


def parse_results(stdout_log_path, internal_log_path, nmea_path):
    text = stdout_log_path.read_text(errors="ignore")
    tracking_starts = len(re.findall(r"Tracking of GPS", text))
    lock_losses = len(re.findall(r"Loss of lock", text))
    position_lines = len(re.findall(r"Position at", text))
    pos_acq, test_stats = 0, []
    if internal_log_path and internal_log_path.exists():
        for line in internal_log_path.read_text(errors="ignore").splitlines():
            if "positive acquisition" in line:
                pos_acq += 1
                m = re.search(r"test statistics value ([0-9.]+)", line)
                if m:
                    test_stats.append(float(m.group(1)))
    nmea_size = nmea_path.stat().st_size if nmea_path.exists() else 0
    avg_stat = sum(test_stats) / len(test_stats) if test_stats else 0.0
    max_stat = max(test_stats) if test_stats else 0.0
    return dict(tracking_starts=tracking_starts, lock_losses=lock_losses,
                position_lines=position_lines, positive_acquisitions=pos_acq,
                avg_test_stat=avg_stat, max_test_stat=max_stat, nmea_bytes=nmea_size)


def fmt_row(combo, r):
    return (f"sr={combo['sample_rate']/1e6:.0f}M taps={combo['n_taps']:>3} "
            f"dop={combo['doppler_step']:>3}Hz | acq={r['positive_acquisitions']:>4} "
            f"trk={r['tracking_starts']:>3} loss={r['lock_losses']:>3} "
            f"avg_ts={r['avg_test_stat']:>5.2f} max_ts={r['max_test_stat']:>5.2f} "
            f"nmea={r['nmea_bytes']:>4}B fix={r['position_lines']}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--quick", action="store_true")
    p.add_argument("--duration", type=int, default=120)
    args = p.parse_args()
    SWEEP_DIR.mkdir(parents=True, exist_ok=True)

    if args.quick:
        grid = dict(sample_rate=[2e6, 4e6], n_taps=[51, 101], doppler_step=[250])
    else:
        grid = dict(sample_rate=[2e6, 4e6, 5e6], n_taps=[51, 101, 151],
                    doppler_step=[100, 250, 500])

    keys = list(grid.keys())
    combos = [dict(zip(keys, v)) for v in product(*(grid[k] for k in keys))]

    print(f"sweep v2: {len(combos)} combos x {args.duration}s = ~{len(combos) * (args.duration + 12) / 60:.1f} min total")
    print(f"using base template: {BASE_TEMPLATE}\n")

    results = []
    for i, combo in enumerate(combos, 1):
        tag = f"sr{int(combo['sample_rate']/1e6)}M_taps{combo['n_taps']}_dop{combo['doppler_step']}"
        config_path = SWEEP_DIR / f"cfg_{tag}.conf"
        stdout_path = SWEEP_DIR / f"stdout_{tag}.log"
        nmea_path = OUTPUT_DIR / "gnss_pvt.nmea"
        if nmea_path.exists():
            nmea_path.unlink()
        render_config(config_path, sample_rate=combo["sample_rate"],
                      n_taps=combo["n_taps"], doppler_step=combo["doppler_step"])
        print(f"[{i}/{len(combos)}] running {tag} ...", flush=True)
        run_one(config_path, stdout_path, args.duration)
        internal_log = newest_internal_log()
        r = parse_results(stdout_path, internal_log, nmea_path)
        print("    " + fmt_row(combo, r))
        results.append((combo, r))

    print("\n=== SORTED BY (fix, nmea, tracking) ===")
    results.sort(key=lambda x: (x[1]["position_lines"], x[1]["nmea_bytes"],
                                x[1]["tracking_starts"]), reverse=True)
    for combo, r in results:
        print(fmt_row(combo, r))


if __name__ == "__main__":
    main()
