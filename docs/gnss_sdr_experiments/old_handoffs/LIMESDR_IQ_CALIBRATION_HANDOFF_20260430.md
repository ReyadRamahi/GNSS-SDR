# Handoff: IQ Calibration Experiment

## Background

Raw IQ analysis of the LimeSDR capture revealed two critical hardware problems:

1. **IQ amplitude imbalance: 128%** — the Q channel has 4.6x more power than the I channel
2. **DC spike: 32 dB above noise floor** — severe zero-IF contamination

The IQ imbalance is the most serious finding. It corrupts the PLL discriminator output on every 1ms integration period, which explains why the tracking treadmill (acquire → start → lose lock → repeat) has persisted across every software experiment. No loop bandwidth, gain, or frequency offset change can fix a corrupted discriminator input.

This experiment tests whether triggering hardware DC/IQ calibration on the LMS7002M fixes the imbalance.

Reference figures showing the problem:

- `scripts_used/matlab_analysis/figures/TrackingLoopSim.fig` — PLL saturated throughout, 25.6% lock fraction
- `scripts_used/matlab_analysis/figures/CN0Summary.fig` — all PRNs 33–38 dB-Hz, marginal

---

## Before You Start — Free Disk Space

The disk is at 100% (91 MB free). The IQ capture file is ~160 MB. You must free space first or the capture will fail.

Check where the space is:

```bash
du -sh /home/rrama28/gnss/runs/ 2>/dev/null
du -sh /tmp/
du -sh /var/log/
ls -lh ~/GSDR* ~/pvt_dat_* ~/*.gpx ~/*.kml ~/*.nmea ~/*.dat 2>/dev/null
```

Safe to delete:

- Large GNSS-SDR output files: `GSDR*`, `pvt_dat_*`, `*.gpx`, `*.kml`, `*.nmea`
- Raw IQ capture `.dat` files — they are in `.gitignore` and not in the repo
- Old run directories that have already been summarized

Verify you have at least 500 MB free before continuing:

```bash
df -h /
```

---

## Step 1 — Upload The Config

The config file is in the repo at:

```
configs_used/f9t_lime_current/lime_iq_capture_calibrated.conf
```

Upload it to hft02 at:

```
/home/alexgu2/gnss/configs/lime_iq_capture_calibrated.conf
```

Key difference from the standard IQ capture config — the `osmosdr_args` line:

```ini
SignalSource.osmosdr_args=soapy=0,driver=lime,serial=0009061C01502715,antenna=LNAW,skipCal=false,CALIBRATE=2500000,dc_offset_mode=2
```

- `skipCal=false` — do not skip the built-in calibration routine
- `CALIBRATE=2500000` — trigger LMS7002M DC/IQ calibration at 2.5 MHz bandwidth
- `dc_offset_mode=2` — enable automatic DC offset tracking after calibration

---

## Step 2 — Run The Capture

```bash
RUN_ID=$(date -u +%Y%m%d_%H%M%S)
RUN_DIR=/home/alexgu2/gnss/runs/iq_capture_calibrated_${RUN_ID}

echo "RUN_DIR: $RUN_DIR"

mkdir -p "$RUN_DIR"
cd "$RUN_DIR"
gnss-sdr --config_file=/home/alexgu2/gnss/configs/lime_iq_capture_calibrated.conf
```

GNSS-SDR will run for 10 seconds and exit automatically. Watch the startup output. If calibration fired you may see a line like:

```
[INFO] Calibrating RX...
```

The output file will be at:

```
/home/alexgu2/gnss/runs/iq_capture_calibrated_YYYYMMDD_HHMMSS/lime_iq_capture_calibrated.dat
```

It will be approximately 160 MB. Download it to your local machine.

---

## Step 3 — Run The MATLAB Analysis

You need:

- `05_iq_constellation.m` from `scripts_used/matlab_analysis/`
- `lime_iq_capture_calibrated.dat` downloaded from hft02

Open `05_iq_constellation.m` and change line 8 from:

```matlab
IQ_FILE = 'lime_iq_capture.dat';
```

to:

```matlab
IQ_FILE = 'lime_iq_capture_calibrated.dat';
```

Run the script. It will produce three figures and print statistics to the terminal.

---

## Step 4 — Read The Results

The key number is **IQ imbalance** in the terminal output. Compare against the pre-calibration baseline:

| Metric | Pre-calibration | Target |
| --- | --- | --- |
| IQ imbalance | 128.89% | < 5% |
| DC offset above floor | HIGH | < 10% of noise std |
| Power ratio I/Q | -13.5 dB | 0 dB (equal) |

### If IQ imbalance drops below 5%

Calibration worked. Proceed immediately to the full tracking experiment using:

```
configs_used/f9t_lime_current/lime_gain20_iqcorrected_ephem_6ch_t26.conf
```

Upload to hft02, run as a standard GNSS-SDR tracking run, and watch for `tracking bit synchronization locked` in the log — that would be the first breakthrough.

### If IQ imbalance is unchanged (~128%)

The `CALIBRATE` arg was silently ignored by the gr-osmosdr/SoapyLMS7 driver version on hft02. Escalate to the professor — the LimeSuite version may need updating, or direct LimeSuite calibration commands need to be run before launching GNSS-SDR.

---

## What To Report Back

After running the MATLAB script, record and share:

- IQ imbalance percentage
- DC offset level (HIGH / MODERATE / OK)
- Power ratio I/Q in dB
- Whether calibration message appeared in GNSS-SDR startup output
- Screenshots of the constellation figure and histograms

The constellation plot should change from an ellipse (current — Q much wider than I) to a circle (healthy — I and Q equal) if calibration worked.