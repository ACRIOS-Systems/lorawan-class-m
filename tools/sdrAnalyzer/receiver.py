import adi
import numpy as np
import os
from config import RECEIVE_THRESHOLD

def getThresholds(received):
    """
    Returns thresholds for signal detection in SDR output.

    Parameters
    ----------
    received : array
        Received IQ samples from SDR.

    Returns
    -------
    rAbs : array
        Magnitudes of IQ samples.
    rHigh : int
        Signal detection threshold.
    rLow : int
        Noise detection threshold
    """

    rAbs = abs(received) # get magnitudes
    rMax = max(rAbs) # get highest magnitude
    rAvg = sum(rAbs) / len(rAbs) # get average
    rHigh = ((rMax + rAvg) / 
            RECEIVE_THRESHOLD) # set threshold for possible signal detection
    rLow = rAvg # set threshold for noise

    return rAbs, rHigh, rLow

def detectSignal(received, frameMinLen):
    """
    Returns thresholds for signal detection in SDR output.

    Parameters
    ----------
    received : array
        Received IQ samples from SDR.
    frameMinLen : int
        Minimum length at which samples can be considered as a signal.

    Returns
    -------
    y : array
        Samples that can be considered as a signal.
    """

    y = []
    start = 0
    stop = 0

    yAbs, yHigh, yLow = getThresholds(received)

    while stop < (len(yAbs)-1): # try to find signal until there are no data to search
        start = stop
        found = False
        for i in range(stop + 100, len(yAbs)): # find possible signal's start
            if yAbs[i] > yHigh: # if there is something above threshold, there will be likely signal
                start = i - 100 # mark new start with offset
                found = True 
                break

        if found: # continue only if there is valid start
            stop = len(yAbs)-1
            for i in range(start + 100, len(yAbs)): # find signal's end
                if yAbs[i] < yLow: # if there is something below threshold, there will be likely noise
                    stop = i + 100 # mark new end with offset
                    break

            fragmentLen = stop - start 

            if fragmentLen < frameMinLen: # check if there is long enough frame
                stop += 100 
            else: # if so, return requested IQ data
                print(f"Found candidate frame, {fragmentLen} symbols long!")
                y = received[start:stop]
                return y # TODO: continue in searching in the rest of samples
    
        if start == stop: # found nothing
            return y

    return y

def createRadio(fs = 6e6, fc = 868.5e6, buffer = 1024*1024*12, rxRfBw = 3e6, control = "fast_attack"):
    """
    Configures and returns radio.

    Parameters
    ----------
    fs : int
        SDR's sampling frequency [Hz].
    fc : int
        SDR's center frequency [Hz].
    buffer : int
        Number of samples returned per rx() call.
    rxRfBw : int
        Bandwidth to listen around center frequency [Hz].
    control : str
        SDR's automatic gain control ("fast_attack" "manual" "slow_attack").
    
    Returns
    -------
    sdr : adi.ad936x.Pluto
        Configured radio.
    """

    # create radio
    sdr = adi.Pluto()

    # configure properties
    sdr.sample_rate = fs 
    sdr.rx_lo = int(fc) 
    sdr.rx_buffer_size = int(buffer) 
    sdr.rx_rf_bandwidth = int(rxRfBw)
    sdr.gain_control_mode_chan0 = control


    return sdr

def SDRReceive(sdr, frameMinLen=12*6144, debug=False):
    """
    Returns received signal if there is any.

    Parameters
    ----------
    sdr : adi.ad936x.Pluto
        Radio used to receiving.
    frameMinLen : int
        Minimum length at which samples can be considered as a signal.
    debug : bool
        Provides debugging tools.

    Returns
    -------
    out : array
        IQ samples representing signal.
    """

    # Read properties
    if debug:
        print("RX LO %s" %(sdr.rx_lo))
    
    # Collect data
    sdr.rx_destroy_buffer()

    print("Starting listening... ")
    y = sdr.rx() # SDR output -> IQ data


    out = detectSignal(y, frameMinLen)

    if debug:
        if len(out) != 0:
            path = os.getcwd() + "/catched/test/"
            # SF_CR_BW_Len_exp.npy
            np.save(path + "7_1_1_44.npy", out)
            return out
    else:
        return out
