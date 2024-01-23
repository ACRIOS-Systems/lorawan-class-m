import os
import numpy as np
import matplotlib.pyplot as plt
from preprocessor import detectCarrierFrequency, downConvertSignal, estimateBandwidth, downSampleSignal
from demodulator import detectPreamble, dechirpSignal, getSymbolValues, freqInTime, getPreambleIndex
from plotter import plotSignalX, plotSubplotX
from decoder import decodeValues, decodeExplicitHeader
from config import EXPLICIT_HEADER_LEN, CARRIER_OFFSET, T_OFFSET, DOWNSAMPLING_FREQUENCIES

# Source signal
path = os.getcwd() + "/catched/gw/"
source = np.load( path + "gw_somebytes.npy")

# Sample frequency
fs = 6e6 # Hz
fs = 1000000
# Bandwidth
bw = 125e3 # Hz

# FFT factor
factor = 8

# For carrier detection
size = CARRIER_OFFSET

sourceSF = 7 # only for plots

# Source symbol duration
chips = 2**sourceSF
symbolDuration = chips/bw
samplesPerSymbol = int(symbolDuration*fs)

# Source signal duration
symbolCount = (len(source)/samplesPerSymbol)
samplesPerSignal =  int(symbolCount * samplesPerSymbol)
signalDuration = (symbolCount * symbolDuration)
t = np.linspace(0, signalDuration, samplesPerSignal)

#source = np.conj(source)
# Plot source signal
plt.figure(0)
plotSubplotX(source, "Source signal x(t) - raw", r"Time [\textit{s}]", r"Amplitude [\textit{-}]", t, 
            freqInTime(source, fs), "Source signal x(t) - enveloped", r"Time [\textit{s}]", r"Frequency [\textit{Hz}]", t[:-1])

# Get carrier frequency of source signal
timeOffset = 500
fc = detectCarrierFrequency(source, fs, timeOffset, size)

# Downconvert source signal
yDown = downConvertSignal(source, fs, fc)

# Plot downconverted source signal
plt.figure(1)
plotSubplotX(yDown, "Downconverted source signal x(t) - raw", r"Time [\textit{s}]", r"Amplitude [\textit{-}]", t, 
            freqInTime(yDown, fs), "Downconverted source signal x(t) - enveloped", r"Time [\textit{s}]", r"Frequency [\textit{Hz}]", t[:-1])

bw = estimateBandwidth(yDown, fs, T_OFFSET)
if bw == 0:
    print("BANDWIDTH not found")

bw = int(125e3)
# Downsample downconverted signal
fsd = DOWNSAMPLING_FREQUENCIES[int(bw/125e3)-1] # Hz

ySamp = yDown
fsd = 500000
ySamp = downSampleSignal(yDown, fs, fsd)
plt.grid()

# Downsampled samplesPerSymbol
samplesPerSymbol = int(symbolDuration*fsd)

# Downsampled signal duration
symbolCount = (len(ySamp)/samplesPerSymbol)
samplesPerSignal =  int(symbolCount * samplesPerSymbol)
signalDuration = (symbolCount * symbolDuration)
t = np.linspace(0, signalDuration, samplesPerSignal)

# Plot downsampled downconverted signal
plt.figure(2)
plotSubplotX(ySamp, "Downsampled downconverted signal x(t) - raw", r"Time [\textit{s}]", r"Amplitude [\textit{-}]", t, 
            freqInTime(ySamp, fsd), "Downsampled downconverted signal x(t) - enveloped", r"Time [\textit{s}]", r"Frequency [\textit{Hz}]", t[:-1])

plt.figure(3)
plotSignalX(freqInTime(ySamp, fsd), "", r"Čas [\textit{s}]", r"Frekvence [\textit{Hz}]", t[:-1])

plt.show()
# Estimate bandwidth


