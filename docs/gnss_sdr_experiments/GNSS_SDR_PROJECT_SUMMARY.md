# GNSS-SDR Project Summary

## Goal

The project goal is to receive live GPS L1 C/A signals using SDR hardware on hft02, process them through GNSS-SDR, and eventually feed receiver/satellite/status information into the project dashboard.

Hardware tested:
- RTL-SDR path through SoapyRemote
- LimeSDR-USB on LNAW
- Shared GNSS antenna feed through splitter
- Antenna bias supplied externally, not by the LimeSDR

Software:
- GNSS-SDR v0.0.16
- GNU Radio 3.10.1.1
- gr-osmosdr / SoapySDR path
- LimeSDR dedicated GNSS-SDR source block is not available in this installed build

---

## Main Findings

### 1. RTL-SDR is the healthier receiver path

The RTL-SDR successfully decoded real GPS navigation messages. It was able to receive repeated NAV subframes and was good enough to generate GNSS-SDR assistance XML files.

Generated assistance files:
- `gps_ephemeris.xml`
- `gps_iono.xml`
- `gps_utc_model.xml`

The harvested ephemeris XML contained:
- GPS PRN 28
- GPS PRN 31

This proves the antenna feed and GNSS-SDR pipeline can receive and decode real GPS data, at least through the RTL-SDR path.

---

### 2. LimeSDR can acquire/enter tracking, but cannot hold lock

The LimeSDR does not appear completely dead. With the better config found through parameter sweeps, it repeatedly enters tracking.

However, it loses lock almost immediately.

Typical pattern:
- acquisition/tracking starts
- quick loss of lock
- no bit synchronization
- no GPS NAV messages
- no position fix

This suggests the Lime issue is not simply “no signal.” It is more likely a tracking stability / RF frontend / clock stability issue.

---

### 3. Old/default Lime config was bad

The old/default Lime config was not useful.

Important bad settings:
- `SignalSource.AGC_enabled=true`
- acquisition threshold around `3.5`
- `InputFilter.number_of_taps=51`
- narrow filter setting around `band1_end=0.45`

That config produced very weak acquisition statistics and basically no useful tracking.

---

### 4. Best Lime config came from sweep testing

The better Lime config came from the sweep results.

Best balanced config:
- sample rate: 2 Msps
- AGC disabled
- `InputFilter.number_of_taps=101`
- `InputFilter.band1_end=0.70`
- lower acquisition threshold
- based on `cfg_sr2M_taps101_band70_agcF.conf`

This config restored tracking starts, but still did not produce stable lock or NAV decode.

---

### 5. AGNSS XML loading works, but does not solve Lime

RTL-SDR was used to harvest GNSS-SDR XML assistance files. Those files were then loaded into a LimeSDR AGNSS config.

GNSS-SDR successfully loaded:
- PRN 28 ephemeris
- PRN 31 ephemeris
- ionosphere model
- UTC model

So the AGNSS config path works.

But it did not fix the Lime problem.

Comparison:

Lime balanced baseline, 3 min:
- Tracking starts: 59
- Loss of lock: 52
- GPS NAV messages: 0
- Position fixes: 0

Lime balanced + AGNSS, 3 min:
- Tracking starts: 39
- Loss of lock: 34
- GPS NAV messages: 0
- Position fixes: 0

Lime balanced + AGNSS, 30 min:
- Tracking starts: 568
- Loss of lock: 564
- Bit synchronization locks: 0
- GPS NAV messages: 0
- Position fixes: 0
- NMEA output: 0 bytes

Conclusion:
AGNSS loads correctly, but the LimeSDR still cannot hold tracking long enough to decode NAV data.

---

## Current Working Theory

The current bottleneck is probably not missing ephemeris anymore.

Most likely problem areas:
- LimeSDR RF/frontend configuration
- interference before the SDR
- LimeSDR clock/temperature stability
- lack of GPS L1 hardware filtering
- tracking loop stability with Lime samples

---

## Next Experiments

1. Try a hardware GPS L1 bandpass filter before the LimeSDR.
2. Keep AGC disabled.
3. Re-test the balanced Lime config with the filter.
4. Compare:
   - tracking starts
   - loss-of-lock count
   - bit synchronization
   - NAV messages
   - NMEA output
5. If filtering does not help, investigate Lime clock/temperature/external reference.
6. Continue using RTL-SDR as the working GPS NAV decode baseline.

---

## Files Preserved in Repo

Curated files were copied into `docs/`, including:
- tested configs
- test scripts
- sweep logs/configs
- RTL harvest logs
- Lime baseline and AGNSS logs
- GNSS-SDR assistance XML files
- public RINEX nav file used for reference

Large raw IQ files and runtime folders were intentionally excluded from Git.
