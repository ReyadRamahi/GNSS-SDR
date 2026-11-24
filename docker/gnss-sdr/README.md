# GNSS-SDR offline replay in Docker

Use the Debian image to reproduce the [November LimeSDR replay](../../docs/gnss_sdr_experiments/EXPERIMENT_RESULTS.md). It packages GNSS-SDR 0.0.20-1, the version that produced a position fix. The Ubuntu image packages 0.0.16-1 for comparison with the version previously recorded on `hft02`.

## Build and check versions

Run from the repository root. Docker selects the host architecture. The original replay ran on ARM64. Ubuntu publishes the comparison package for both ARM64 and AMD64.

```bash
docker build -t gnss-sdr-replay:0.0.20 docker/gnss-sdr
docker run --rm gnss-sdr-replay:0.0.20 --version

docker build -t gnss-sdr-replay:0.0.16 -f docker/gnss-sdr/Dockerfile.jammy docker/gnss-sdr
docker run --rm gnss-sdr-replay:0.0.16 --version
```

## Replay the known recording

Set `capture_dir` to the directory holding `rx1h.cf32` and `SHA256SUMS`. This config expects headerless, little-endian interleaved CF32 at 2 MS/s and translates the recording's +500,009.766 Hz IF. It targets six PRNs acquired in this recording. For a different recording, check its metadata and select suitable acquisition channels.

```bash
capture_dir=/absolute/path/to/the/capture
config="$PWD/docs/gnss_sdr_experiments/configs_used/baseline/lime_soapyremote_l1_cf32_replay.conf"
output_dir=$(mktemp -d "$PWD/lime-replay-XXXXXX")

(
  cd "$capture_dir" || exit 1
  if command -v sha256sum >/dev/null; then
    sha256sum -c SHA256SUMS
  else
    shasum -a 256 -c SHA256SUMS
  fi
) &&
cp "$config" "$output_dir/lime_l1.conf" &&
docker run --rm --network none \
  --mount "type=bind,source=$capture_dir,target=/capture,readonly" \
  --mount "type=bind,source=$output_dir,target=/output" \
  gnss-sdr-replay:0.0.20 --config_file=/output/lime_l1.conf
```

The replay reads the capture through a read-only mount. The output directory holds the NMEA solution and the RINEX observation and navigation files after a successful fix. If the receiver appears stalled, check whether it reaches `Processing file` before interpreting the result. Use a fresh output directory for each run, including version comparisons, so cached ephemerides do not carry over.

The Ubuntu recipe is for diagnosis. The 0.0.20 replay produced a fix again with the same file and config after an earlier startup delay. The older-package attempts that stalled before processing the file do not establish why the earlier `hft02` run failed.
