#!/usr/bin/env python3
import serial
import time
from pyubx2 import UBXMessage

PORT = "/dev/ttyUSB0"
BAUD = 38400

cfg_data = [
    # Make sure UBX protocol is allowed on UART1
    ("CFG_UART1INPROT_UBX", 1),
    ("CFG_UART1OUTPROT_UBX", 1),

    # Keep NMEA output too, don't break professor's screen workflow
    ("CFG_UART1OUTPROT_NMEA", 1),

    # Needed for ephemeris extraction
    ("CFG_MSGOUT_UBX_RXM_SFRBX_UART1", 1),

    # Useful for raw measurements / obs
    ("CFG_MSGOUT_UBX_RXM_RAWX_UART1", 1),
]

msg = UBXMessage.config_set(layers=1, transaction=0, cfgData=cfg_data)

with serial.Serial(PORT, BAUD, timeout=0.2) as ser:
    print("Sending CFG-VALSET...")
    print(msg)
    ser.reset_input_buffer()
    ser.write(msg.serialize())

    data = b""
    start = time.time()
    while time.time() - start < 5:
        chunk = ser.read(4096)
        if chunk:
            data += chunk

print("bytes read:", len(data))
print("ACK present:", b"\xb5\x62\x05\x01" in data)
print("NAK present:", b"\xb5\x62\x05\x00" in data)
print("UBX sync count:", data.count(b"\xb5\x62"))
print("NMEA count:", data.count(b"$GN") + data.count(b"$GP"))
print("first 300 decoded chars:")
print(data[:300].decode(errors="ignore"))
