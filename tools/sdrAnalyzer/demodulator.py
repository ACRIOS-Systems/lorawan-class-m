import numpy as np
from config import (VALID_SFS, SF_SAMPLES_N, SF_7_SAMPLES_N, VALIDS_BWS, BW_THRESHOLD, MINIMUM_SPAN_SAMPLES, 
                    SPAN_COEFFICIENT, PERIOD_SPAN, PERIOD_VARIANCE, SF_THRESHOLD_SKIP, SF_THRESHOLD_SKIP_END, 
                    SF_THRESHOLD_COEFFICIENT, INITIAL_PEAK_SPAN, TIME_OFFSET, INITIAL_CORRELATION_COEFFICIENT, FFT_DISTANCE, SAMPLING_FREQUENCY)

def freqInTime(sig, fs = 0):
    """
    Applies envelope on signal and returns enveloped signal as array.

    Parameters
    ----------
    sig : array
        IQ samples (signal) to be enveloped.
    fs : int
        Signals's sampling frequency.
    """

    if fs == 0:
        return np.angle(sig[1:] * np.conj(sig)[:-1])
    else:
        return (np.angle(sig[1:] * np.conj(sig)[:-1]) / (2.0*np.pi)) * fs
    
def calculateSamplesSpecific(sf, bw, fs):
    """
    Calculates and returns as int samples per symbol for given Spreading Factor, Bandwidth and Sampling frequency.

    Parameters
    ----------
    sf : int
        For which Spreading Factor is needed to calculate samples per symbol.
    bw : int
        For which Bandwidth is needed to calculate samples per symbol.
    fs : int
        Sampling frequency.
    """

    chips = 2**sf
    duration = chips/bw

    return int(duration * fs)

def caulcateSamples(bw, fs):
    """
    Calculates and returns samples per symbol for each valid Spreading Factor.

    Parameters
    ----------
    bw : int
        For which Bandwidth is needed to calculate samples per symbol.
    fs : int
        Sampling frequency.

    Returns
    -------
    samples : dict
        Samples per symbol for each valid Spreading Factor for given Bandwidth and Sampling Frequency.
    """

    samples = {}

    for i in range(len(VALID_SFS)):
        samples[SF_SAMPLES_N[i]] = calculateSamplesSpecific(VALID_SFS[i], bw, fs)

    return samples

def getSFDetectionThreshold(y, coeff, range = 0.1):
    """
    Returns threshold for peak detection.

    Parameters
    ----------
    y : array
        IQ samples from which is threshold established.
    coeff : int
        Coefficient that is used to magnify or shrink threshold.
    range : float
        Determines count of minimums to be picked.

    Returns
    -------
    threshold : int
        Threshold for peak detection.
    """

    diff = np.diff(freqInTime(y), 1)
    avgSig = np.sum(diff) / len(diff) # calculate average from given bunch of samples
    env = np.abs(diff) # get magnitudes

    envMins = sorted(env)[-(int(len(env) * range)):] # select minimums given to the range

    avgMin = sum(envMins) / len(envMins) # get average from selected minimums

    threshold = avgSig - (avgMin * coeff) # actual threshold

    return threshold

def detectEdges(window, threshold, state, startIndex = 0, start = 0, isRest = False):
    """
    Searchs in given bunch of samples and based on threshold finds lowest point (which should be peak/end of symbol).

    Parameters
    ----------
    window : array
        IQ samples in which is peak searched.
    threshold : float
        Boundary to pick out lowest points.
    startIndex : int
        Is used to give right range of samples if in first given bunch of samples was not found end of the edge.
    start : int
        Serves for searching from end of the first bunch of samples if in first given bunch of samples was not found end of the edge.
    isRest : bool
        Signalling that end of the edge was not found in first given bunch of samples. 
        Once, end of the edge is found it is not necessary to continue in searching. 

    Returns
    -------
    foundMins : array
        Contains all found lowest points (there could be many in one bunch of samples - that depends on how accurate is threshold and how much samples are given).
    state : string
        If necessary (state == searchingRisingEdge), signalling that there is still edge to be searched.
    startIndex : int
        Is used to give right range of samples if in first given bunch of samples was not found end of the edge.
    """

    foundMins = []
    for i in range(start, len(window)):
        if state == "searchingFallingEdge":
            if window[i] < threshold: # find first occurence that is under the threshold -> start of the edge
                startIndex = i
                state = "searchingRisingEdge"
        else:
            if window[i] > threshold: # first occurence above threshold should be end of the edge
                endIndex = i
                foundMins.append(findLowest(window[startIndex:endIndex], startIndex))
                state = "searchingFallingEdge"
                if isRest:
                    break
                
    return foundMins, state, startIndex