# Detect preamble and return generated down-chirp
premEnd, w, period, sf, signalBeg, found = detectPreamble(ySamp, fsd, bw)
if not found:
    print("SPREADING FACTOR not found for uplink")
    print("Try downlink...")
    premEnd, w, period, sf, signalBeg, found = detectPreamble(ySamp, fsd, bw, True)
    if not found:
        print("Not found")
    else:
        isDowlink = 1

# Apply de-chirp process on preamble
yDecPrem = dechirpSignal(ySamp[signalBeg:8*period+period//4+signalBeg], w, period)

# Downsampled signal duration
preambleSymbolCount = 8
samplesPerPreamble =  int(preambleSymbolCount * samplesPerSymbol)
preambleDuration = (preambleSymbolCount * symbolDuration)
tp = np.linspace(0, preambleDuration, samplesPerPreamble)

# plt.figure(4)
# plotSubplotX(freqInTime(ySamp[signalBeg:len(yDecPrem)+signalBeg], fsd), "Downsampled downconverted signal preamble x(t) - enveloped", r"Time [\textit{s}]", r"Frequency [\textit{Hz}]", tp[:-1], 
#             freqInTime(yDecPrem, fsd), "Dechirped downsampled downconverted signal preamble x(t) - enveloped", r"Time [\textit{s}]", r"Frequency [\textit{Hz}]", tp[:-1])

# Dechirped signal data duration
symbolCount = (len(yDecPrem)/samplesPerSymbol)
samplesPerSignal =  int(symbolCount * samplesPerSymbol)
signalDuration = (symbolCount * symbolDuration)
tPrem = np.linspace(0, signalDuration, samplesPerSignal)

# Apply de-chirp process on data
yDec = dechirpSignal(ySamp[premEnd:], w, period)

# Dechirped signal data duration
symbolCount = (len(yDec)/samplesPerSymbol)
samplesPerSignal =  int(symbolCount * samplesPerSymbol)
signalDuration = (symbolCount * symbolDuration)
t = np.linspace(0, signalDuration, samplesPerSignal)

# Plot data
plt.figure(5)
plotSubplotX(freqInTime(ySamp[premEnd:premEnd+len(yDec)], fsd), "Downsampled downconverted signal data x(t) - enveloped", r"Time [\textit{s}]", r"Frequency [\textit{Hz}]", t[:-1], 
            freqInTime(yDec, fsd), "Dechirped downsampled downconverted signal data x(t) - enveloped", r"Time [\textit{s}]", r"Frequency [\textit{Hz}]", t[:-1])

# Lines indexes
# idxs = np.arange(0, symbolCount*symbolDuration, symbolDuration)
# plt.vlines(x = idxs, ymin = -125000, ymax = 125000, colors = 'black')

# Get premable's values
preambleFreq = getPreambleIndex(yDecPrem, period, factor)

# Get symbols' values
values = getSymbolValues(yDec, period, preambleFreq, factor, sf)
print("Symbol values: " + str(values))

# Plot preamble and data
plt.figure(6)
plotSignalX((freqInTime(yDec, fsd) / 125000) * 2**sf, "Dechirped downsampled downconverted signal data x(t) - enveloped", r"Time [\textit{s}]", r"Value [\textit{-}]", t[:-1])

# Lines indexes
# idxs = np.arange(0, symbolCount*symbolDuration, symbolDuration)
# plt.vlines(x = idxs, ymin = -2**sf, ymax = 2**sf, colors = 'black')

# Estimate if there is explicit header
isExplicit, isCRC, cr, rest, pLen = decodeExplicitHeader(values[:EXPLICIT_HEADER_LEN], sf)
toDecode = []
if isExplicit:
    toDecode = values[EXPLICIT_HEADER_LEN:]
else:
    print("Likely there is no explicit header, try implicit")
    toDecode = values

messages = decodeValues(toDecode, sf, bw, isCRC, cr, rest, pLen)

for m in messages:
    print(''.join(chr(x) for x in m))

# Plot all figures
plt.show()