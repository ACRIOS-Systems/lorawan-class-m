import numpy as np
import scipy.signal as signal
from config import VALIDS_BWS, VALID_SFS, BW_THRESHOLD
from demodulator import freqInTime, calculateSamplesSpecific

def detectCarrierFrequency(sig, fs, offset, size):
    """
    Returns signal's carrier frequency in Hz.

    Parameters
    ----------
    sig : array
        IQ samples from which is carrier frequency estimated.
    fs : int
        Signal's sampling frequency.
    offset : int
        In order to avoid possible noise at the beginning of the signal and thus distorted carrier detection, time offset (count of samples) is defined.
    size : int
        Count of samples from which carrier frequency is estimated.
    """

    e =  offset + size 
    if (e > (len(sig) - offset)) or (size <= 0): # if invalid size - correct it
        e = len(sig) - offset
        size = e - offset

    # FFT calculation
    Sxx = np.fft.fft(sig[offset : e])

    # Find index with highest value
    idx = np.argmax(np.abs(Sxx))

    # Calculate carrier frequency and return it
    return (idx * fs) / size

def downConvertSignal(sig, fs, fc):
    """
    Returns array of downconverted signal.

    Parameters
    ----------
    sig : array
        IQ samples (signal) to be downconverted.
    fs : int
        Signal's sampling frequency.
    fc : int
        Carrier frequency.
    """
    # Create signal with carrier frequency
    carrier = np.exp(-1j * 2 * np.pi * fc * (np.arange(len(sig)) / fs))

    # Downconvert signal
    return sig * carrier

def getMinMaxFreq(y, fs):
    """
    In given bunch of IQ samples searchs for minimum and maximum frequency.

    Parameters
    ----------
    y : array
        IQ samples to be searched.
    fs : int
        Sampling frequency.

    Returns
    -------
    fMin : int
        Minimum frequency [Hz].
    fMax : int
        Maximum frequency [Hz]
    """

    yEnv = freqInTime(y, fs)
    fMin = np.min(yEnv)
    fMax = np.max(yEnv)

    return fMin, fMax

def estimateBandwidth(sig, fs, offset):
    """
    Returns signal's Bandwidth estimation.

    Parameters
    ----------
    sig : array
        IQ samples (signal) from which is Bandwidth estimated.
    fs : int
        Sampling frequency.
    offset : int
        In order to avoid possible noise at the ends of the signal or overflow, time offset is defined.

    Returns
    -------
    bw : int
        Estimated Bandwidth [Hz].
    """

    bw = 0
    min = 0
    for b in VALIDS_BWS:
        samps = calculateSamplesSpecific(VALID_SFS[-1], b, fs) # calculate samples per symbol for last valid Spreading Factor and current Bandwidth

        s = offset + int(samps / 2)
        e = s + samps

        if e > (len(sig) - offset):
            e = len(sig) - offset
            if e < s:
                s = offset
                if s > e:
                    continue # probably no valid signal for this configuration

        min, max = getMinMaxFreq(sig[s : e], fs) # if is given highest valid Spreading Factor, it should ensure that in given range there is atleast one peak
        total = abs(min) + abs(max) # calculate distance (in Hz) between minimum and maximum frequency

        if total > (b * (1 - BW_THRESHOLD)) and total < (b * (1 + BW_THRESHOLD)): # if distance is in boundaries, signal's Bandwidth is found
            bw = b
            break
    
    return bw

def downSampleSignal(down, fs, fsdown):
    """
    Returns array of downsampled signal.

    Parameters
    ----------
    sig : array
        IQ samples (signal) to be downsampled.
    fs : int
        Signal's sampling frequency.
    fsdown : int
        Sampling frequency to downsample.
    """

    # Calculate how much will be signal downsampled
    ratio = int(fs // fsdown)

    # Downsample signal and return it
    return signal.decimate(down, ratio, ftype="fir")


def preproccessSignal(sig, fs, fsd, size, offset = 500):
    """
    Returns downconverted and downsampled signal.

    Parameters
    ----------
    sig : array
        IQ samples (signal) to be preprocessed.
    fs : int
        Signals's sampling frequency.
    offset : int
        In order to avoid possible noise at the beginning of signal and thus distorted carrier detection, time offset (count of samples) is defined.
    fsd : int
        Sampling frequency to downsample.
    size : int
        Count of samples from which carrier frequency is estimated.

    Returns
    -------
    downsampled : array
        Downconverted and downsampled signal.
    """

    # Find signal's carrier frequency
    carrier = detectCarrierFrequency(sig, fs, offset, size)

    # Downconvert signal to the estimated carrier frequency
    downconverted = downConvertSignal(sig, fs, carrier)

    # Downsample signal
    downsampled = downSampleSignal(downconverted, fs, fsd)

    return downsampled