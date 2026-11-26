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

## Optional LimeSDR capture image

Build the capture target to add GNU Radio, gr-osmosdr, NumPy, the Python SoapySDR API, and the Lime and SoapyRemote modules. The default build remains the lean offline receiver.

```bash
docker build --target capture -t gnss-sdr-capture:0.0.20 docker/gnss-sdr
docker run --rm --network none --entrypoint SoapySDRUtil gnss-sdr-capture:0.0.20 --info
```

Use `--entrypoint python3` to run a capture script you mount into the container. Review the existing `hft02` helper's absolute paths and host-specific Soapy module overrides before reusing it. The container can use its own packaged modules and standard discovery paths. Mount a writable output directory on a local disk for long recordings.

If the Lime is still attached to `hft02`, its existing SoapyRemote server continues to handle USB. A capture container on the Linux host can use `--network host` and the existing loopback endpoint. A capture container on another computer needs network access to the server and its stream transport. The offline replay can run anywhere the capture file is available, with networking disabled. See [Docker host networking](https://docs.docker.com/engine/network/drivers/host/).

### Sample timestamps

Docker packaging does not change the SDR's sample clock or the hardware timestamp on a sample that arrives intact. Live streaming adds scheduling, buffering, and transport risk. Judge continuity from stream metadata and overrun reports.

The verified 300-second CF32 file stores I/Q values only. Its host launch and activation-request times cannot identify the UTC time of its first ADC sample. For a timing run, use a capture program that records each buffer's file sample index, actual sample count, `readStream` flags, and valid `timeNs` values. Check that successive device timestamps advance by the preceding sample count at the recorded rate, and record discontinuities. Use device timestamps only when `SOAPY_SDR_HAS_TIME` is set. [SoapySDR stream API](https://github.com/pothosware/SoapySDR/blob/master/include/SoapySDR/Device.hpp)

For absolute UTC or alignment across receivers, verify how the particular radio and firmware relate the hardware sample counter to PPS and UTC. A locked 10 MHz reference stabilizes the sample rate. PPS supplies the timing edge, and a known relationship between that edge and the sample counter supplies the time origin. The earlier run left external-reference selection and lock unverified.

## Version comparison

Both ARM64 images completed a replay of the same checksum-verified 300-second recording with the same configuration and fresh output directories.

| Package | GPS NAV messages logged | Position epochs printed |
| --- | ---: | ---: |
| Ubuntu 22.04, GNSS-SDR 0.0.16-1 | 272 | 0 |
| Debian trixie, GNSS-SDR 0.0.20-1 | 257 | 149 |

The 0.0.20 package is the recommended starting point for this offline replay. The packages also use different dependency versions, so the comparison does not identify an individual code change or establish the cause of the earlier live or offline failures on `hft02`. Try 0.0.20 alongside the existing host installation before changing the system package.

## Live fix-health dashboard on Linux

Run from the checkout root on the Linux host with access to the LimeSDR SoapyRemote server. The live configuration assumes that server is reachable at `127.0.0.1:55132` and uses the lab receiver's RX1_H/LNAH input. Check receiver availability before starting. Update the device selector in [the live config](../../configs/lime_soapyremote_live_l1.conf) for another radio or endpoint.

```bash
docker compose -p lime-live -f docker/gnss-sdr/compose.live.yaml up --build -d
docker compose -p lime-live -f docker/gnss-sdr/compose.live.yaml logs -f receiver
```

If Docker Engine is available without the Compose plugin, use the same services directly:

```bash
docker build --target capture -t lime-live-receiver docker/gnss-sdr
docker build -f docker/gnss-sdr/Dockerfile.dashboard -t lime-live-dashboard .
docker volume create lime-live-output

docker run -d --rm --name lime-live-dashboard --network host \
  -e GNSS_LIVE_NMEA=/output/gnss_pvt.nmea -e GNSS_MONITOR_PORT=15532 \
  --mount type=volume,source=lime-live-output,target=/output,readonly \
  lime-live-dashboard

docker run -d --rm --name lime-live-receiver --network host \
  --mount type=volume,source=lime-live-output,target=/output \
  --mount "type=bind,source=$PWD/configs/lime_soapyremote_live_l1.conf,target=/config/live.conf,readonly" \
  lime-live-receiver --config_file=/config/live.conf
```

The receiver writes NMEA to a shared volume and sends Monitor activity to loopback UDP port 15532. The dashboard reads NMEA and forwards both streams over its existing WebSocket. It shows GGA fix status and satellite count, GSA geometry and satellite IDs, and GSV signal strength for used GPS satellites. Fix age is elapsed time since the latest valid fix arrived in the browser. After six seconds without receiver activity, the app marks the last position stale. Monitor activity can show an active receiver while it is still acquiring a fix.

The dashboard listens on `127.0.0.1:8000`. To view it from your Mac, run the SSH tunnel locally and open [the forwarded dashboard](http://localhost:8000).

```bash
ssh -N -L 8000:127.0.0.1:8000 your-user@hft02
```

Stop the containers with `docker compose -p lime-live -f docker/gnss-sdr/compose.live.yaml down`. For the standalone containers, use `docker stop lime-live-receiver lime-live-dashboard`. The named output volume retains the NMEA file. The fix-health indicators describe the available observations and their geometry. Surveyed truth or a validated error model is needed to estimate accuracy in meters.
