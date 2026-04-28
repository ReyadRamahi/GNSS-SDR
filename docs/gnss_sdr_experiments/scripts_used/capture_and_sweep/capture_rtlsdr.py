import numpy as np
from gnuradio import gr, blocks
import osmosdr

class TopBlock(gr.top_block):
    def __init__(self, n_samples):
        gr.top_block.__init__(self, "rtlsdr_capture")
        self.src = osmosdr.source(
            args="soapy=0,driver=remote,remote=tcp://172.17.0.1:55132,remote:driver=rtlsdr,serial=00000001"
        )
        self.src.set_sample_rate(2.048e6)
        self.src.set_center_freq(1.57542e9, 0)
        self.src.set_gain_mode(False, 0)
        self.src.set_gain(40, 0)
        self.head = blocks.head(gr.sizeof_gr_complex, n_samples)
        self.sink = blocks.vector_sink_c()
        self.connect(self.src, self.head, self.sink)

n = 500_000
tb = TopBlock(n)
tb.start()
tb.wait()

samples = np.array(tb.sink.data(), dtype=np.complex64)
print(f"samples captured: {len(samples)}")
if len(samples) == 0:
    print("NO SAMPLES")
else:
    power = float(np.mean(np.abs(samples)**2))
    rms = float(np.sqrt(power))
    peak = float(np.max(np.abs(samples)))
    print(f"mean power: {power:.6e}")
    print(f"RMS:        {rms:.6e}")
    print(f"peak:       {peak:.6e}")
