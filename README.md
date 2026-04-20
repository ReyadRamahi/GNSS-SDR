# IE 421 Group 16 Project

## Large Dataset Setup

This repo does not store the GNSS data files in Git because they are too large for GitLab. Each teammate needs to download them locally before running the parser integration tests.

Datasets:

- CTTC Spain GPS L1 C/A: https://sourceforge.net/projects/gnss-sdr/files/data/2013_04_04_GNSS_SIGNAL_at_CTTC_SPAIN.tar.gz/download
- LimeSDR GPS L1: https://sdr.ion.org/LimeSDR/LimeSDR_Bands-L1.int16

Expected local paths after download and extraction:

- `CTTC_GPS/2013_04_04_GNSS_SIGNAL_at_CTTC_SPAIN/gnss_pvt.nmea`
- `LimeSDR_GPS/LimeSDR_Bands-L1.int16`

The `.gitignore` intentionally excludes `.nmea`, `.dat`, `.int16`, and archive files so these datasets stay local.

## Parser Tests

The NMEA parser lives in `nmea_parser.py`.

Run the test suite with:

```bash
pytest -q
```

Test behavior:

- Unit tests for coordinate conversion and sentence parsing always run.
- Full-file integration tests run only if `CTTC_GPS/2013_04_04_GNSS_SIGNAL_at_CTTC_SPAIN/gnss_pvt.nmea` exists locally.
- If that file is missing, pytest skips the integration tests with a clear message instead of failing.

## Repository Notes

- Large raw GNSS data files are local-only dependencies.
- Generated Python cache files should not be committed.

## GitLab Reference

For the standard GitLab starter README/checklist, see:

- https://docs.gitlab.com/user/project/repository/files/gitlab_readme/
