# Datasets and receiver files

The repository tracks small reference outputs, assistance files, and receiver configs. Large IQ recordings and NMEA files are excluded by `.gitignore` and must be downloaded or produced locally.

## Expected local paths

```text
data/
├── CTTC_GPS/
│   └── 2013_04_04_GNSS_SIGNAL_at_CTTC_SPAIN/
│       ├── 2013_04_04_GNSS_SIGNAL_at_CTTC_SPAIN.conf   # Tracked file-source config
│       ├── 2013_04_04_GNSS_SIGNAL_at_CTTC_SPAIN.dat    # Local IQ recording
│       └── 2013_04_04_GNSS_SIGNAL_at_CTTC_SPAIN.nmea   # Local parsed replay output
├── LimeSDR_GPS/
│   ├── limesdr_gps.conf                               # Tracked file-source config
│   └── LimeSDR_Bands-L1.int16                         # Local IQ recording
└── kaggle/                                           # Optional local validation inputs
```

Sources:

- [CTTC Spain GPS L1 C/A recording](https://sourceforge.net/projects/gnss-sdr/files/data/2013_04_04_GNSS_SIGNAL_at_CTTC_SPAIN.tar.gz/download).
- [LimeSDR GPS L1 IQ recording](https://sdr.ion.org/LimeSDR/LimeSDR_Bands-L1.int16).
- Google Smartphone Decimeter Challenge 2022 inputs for the [multipath validation tool](../tools/README.md).

Extract/copy the CTTC data into the folder shown above. NMEA is receiver-generated output, not necessarily included in the raw IQ archive. If your run produces `gnss_pvt.nmea`, copy it to the full CTTC replay filename shown above to use the default replay endpoints and dataset integration tests.

## Running the tracked file-source configs

Launch GNSS-SDR from the repository root so relative input paths resolve:

```bash
gnss-sdr --config_file=data/CTTC_GPS/2013_04_04_GNSS_SIGNAL_at_CTTC_SPAIN/2013_04_04_GNSS_SIGNAL_at_CTTC_SPAIN.conf
# Or:
gnss-sdr --config_file=data/LimeSDR_GPS/limesdr_gps.conf
```

Both configs retain `PVT.nmea_dump_filename=./gnss_pvt.nmea`. The server tails that file at the repository root for live telemetry. Do not confuse this live file with the archived CTTC replay file inside `data/`.

If upgrading an older checkout, move local ignored raw files from root-level `CTTC_GPS/` and `LimeSDR_GPS/` into these new directories. Git only moves tracked files when applying a pulled commit; it cannot migrate teammates' ignored local datasets.

The [experiment archive](../docs/gnss_sdr_experiments/README.md) contains additional historical logs/configs with machine-specific paths. Use its workflow guidance to adapt those configs to your receiver.
