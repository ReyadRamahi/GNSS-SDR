# Command-line analysis

Run these tools from the repository root with Python module syntax. They reuse the library in `gnss_sdr/`; no manual import-path setup is needed. Install dependencies from `server/requirements.txt` first.

## Receiver benchmark

```bash
mkdir -p outputs
python -m tools.benchmark_gnss_sdr \
  --label 10Msps_usb3 \
  --rate-msps 10 \
  --transport usb3 \
  --log docs/gnss_sdr_experiments/results/logs/baseline_runs/lime_balanced_3min.log \
  --duration 180 \
  --output outputs/benchmark_results.md \
  --csv outputs/benchmark_results.csv
```

Optionally add `--nmea <recording.nmea>` for signal-strength and fix statistics. The tool appends one row per run; repeated labels are intentionally retained. Inspect options with `python -m tools.benchmark_gnss_sdr --help`.

## Multipath validation

Place your Google Smartphone Decimeter Challenge 2022 inputs under `data/kaggle/`, or pass any other local paths:

```bash
mkdir -p outputs
python -m tools.validate_multipath \
  --gnss-log data/kaggle/gnss_log.txt \
  --ground-truth data/kaggle/ground_truth.csv \
  --device-gnss data/kaggle/device_gnss.csv \
  --output outputs/validation_report.json \
  --max-epochs 200
```

Validation uses building footprints fetched from Overpass when available. Unit tests mock the network and use synthetic input files. Inspect options with `python -m tools.validate_multipath --help`.

See [the repository map](../docs/STRUCTURE.md) for renamed paths and [dataset setup](../data/README.md) for recordings. Historical hardware capture/refresh/MATLAB scripts live under `docs/gnss_sdr_experiments/scripts_used/` alongside their experiment notes.
