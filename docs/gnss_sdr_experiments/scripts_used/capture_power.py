import SoapySDR
from SoapySDR import SOAPY_SDR_RX, SOAPY_SDR_CF32
import numpy as np
import sys

sdr = SoapySDR.Device(dict(driver="lime", serial="0009061C01502715"))
sdr.setSampleRate(SOAPY_SDR_RX, 0, 2e6)
sdr.setFrequency(SOAPY_SDR_RX, 0, 1.57542e9)
sdr.setAntenna(SOAPY_SDR_RX, 0, "LNAW")
sdr.setGain(SOAPY_SDR_RX, 0, 50)

rx_stream = sdr.setupStream(SOAPY_SDR_RX, SOAPY_SDR_CF32)
sdr.activateStream(rx_stream)

n_samples = 1_000_000
buf = np.zeros(n_samples, dtype=np.complex64)
total_read = 0
while total_read < n_samples:
    sr = sdr.readStream(rx_stream, [buf[total_read:]], n_samples - total_read, timeoutUs=2_000_000)
    if sr.ret <= 0:
        print(f"read error: {sr.ret}", file=sys.stderr)
        break
    total_read += sr.ret

sdr.deactivateStream(rx_stream)
sdr.closeStream(rx_stream)

power = float(np.mean(np.abs(buf[:total_read])**2))
rms = float(np.sqrt(power))
peak = float(np.max(np.abs(buf[:total_read])))

print(f"samples captured: {total_read}")
print(f"mean power (|x|^2):  {power:.6e}")
print(f"RMS amplitude:       {rms:.6e}")
print(f"peak amplitude:      {peak:.6e}")
