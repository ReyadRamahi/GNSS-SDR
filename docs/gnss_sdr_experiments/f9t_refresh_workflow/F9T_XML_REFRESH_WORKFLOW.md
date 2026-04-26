# F9T XML Refresh Workflow

## Goal

Use the EVK-F9T / ZED-F9T stream from `hft09` to generate fresh GNSS-SDR assistance XML files.

Important context:

- Receiver is EVK-F9T / ZED-F9T, not older u-blox Gen 8.
- The `hft09` stream behaves like raw TCP, not a standard NTRIP caster.
- Capture source: `10.30.200.59:50012`
- Capture method: `nc`
- Conversion path:

```text
hft09 raw TCP stream
→ UBX binary capture
→ RTKLIB convbin
→ RINEX NAV
→ rinex2assist
→ GNSS-SDR XML assistance
```

## Main Script

Reusable script:

```bash
~/gnss/scripts/refresh_f9t_xml.sh
```

Default usage:

```bash
~/gnss/scripts/refresh_f9t_xml.sh 1800
```

This captures 30 minutes of `hft09` TCP data, converts it to RINEX NAV, runs `rinex2assist`, and updates:

```text
~/gnss/assist/f9t_tcp_latest/
```

## tmux Launcher

Safe launcher for long captures:

```bash
~/gnss/scripts/start_f9t_refresh_tmux.sh 1800
```

This starts the refresh in a tmux session so it survives disconnects.

## Stable XML Path

GNSS-SDR configs should point to:

```ini
GNSS-SDR.AGNSS_gps_ephemeris_xml=/home/rrama28/gnss/assist/f9t_tcp_latest/gps_ephemeris.xml
GNSS-SDR.AGNSS_gps_utc_model_xml=/home/rrama28/gnss/assist/f9t_tcp_latest/gps_utc_model.xml
GNSS-SDR.AGNSS_ref_location=41.880662482,-87.643929543
```

## Current Known-Good XML

A previous successful `hft09` TCP capture produced GNSS-SDR XML with:

```text
<count>3</count>
```

GPS satellites included:

```text
G29
G23
G24
```

That XML was restored into:

```text
~/gnss/assist/f9t_tcp_latest/
```

## Why This Matters

Earlier RTL-SDR-harvested XML only had PRN 28 and PRN 31. The F9T/TCP pipeline gives us a cleaner way to refresh ephemeris from the reference receiver instead of relying on weak RTL harvests.

## Notes

- Do not use `str2str` for the `hft09` stream unless the server is changed to true NTRIP.
- The stream currently behaves like raw TCP.
- If the capture is too small, the script exits without overwriting the latest XML.
- Large raw `.bin` captures are not committed to GitLab.
