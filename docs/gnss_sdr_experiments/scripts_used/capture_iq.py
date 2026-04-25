#!/usr/bin/env python3
from gnuradio import gr, blocks
import osmosdr
import sys

if len(sys.argv) != 3:
    print("usage: python3 capture_iq.py <ANTENNA> <OUTFILE>")
    sys.exit(1)

antenna = sys.argv[1]
outfile = sys.argv[2]

class top_block(gr.top_block):
    def __init__(self):
        gr.top_block.__init__(self)

        self.src = osmosdr.source(args="driver=lime")
        self.src.set_sample_rate(2e6)
        self.src.set_center_freq(1575.42e6, 0)
        self.src.set_gain(50, 0)
        self.src.set_antenna(antenna, 0)

        self.head = blocks.head(gr.sizeof_gr_complex, int(2e6 * 3))
        self.sink = blocks.file_sink(gr.sizeof_gr_complex, outfile, False)
        self.sink.set_unbuffered(False)

        self.connect(self.src, self.head, self.sink)

tb = top_block()
tb.start()
tb.wait()
print(f"done: {antenna} -> {outfile}")
