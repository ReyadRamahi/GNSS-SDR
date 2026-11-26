FROM debian:trixie-slim AS receiver

RUN apt-get update \
    && apt-get install -y --no-install-recommends gnss-sdr=0.0.20-1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /output
ENTRYPOINT ["gnss-sdr"]

FROM receiver AS capture

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gnuradio \
        gr-osmosdr \
        python3-numpy \
        python3-soapysdr \
        soapysdr-module-lms7 \
        soapysdr-module-remote \
        soapysdr-tools \
    && rm -rf /var/lib/apt/lists/*

FROM receiver AS replay
