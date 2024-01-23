import os
import numpy as np
from preprocessor import detectCarrierFrequency, downConvertSignal, estimateBandwidth, downSampleSignal
from demodulator import detectPreamble, dechirpSignal, getSymbolValues, getPreambleIndex
from decoder import decodeValues, decodeExplicitHeader
from config import EXPLICIT_HEADER_LEN, CARRIER_OFFSET, FFT_FACTOR, TIME_OFFSET, DOWNSAMPLING_FREQUENCIES
import time
from WiresharkStreamer import WiresharkStreamer

wire = WiresharkStreamer()

# Source signal
path = os.getcwd() + "/catched/debug/"
source = np.load( path + "SF7_iqdata.npy")

# Sample frequency
fs = 6e6 # Hz

# FFT factor
factor = FFT_FACTOR

# For carrier detection
size = CARRIER_OFFSET

t1 = time.time()
# Get carrier frequency of source signal
fc = detectCarrierFrequency(source, fs, TIME_OFFSET, size)

# Downconvert source signal
yDown = downConvertSignal(source, fs, fc)

bw = estimateBandwidth(yDown, fs, TIME_OFFSET)

# Downsample downconverted signal
fsd = DOWNSAMPLING_FREQUENCIES[int(bw/125e3)] # Hz
ySamp = downSampleSignal(yDown, fs, fsd)

# Detect preamble and return generated down-chirp
premEnd, w, period, sf, signalBeg, found = detectPreamble(ySamp, fsd, bw)

# Apply de-chirp process on preamble
yDecPrem = dechirpSignal(ySamp[signalBeg:8*period+period//4+signalBeg], w, period)

# Apply de-chirp process on data
yDec = dechirpSignal(ySamp[premEnd:], w, period)

preambleFreq = getPreambleIndex(yDecPrem, period, factor)

# Get symbols' values
values = getSymbolValues(yDec, period, preambleFreq, factor, sf)
print("Symbol values: " + str(values))

# Estimate if there is explicit header
isExplicit, isCRC, cr, rest, pLen = decodeExplicitHeader(values[:EXPLICIT_HEADER_LEN], sf)
toDecode = []
if isExplicit:
    toDecode = values[EXPLICIT_HEADER_LEN:]
else:
    print("Likely there is no explicit header, try implicit")
    toDecode = values

messages = decodeValues(toDecode, sf, bw, isCRC, cr, rest, pLen)
t2 = time.time()
print(str(t2-t1))
b = ""
# for m in messages:
# #    print(''.join(chr(x) for x in m))
#     for x in m:
#         b += "%s " % x

header = {}
header["crc_en"] = 0
header["frequency"] = int(868e6)
header["bandwidth_kHz"] = int(bw/125000)
header["spreading_factor"] = int(sf)
header["implicit_header"] = isExplicit ^ 0x01
header["coding_rate"] = cr
nwskey = "A54F66E173B919CA6BA8375C9B2D7106"
appskey = "A54F66E173B919CA6BA8375C9B2D7106"

def decodeLoRaWAN(b):
    mhdr = {}
    mhdr["FType"] = (b[0] & 0xE0) >> 5
    mhdr["Major"] = b[0] & 0x03
    
    fhdr = {}
    fhdr["DevAddr"] = "".join(["%02X" % x for x in b[1:5][::-1]])
    fhdr["FCtrl"] = {}
    fhdr["FCtrl"]["ADR"] = (b[5] & 0x80) >> 7
    fhdr["FCtrl"]["ACK"] = (b[5] & 0x20) >> 5
    fhdr["FCtrl"]["FOptsLen"] = (b[5] & 0x0F)
    fhdr["FCnt"] = int("".join(["%02X" % x for x in b[6:8][::-1]]))
    skip = 8 + fhdr["FCtrl"]["FOptsLen"]
    fPort = b[skip]
    pay = b[(skip+1):(skip+1) + (len(b[skip+1:]) - 4)]

    from lora.crypto import loramac_decrypt
    payload = "".join(["%02X" % x for x in pay])
    sequence_counter = fhdr["FCnt"]
    key = appskey
    dev_addr = fhdr["DevAddr"]
    decrypted = loramac_decrypt(payload, sequence_counter, key, dev_addr)
    
    return decrypted

dec = decodeLoRaWAN(messages)

payload = b''
for b in messages:
    payload += b.to_bytes(2, "big")
wire.packet(node_id=0, ts = t2, par = header, data = payload)
