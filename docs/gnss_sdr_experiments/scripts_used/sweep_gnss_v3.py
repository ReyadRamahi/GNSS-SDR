"""gnss-sdr parameter sweep v3 - around official LimeSDR reference."""
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
SWEEP_DIR = OUTPUT_DIR / "sweep_v3_runs"
SERIAL = "0009061C01502715"

CONFIG_TEMPLATE = """[GNSS-SDR]

GNSS-SDR.internal_fs_sps={sr}

SignalSource.implementation=Osmosdr_Signal_Source
SignalSource.item_type=gr_complex
SignalSource.sampling_frequency={sr}
SignalSource.freq=1575420000
SignalSource.gain=50
SignalSource.AGC_enabled={agc}
SignalSource.samples=0
SignalSource.repeat=false
SignalSource.enable_throttle_control=false
SignalSource.dump=false
SignalSource.osmosdr_args=soapy=0,driver=lime,serial={serial},antenna=LNAW

SignalConditioner.implementation=Signal_Conditioner
DataTypeAdapter.implementation=Pass_Through

InputFilter.implementation=Freq_Xlating_Fir_Filter
InputFilter.input_item_type=gr_complex
InputFilter.output_item_type=gr_complex
InputFilter.taps_item_type=float
InputFilter.number_of_taps={taps}
InputFilter.number_of_bands=2
InputFilter.band1_begin=0.0
InputFilter.band1_end={band1_end}
InputFilter.band2_begin={band2_begin}
InputFilter.band2_end=1.0
InputFilter.ampl1_begin=1.0
InputFilter.ampl1_end=1.0
InputFilter.ampl2_begin=0.0
InputFilter.ampl2_end=0.0
InputFilter.band1_error=1.0
InputFilter.band2_error=1.0
InputFilter.filter_type=bandpass
InputFilter.grid_density=16
InputFilter.sampling_frequency={sr}
InputFilter.IF=0
InputFilter.decimation_factor=1
InputFilter.dump=false

Resampler.implementation=Pass_Through

Channels_1C.count=8
Channels.in_acquisition=1
Channel.signal=1C

Acquisition_1C.implementation=GPS_L1_CA_PCPS_Acquisition
Acquisition_1C.item_type=gr_complex
Acquisition_1C.coherent_integration_time_ms=1
Acquisition_1C.threshold=2.5
Acquisition_1C.doppler_max=10000
Acquisition_1C.doppler_step=250
Acquisition_1C.bit_transition_flag=false
Acquisition_1C.max_dwells=1
Acquisition_1C.dump=false

Tracking_1C.implementation=GPS_L1_CA_DLL_PLL_Tracking
Tracking_1C.item_type=gr_complex
Tracking_1C.pll_bw_hz=40.0
Tracking_1C.dll_bw_hz=2.0
Tracking_1C.pll_bw_narrow_hz=2.0
Tracking_1C.dll_bw_narrow_hz=0.25
Tracking_1C.fll_bw_hz=10.0
Tracking_1C.enable_fll_pull_in=true
Tracking_1C.early_late_space_chips=0.5
Tracking_1C.dump=false

TelemetryDecoder_1C.implementation=GPS_L1_CA_Telemetry_Decoder
TelemetryDecoder_1C.dump=false

Observables.implementation=Hybrid_Observables
Observables.dump=false

PVT.implementation=RTKLIB_PVT
PVT.positioning_mode=Single
PVT.iono_model=Broadcast
PVT.trop_model=Saastamoinen
PVT.output_rate_ms=100
PVT.display_rate_ms=500
PVT.elevation_mask=10
PVT.dump=false
PVT.flag_nmea_tty_port=false
PVT.nmea_dump_filename=./gnss_pvt.nmea
PVT.flag_rtcm_server=false
PVT.flag_rtcm_tty_port=false
PVT.rinex_version=2
PVT.flag_rinex_multi_freq=false
"""


def render_config(out_path, sample_rate, taps, band1_end, agc):
    band2_begin = round(band1_end + 0.10, 2)
    if band2_begin >= 1.0:
        band2_begin = 0.99
    text = CONFIG_TEMPLATE.format(
        sr=int(sample_rate), taps=taps, band1_end=band1_end,
        band2_begin=band2_begin,
        agc="true" if agc else "false", serial=SERIAL,
    )
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
                avg_test_stat=avg_stat, max_test_stat=max_stat,
                nmea_bytes=nmea_size)


def fmt_row(combo, r):
    return (f"sr={combo['sample_rate']/1e6:>2.0f}M "
            f"taps={combo['taps']:>3} band1={combo['band1_end']:.2f} "
            f"agc={'T' if combo['agc'] else 'F'} | "
            f"acq={r['positive_acquisitions']:>4} "
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
        grid = dict(sample_rate=[2e6, 5e6], taps=[51], band1_end=[0.45], agc=[False])
    else:
        grid = dict(sample_rate=[2e6, 5e6, 10e6], taps=[51, 101],
                    band1_end=[0.45, 0.7, 0.9], agc=[True, False])

    keys = list(grid.keys())
    combos = [dict(zip(keys, v)) for v in product(*(grid[k] for k in keys))]

    print(f"sweep v3: {len(combos)} combos x {args.duration}s = ~{len(combos) * (args.duration + 12) / 60:.1f} min total\n")

    results = []
    for i, combo in enumerate(combos, 1):
        tag = (f"sr{int(combo['sample_rate']/1e6)}M_taps{combo['taps']}"
               f"_band{int(combo['band1_end']*100)}_agc{'T' if combo['agc'] else 'F'}")
        config_path = SWEEP_DIR / f"cfg_{tag}.conf"
        stdout_path = SWEEP_DIR / f"stdout_{tag}.log"
        nmea_path = OUTPUT_DIR / "gnss_pvt.nmea"
        if nmea_path.exists():
            nmea_path.unlink()
        render_config(config_path, sample_rate=combo["sample_rate"],
                      taps=combo["taps"], band1_end=combo["band1_end"],
                      agc=combo["agc"])
        print(f"[{i}/{len(combos)}] running {tag} ...", flush=True)
        run_one(config_path, stdout_path, args.duration)
        internal_log = newest_internal_log()
        r = parse_results(stdout_path, internal_log, nmea_path)
        print("    " + fmt_row(combo, r))
        results.append((combo, r))

    print("\n=== SORTED BY (fix, max_test_stat, tracking) ===")
    results.sort(key=lambda x: (x[1]["position_lines"], x[1]["max_test_stat"],
                                x[1]["tracking_starts"]), reverse=True)
    for combo, r in results:
        print(fmt_row(combo, r))


if __name__ == "__main__":
    main()
