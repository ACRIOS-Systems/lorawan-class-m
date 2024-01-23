import adi
from encoder import encodeCR1, listToInt, interleaver, whitening, grayDecode, modulate, modulateReal, generateDownchirp
import numpy as np
from demodulator import freqInTime2
from plotter import plotSignal
import matplotlib.pyplot as plt

def SDRTransmit(fSample=6000000, fCenter=867800000, rxBufferSize=1024*1024*12, rxRfBw=6000000):
    # sdr = adi.Pluto()
    # sdr.sample_rate = fSample
    # sdr.tx_rf_bandwidth = rxRfBw
    # sdr.tx_lo = fCenter
    # sdr.tx_hardwaregain_chan0 = -50

    sf = 8
    cr = 1
    fSample = int(125e3)
    #fSample = 2**sf
    #fSample = 6e6

    #bytes = [74, 65, 73, 74, 44, 61, 74, 61]
    bytes = [248, 28, 0, 24, 0, 8, 252, 2, 3, 2, 13, 238, 10, 248, 242, 5, 245, 26, 244, 235, 246, 28, 243]
    nibbles = []

    for b in bytes:
        nibbles.append((b & 0xF0) >> 4)
        nibbles.append((b & 0x0F)) 

    encoded = []
    for n in nibbles:
        en = encodeCR1(n)
        encoded.append(en)


    print(encoded)
    encoded = listToInt(encoded)
    print(encoded)
    interleaved = interleaver(encoded, sf, cr)

    whitened = whitening(interleaved, cr)

    grayed = grayDecode(whitened)
    #grayed = [3783, 412, 255, 424, 32, 147, 4044, 4055, 480, 143, 3899, 3787, 3672, 3850, 4011, 266, 333, 3999]
    #grayed = [248, 28, 0, 24, 0, 8, 252, 2, 3, 2, 13, 238, 10, 248, 242, 5, 245, 26, 244, 235, 246, 28, 243]
    grayed = [25, 50, 75, 100, 125, 150, 175, 200, 225, 250]
    upchirps = [0, 0, 0, 0, 0, 0, 0, 0]
    downchirps = [0, 0]

    upchirpsMod = np.concatenate([modulate(2**sf, up, fSample) for up in upchirps])
    downchirpsMod = np.concatenate([np.conj(modulate(2**sf, down, fSample)) for down in downchirps])
    downchirpsMod = np.concatenate([downchirpsMod, downchirpsMod[:fSample//4]])
    datasMod = np.concatenate([modulate(2**sf, dat, fSample) for dat in grayed])


    # chips = 2**sf
    # symbolDuration = chips/125e3
    # samplesPerSymbol = int(symbolDuration*fSample)

    # upchirpsMod = np.concatenate([modulateReal(125e3, fSample, sf, up) for up in upchirps])
    # downchirpsMod = np.concatenate([generateDownchirp(125e3, fSample, sf) for down in downchirps])
    # downchirpsMod = np.concatenate([downchirpsMod, downchirpsMod[:samplesPerSymbol//4]])
    #datasMod = np.concatenate([modulateReal(125e3, fSample, sf, dat) for dat in grayed])
    
    sig = np.concatenate([upchirpsMod, downchirpsMod, datasMod])



    plotSignal(freqInTime2(sig), "Modulated signal x(t)", "Time [s]", "Frequency [Hz]")
    plt.show()

    np.save("testData_SF8_modulatedReceivedValuesSim.npy", sig)
    pass

SDRTransmit()