def findLowest(edge, offset):
    """
    Searchs in given bunch of samples for lowest value and returns it as tuple with the correct position.

    Parameters
    ----------
    edge : array
        IQ samples in which is lowest value searched.
    offset : int
        Serves to calculate correct position in window.
    """

    localMinIndex = np.argmin(edge)

    return (edge[localMinIndex], offset+localMinIndex)

def recalculateSpan(pos, ref, last, span, samples, coef):
    """
    If needed, based on previous difference and current difference, recalculate span to expand/narrow searching window for peak detection.

    Parameters
    ----------
    pos : int
        Current found peak position.
    ref : int
        Reference position from which is calculated next jump and period.
    span : float
        Currently used span.
    samples : int
        Count of samples per symbol.
    coef : float
        Coefficient that determines how much can span grow or shrink.
    
    Returns
    -------
    ref : int
        Updated reference position.
    last : int
        Updated last difference for next iteration.
    span : float
        Updated or same as before span.
    """

    diff = ref - pos
    if abs(diff) <= abs(last): # if difference is getting smaller (= peak detection is more precise), span could be scaled down 
        newSpan = span - (span * (((samples - (abs(last) - abs(diff)))/samples) * coef))
    else: # scale up span if current difference is higher than the previous one
        newSpan = span + (span * (((abs(diff) - abs(last))/samples) * coef))

    # there are defined boundaries in which span should operate
    # bad things could happen if there would be only one sample for peak detection, or the searching window would interfere into two symbols
    if int(newSpan * samples) > MINIMUM_SPAN_SAMPLES and int(newSpan * samples) < (samples//2):
        span = newSpan

    # do correction
    ref -= diff
    last = diff

    return ref, last, span

def findPreamblePeaks(sig, threshold, SFSamples, span, offset, downlink):
    # TODO: do description
    mins = [] # there are stored peaks

    lastDifference = None # to corrigate period's deflection

    ref = SFSamples + offset # first peak should be around number of samples for given SF with time offset
    lastConfirmedSymbol = 0 # = last found peak -> last found symbol
    isFirst= True
    lastIndex = 0

    nextStart = int(ref - (SFSamples * span)) # define start for the next possible peak detection
    nextEnd = int(ref + (SFSamples * span)) # define end for the next possible peak detection

    peaks = []
    # TODO: what if there are more upchirps in preamble??
    for i in range(1, 9):
        state = "searchingFallingEdge"

        if downlink:
            yEnvDiff = np.diff(freqInTime(np.conj(sig[nextStart:nextEnd])), 1)
        else:
            yEnvDiff = np.diff(freqInTime(sig[nextStart:nextEnd]), 1) # envelope specific part of the signal

        found, state, startIndex = detectEdges(yEnvDiff, threshold, state) # detect peak at estimated area
        mins.extend(found)

        if state == "searchingRisingEdge": # if in given area of signal peak didn't end - continue in its searching
            iterator = 0
            while state == "searchingRisingEdge":
                yEnvDiffEx = np.diff(freqInTime(sig[nextEnd:int(nextEnd + (SFSamples * span))]), 1)
                yEnvDiff = np.hstack([yEnvDiff, yEnvDiffEx])
                found, state, _ = detectEdges(yEnvDiff, threshold, state, startIndex, (len(yEnvDiff) - len(yEnvDiffEx)), True) # deteck minimum peak
                mins.extend(found)
            
                nextEnd += int(SFSamples * span)

                if iterator > 3:
                    break

                iterator += 1

        if len(mins) >= 1: # if there is atleast one found peak
            minsSorted = sorted(mins, key = lambda el: el[0])[:1] # take one with lowest value
            peakPos = int(minsSorted[0][1] + nextStart) # calculate its position in whole signal

            if isFirst:
                isFirst = False
                difference = 0
                ref = peakPos
                firstOffset = peakPos - SFSamples
                period = peakPos - firstOffset
            else:
                period = peakPos - ref
                ref, difference, span = recalculateSpan(peakPos, ref + SFSamples, lastDifference, span, SFSamples, SPAN_COEFFICIENT)
            
            lastIndex = peakPos
            lastDifference = difference
            peaks.append(period)

            lastConfirmedSymbol = i

            mins = []
        else:
            ref += SFSamples
            newSpan = span + (span * SPAN_COEFFICIENT)
            if int(newSpan * SFSamples) > MINIMUM_SPAN_SAMPLES and int(newSpan * SFSamples) < (SFSamples//2):
                span = newSpan

        nextStart = int((ref + SFSamples) - (SFSamples * span)) # define start for the next possible peak detection
        nextEnd = int((ref + SFSamples) + (SFSamples * span)) # define end for the next possible peak detection


    return peaks, lastConfirmedSymbol, lastIndex

def getSignalPeriod(periods):
    """
    Returns period of signal as integer.

    Parameters
    ----------
    periods : array
        Found periods between peaks.
    """

    # in order to get rid of possible outliers, given to the span is established from which periods final period would be calculated
    s = int(len(periods) * PERIOD_SPAN)
    e = int(len(periods) * (1 - PERIOD_SPAN))
    
    # sort periods and take those who are in given range
    sort = sorted(periods)[s:e]

    # calculate average and return it as final period
    return int(sum(sort) / len(sort))

    
def searchForPeakCount(results, invalid = []):
    """
    Spreading Factor with highest peak count has highest probability to be correct signal's Spreading Factor. For that reason
    are searched all Spreading Factors and maximum peak count between them is found.

    Parameters
    ----------
    results : array
        Array of dictionaries containing informations if some peak was found for given Spreading Factor and how many peaks were found.
    invalid : array
        Contains all Spreading Factors from previous iterations at which period did not fit.

    Returns
    -------
    candidates : array
        Spreading Factor with highest peak count. If there are many with same highest peak count, all are returned.
    """

    candidates = []
    maxValue = 0

    for i in range(len(results)): # search through all results
        if results[i][VALID_SFS[i]]["found"]:  # continue, if for given SF there were found some peaks
            if results[i][VALID_SFS[i]]["peakCount"] > maxValue and (i + VALID_SFS[0]) not in invalid:  # if current SF has higher peak count (and its presence was not in previous iterations) than previous one, store it as new SF with highest peak count
                candidates = []
                maxValue = results[i][VALID_SFS[i]]["peakCount"]
                candidates.append(i + VALID_SFS[0])
            elif results[i][VALID_SFS[i]]["peakCount"] == maxValue and (i + VALID_SFS[0]) not in invalid: # if current SF has same peak count (and its presence was not in previous iterations) as some previous ones, store it also
                candidates.append(i + VALID_SFS[0])

    return candidates

def chooseSF(candidates, results, samples):
    """
    Returns all possible signal's Spreading Factors based on calculated period.

    Parameters
    ----------
    candidates : array
        Possible candidates for signal's true Spreading Factor.
    results : array
        Array of dictionaries containing informations for given SF. Based on periods of peaks is estimated signal's period. After that is decided 
        if estimated period belongs into the borders based on SF's samples per symbol (= period) and period variance.
    samples : dict
        Contains samples per symbol for all valid Spreading Factors.


    Returns
    -------
    credible : array
        Spreading factors that are in given boundaries.
    """

    credible = []
    for sf in candidates:
        arrPos = sf - VALID_SFS[0] # calculate correct position in array of results
        peaks = results[arrPos][sf]["peaks"]
        if len(peaks) >= 2: # if there are atleast two peak, estimate period
            finalPeriod = getSignalPeriod(peaks)
        else: # otherwise skip
            continue 
        
        SFPeriod = samples[SF_SAMPLES_N[arrPos]] # period for current Spreading Factor
        if abs(finalPeriod - SFPeriod) < int(SFPeriod * PERIOD_VARIANCE): # if estimated period is in boundaries, store informations for future usage
            valid = {}
            valid["SF"] = sf
            valid["lastIndex"] = results[arrPos][sf]["lastIndex"]
            valid["lastSymbol"] = results[arrPos][sf]["lastSymbol"]
            valid["period"] = finalPeriod
            credible.append(valid)

    return credible

def findSignalSF(y, fSample, bw, downlink):
    # TODO: Do description
    # GET SAMPLES PER SYMBOL FOR EACH SF
    samplesPerSymbol = caulcateSamples(bw, fSample)

    # SET WINDOW IN WHICH IS THRESHOLD DETERMINED
    skip = int((((2**VALID_SFS[0]) / bw) * SF_THRESHOLD_SKIP) * fSample)
    skipEnd = skip + int(samplesPerSymbol[SF_7_SAMPLES_N] * SF_THRESHOLD_SKIP_END)

    envelopeResult = getSFDetectionThreshold(y[skip:skipEnd], SF_THRESHOLD_COEFFICIENT)

    results = []
    # TODO: use paralization
    for i in range(len(VALID_SFS)):
        if not (((8 * samplesPerSymbol[SF_SAMPLES_N[i]]) + samplesPerSymbol[SF_SAMPLES_N[i]]//2) > len(y)): # There is no need to check, if the length of signal is less than the length of the 8 first up-chirps for given SF
            signalPeaks, last, idx = findPreamblePeaks(y, envelopeResult, samplesPerSymbol[SF_SAMPLES_N[i]], INITIAL_PEAK_SPAN, int(TIME_OFFSET / (SAMPLING_FREQUENCY / fSample)), downlink)
            if len(signalPeaks) == 0:
                print("NO PERIOD FOUND FOR SF %s" %(VALID_SFS[i]))
                result = {}
                result[VALID_SFS[i]] = {}
                result[VALID_SFS[i]]["found"] = False
                results.append(result)
            else:
                result = {}
                result[VALID_SFS[i]] = {}
                result[VALID_SFS[i]]["found"] = True
                result[VALID_SFS[i]]["lastSymbol"] = last
                result[VALID_SFS[i]]["peakCount"] = len(signalPeaks)
                result[VALID_SFS[i]]["peaks"] = signalPeaks
                result[VALID_SFS[i]]["lastIndex"] = idx
                results.append(result)
                print("FOUND PERIOD FOR SF %s" %(VALID_SFS[i]))
        else:
            print("NO PERIOD FOUND FOR SF %s" %(VALID_SFS[i]))
            result = {}
            result[VALID_SFS[i]] = {}
            result[VALID_SFS[i]]["found"] = False
            results.append(result)
    
    maxes = searchForPeakCount(results)

    resultSFs = chooseSF(maxes, results, samplesPerSymbol)
    if len(resultSFs) == 0:
        invalid = maxes
        maxes = searchForPeakCount(results, invalid)
        resultSFs = chooseSF(maxes, results, samplesPerSymbol)

    return resultSFs


def detectPreamble(y, fs, bw, downlink=False):
    # TODO: Do description
    # FIND SIGNAL'S SF
    sfs = findSignalSF(y, fs, bw, downlink)
    maxCorr = INITIAL_CORRELATION_COEFFICIENT
    finDown = np.array([])
    preambleEnd = 0
    period = 0
    sf = 0
    signalStart = 0
    finPeriod = 0
    found = False
    invalid = False
    # VARIABLES FOR SPECIFIC SF
    if len(sfs) >= 1:
        for el in sfs:
            # GENERATE DOWN-CHIRP
            period = el["period"]
            lastIndex = el["lastIndex"]
            lastSymbol = el["lastSymbol"]

            wDown = np.conj(y[lastIndex - period: lastIndex]) # there is possibility to use known preamble symbol

            # CREATE 2,25 DOWN-CHIRP
            wDown2 = np.hstack([wDown, wDown, wDown[:period//4]])
            wDownFreq = freqInTime(wDown2)

            # GET NUMBER OF SAMPLES FOR GENERATED 2,25 DOWN-CHIRP
            nWdownFreq2 = len(wDown2)

            # FIND END OF PREAMBLE
            correlations = []
            firstStart = lastIndex
            start = firstStart # start from the last known up-chirp
            end = start + nWdownFreq2 # take length of 2,25 symbol
            if end > len(y):
                continue
            starts = []

            # TODO: what if there are more upchirps in preamble??
            for i in range(13 - lastSymbol):
                correlations.append(np.corrcoef(freqInTime(y[start:end]), wDownFreq)[0, 1]) # correlate 2,25 signal's symbols with 2,25 of down-chirp signal
                starts.append(start)
                start = start + period # move by symbol
                end = end + period
                if end > len(y):
                    invalid = True
                    break
            
            if invalid:
                invalid = False
                continue

            maxIndex = np.argmax(correlations) # find highest correlation
            highestCorr = correlations[maxIndex]
            if highestCorr > maxCorr:
                maxCorr = highestCorr
                preambleEnd = starts[maxIndex]  + nWdownFreq2 # determine end of preamble based on position of 2,25 down-chirp
                finDown = wDown
                finPeriod = el["period"]
                sf = el["SF"]
                found = True
                signalStart = lastIndex - (lastSymbol*period)
                if signalStart < 0:
                    signalStart = 0

    return preambleEnd, finDown, finPeriod, sf, signalStart, found

def dechirpSignal(y, w, period):
    # TODO: Do description
    start = 0
    end = start + len(w)
    dechirped = np.array([])

    while end <= len(y):
        dechirped = np.concatenate([dechirped, y[start:end] * w]) # to de-chirp signal multiply each symbol of signal with down-chirp
        start += period # move by symbol
        end += period

    return dechirped

def getPreambleIndex(y, period, fftFactor):
    # TODO: Do description
    start = 0
    end = start + period
    indexes = []
    N = fftFactor*period
    while end <= len(y):
        sym = y[start + int(FFT_DISTANCE * period) : end - int(FFT_DISTANCE * period)]
        Sxx = np.fft.fft(sym, n=N)
        idx = np.argmax(np.abs(Sxx))
        indexes.append(idx)
        start += period # move by symbol
        end += period

    return max(indexes,key=indexes.count)

def getSymbolValues(y, period, premIdx, fftFactor, sf):
    # TODO: Do description
    start = 0
    end = start + period
    values = []
    N = fftFactor*period
    premIdx = premIdx / fftFactor

    while end <= len(y):
        sym = y[start + int(FFT_DISTANCE * period) : end - int(FFT_DISTANCE * period)]
        Sxx = np.fft.fft(sym, n=N)

        idx = np.argmax(np.abs(Sxx))
        value = int(((idx/fftFactor) - premIdx) % 2**sf) # calculate value      
        values.append(value)
        start += period # move by symbol
        end += period

    return values

def demodulateSignal(sig, fs, bw, factor):
    """
    Estimate signal's beginning, Spreading Factor, symbol period and end of preamble. Do dechirp proccess abd returns values for each data symbol.

    Parameters
    ----------
    sig : array
        IQ samples to demodulate.
    fs : int
        Sampling frequency.
    bw : int
        Signal's bandwidth.
    factor : int
        FFT factor.

    Returns
    -------
    symVals : array
        Data's symbol values.
    sf : int
        Signal's Spreading Factor.
    """

    # Estimate signal's beginning, Spreading Factor, symbol period, end of preamble and downchirp
    premEnd, w, period, sf, signalBeg, found = detectPreamble(sig, fs, bw)
    
    # Dechirp signal's preamble
    preamble = dechirpSignal(sig[signalBeg:8*period+period//4+signalBeg], w, period)

    # Get premable's index
    premVal = getPreambleIndex(preamble, period, factor, sf)

    # Dechirp signal's data symbols
    data = dechirpSignal(sig[premEnd:], w, period)

    # Get value for each data symbol
    symVals = getSymbolValues(data, period, premVal, factor, sf)

    return symVals, sf