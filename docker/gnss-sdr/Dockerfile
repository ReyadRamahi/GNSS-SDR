FROM debian:trixie-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends gnss-sdr=0.0.20-1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /output
ENTRYPOINT ["gnss-sdr"]
