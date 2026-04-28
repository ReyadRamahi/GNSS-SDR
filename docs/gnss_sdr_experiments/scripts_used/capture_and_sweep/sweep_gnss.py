"""gnss-sdr parameter sweep."""
import argparse
import os
import re
import shutil
import signal
import subprocess
import time
from itertools import product
from pathlib import Path

CONFIGS_DIR = Path.home() / "gnss" / "configs"
OUTPUT_DIR = Path.home() / "gnss" / "output"
SWEEP_DIR = OUTPUT_DIR / "sweep_runs"
BASE_TEMPLATE = CONFIGS_DIR / "limesdr_l1.conf"


def render_config(out_path, threshold, coherent_ms, bit_transition, pll_bw, dll_bw, n_taps):
    text = BASE_TEMPLATE.read_text()
    overrides = {
        r"^Acquisition_1C\.threshold=.*$": f"Acquisition_1C.threshold={threshold}",
        r"^Acquisition_1C\.coherent_integration_time_ms=.*$": f"Acquisition_1C.coherent_integration_time_ms={coherent_ms}",
        r"^Acquisition_1C\.bit_transition_flag=.*$": f"Acquisition_1C.bit_transition_flag={'true' if bit_transition else 'false'}",
        r"^Tracking_1C\.pll_bw_hz=.*$": f"Tracking_1C.pll_bw_hz={pll_bw}",
        r"^Tracking_1C\.dll_bw_hz=.*$": f"Tracking_1C.dll_bw_hz={dll_bw}",
        r"^InputFilter\.number_of_taps=.*$": f"InputFilter.number_of_taps={n_taps}",
    }
    for pattern, replacement in overrides.items():
        text, n = re.subn(pattern, replacement, text, flags=re.MULTILINE)
        if n == 0:
            text += f"\n{replacement}\n"
    out_path.write_text(text)


def run_one(config_path, log_path, duration_s):
    proc = subprocess.Popen(
        ["gnss-sdr", "--config_file", str(config_path)],
        stdout=open(log_path, "w"),
        stderr=subprocess.STDOUT,
        cwd=str(OUTPUT_DIR),
        preexec_fn=os.setsid,
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
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


def parse_results(stdout_log_path, internal_log_path, nmea_path):
    text = stdout_log_path.read_text(errors="ignore")
    tracking_starts = len(re.findall(r"Tracking of GPS", text))
    lock_losses = len(re.findall(r"Loss of lock", text))
    position_lines = len(re.findall(r"Position at", text))
    pos_acq = 0
    test_stats = []
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
    return dict(
        tracking_starts=tracking_starts, lock_losses=lock_losses,
        position_lines=position_lines, positive_acquisitions=pos_acq,
        avg_test_stat=avg_stat, max_test_stat=max_stat, nmea_bytes=nmea_size,
    )


def score(r):
    return (r["position_lines"] * 1000 + min(r["nmea_bytes"], 100) * 10
            + r["tracking_starts"] - r["lock_losses"] * 0.5
            + r["avg_test_stat"] * 5)


def fmt_row(combo, r):
    return (f"thr={combo['threshold']:>4} coh={combo['coherent_ms']:>2}ms "
            f"bit={'T' if combo['bit_transition'] else 'F'} "
            f"pll={combo['pll_bw']:>4} dll={combo['dll_bw']:>4} "
            f"taps={combo['n_taps']:>3} | acq={r['positive_acquisitions']:>4} "
            f"trk={r['tracking_starts']:>3} loss={r['lock_losses']:>3} "
            f"avg_ts={r['avg_test_stat']:>5.2f} max_ts={r['max_test_stat']:>5.2f} "
            f"nmea={r['nmea_bytes']:>4}B fix={r['position_lines']}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--quick", action="store_true")
    p.add_argument("--duration", type=int, default=180)
    args = p.parse_args()
    SWEEP_DIR.mkdir(parents=True, exist_ok=True)

    if args.quick:
        grid = dict(threshold=[2.0, 2.5], coherent_ms=[1, 4],
                    bit_transition=[None], pll_bw=[30], dll_bw=[2.0], n_taps=[51])
    else:
        grid = dict(threshold=[2.0, 2.2, 2.4, 2.6], coherent_ms=[1], 
                    bit_transition=[None], pll_bw=[15, 25, 35, 50],
                    dll_bw=[1.0, 2.0, 3.0], n_taps=[51])
    keys = list(grid.keys())
    combos = []
    for values in product(*(grid[k] for k in keys)):
        combo = dict(zip(keys, values))
        combo["bit_transition"] = combo["coherent_ms"] >= 4
        combos.append(combo)

    print(f"sweep: {len(combos)} combos x {args.duration}s = ~{len(combos) * (args.duration + 10) / 60:.1f} min total")
    print(f"using base template: {BASE_TEMPLATE}\n")

    results = []
    for i, combo in enumerate(combos, 1):
        tag = f"thr{combo['threshold']}_coh{combo['coherent_ms']}_pll{combo['pll_bw']}_dll{combo['dll_bw']}_t{combo['n_taps']}"
        config_path = SWEEP_DIR / f"cfg_{tag}.conf"
        stdout_path = SWEEP_DIR / f"stdout_{tag}.log"
        nmea_path = OUTPUT_DIR / "gnss_pvt.nmea"
        if nmea_path.exists():
            nmea_path.unlink()
        render_config(config_path, threshold=combo["threshold"],
                      coherent_ms=combo["coherent_ms"], bit_transition=combo["bit_transition"],
                      pll_bw=combo["pll_bw"], dll_bw=combo["dll_bw"], n_taps=combo["n_taps"])
        print(f"[{i}/{len(combos)}] running {tag} ...", flush=True)
        run_one(config_path, stdout_path, args.duration)
        internal_log = newest_internal_log()
        r = parse_results(stdout_path, internal_log, nmea_path)
        print("    " + fmt_row(combo, r))
        results.append((combo, r))

    print("\n=== SORTED BY SCORE ===")
    results.sort(key=lambda x: score(x[1]), reverse=True)
    for combo, r in results:
        print(fmt_row(combo, r))


if __name__ == "__main__":
    main()
