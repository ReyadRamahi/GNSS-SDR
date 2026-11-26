# UIUC Fintech Lab GNSS-SDR Project

A GPS software receiver experiment archive, a live and replay dashboard, and Python tools for analyzing GNSS recordings. Includes the IE 421 Group 16 receiver experiments.

## Start here

| Goal | Guide |
| --- | --- |
| See the latest receiver results | [LimeSDR experiment results](docs/gnss_sdr_experiments/EXPERIMENT_RESULTS.md) |
| Run the live fix-health dashboard | [Live receiver and dashboard setup](docker/gnss-sdr/README.md#live-fix-health-dashboard-on-linux) |
| Reproduce the offline GPS fix | [GNSS-SDR Docker replay](docker/gnss-sdr/README.md) |
| Run the dashboard or tests | [Local development guide](docs/DEVELOPMENT.md) |
| Find datasets, configs, or historical logs | [Documentation index](docs/README.md) |

The latest LimeSDR replay decoded GPS L1 C/A and produced a standalone position fix from a 300-second recording. GNSS-SDR decoded and solved the raw recording. MATLAB cross-checked the exported RINEX measurements.

## Repository layout

- [Dashboard frontend](frontend/) and [FastAPI server](server/)
- [Shared Python library](gnss_sdr/), [analysis tools](tools/), and [tests](tests/)
- [Reference datasets and local data paths](data/README.md)
- [Receiver experiment archive](docs/gnss_sdr_experiments/) and [Docker recipes](docker/gnss-sdr/)

See the [repository map](docs/STRUCTURE.md) for the full layout. Large raw I/Q recordings are stored outside Git.
