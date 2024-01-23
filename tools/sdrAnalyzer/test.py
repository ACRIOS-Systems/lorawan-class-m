import os
import numpy as np
from preprocessor import detectCarrierFrequency, downConvertSignal, estimateBandwidth, downSampleSignal
from demodulator import detectPreamble, dechirpSignal, getSymbolValues, getPreambleIndex
from decoder import decodeValues, decodeExplicitHeader
from config import (EXPLICIT_HEADER_LEN, SAMPLING_FREQUENCY, CARRIER_SIZE, T_OFFSET, FFT_FACTOR, DOWNSAMPLING_FREQUENCIES, VALIDS_BWS)
import json

def generateSequence(start, g = False):
    if g:
        b = ''
    else:
        b = []

    lfsr = start
    for _ in range(start):
        bit = (lfsr ^ (lfsr >> 1) ^ (lfsr >> 3) ^ (lfsr >> 12)) & 1
        lfsr = (lfsr >> 1) | (bit << 15)
        if g:
            b += "\%s" % str((lfsr >> 8))
            # b += (lfsr >> 8).to_bytes(1, "big")
        else:
            b.append((lfsr >> 8))

    if g:
        return f'api.p2p_tx("{b}", 868500000, 7, 1, 1, 10, 0, 0)'
    else:
        return b
    

if __name__ == "__main__":
    generating = False

    if generating:
        output = generateSequence(44, generating)
        print(output)
    else:
        with open("testedFiles.txt", "w") as fwf:
            fwf.write("Tested files: \n")

        with open("invalidPayloads.txt", "w") as fwp:
            fwp.write("Invalid: \n")

        path = os.getcwd() + "/catched/test/"
        files = os.listdir(path)

        for f in files:
            print("***************************")
            print("Testing file: %s" %(f))
            payFail = False
            source = np.load(path + f)
            splitted = f[:-4].split("_")
            sfF = int(splitted[0])
            crF = int(splitted[1])
            bwF = int(splitted[2])
            lnF = int(splitted[3])
            head = splitted[4]
            isExplicitF = False
            if head == "exp":
                isExplicitF = True

            ###### PREPROCESSOR ######
            # Find signal's carrier frequency
            carrier = detectCarrierFrequency(source, SAMPLING_FREQUENCY, T_OFFSET, CARRIER_SIZE)

            # Downconvert signal to the estimated carrier frequency
            downconverted = downConvertSignal(source, SAMPLING_FREQUENCY, carrier)

            # Estimate bandwidth
            bw = estimateBandwidth(downconverted, SAMPLING_FREQUENCY, T_OFFSET)
            if bw == 0 or bw != VALIDS_BWS[bwF]:
                print("! FAILED !")
                print("Bandwidths do not match !")
                print("Source bw is - %s estimated bw is - %s" %(VALIDS_BWS[bwF], bw))
                err = "Bandwidth S:%s/E:%s" %(VALIDS_BWS[bwF], bw)
                with open("testedFiles.txt", "a") as fwf:
                    fwf.write("File: %s - FAILED, reason: %s \n" %(f, err))
                continue

            # Choose downsampling frequency based on bandwidth
            fsd = DOWNSAMPLING_FREQUENCIES[int(bw/125e3)-1]

            # Downsample signal
            downsampled = downSampleSignal(downconverted, SAMPLING_FREQUENCY, fsd)


            ###### DEMODULATOR ######
            # Estimate signal's beginning, Spreading Factor, symbol period, end of preamble and downchirp
            premEnd, w, period, sf, signalBeg, found = detectPreamble(downsampled, fsd, bw)
            if not found:
                print("SPREADING FACTOR not found for uplink")
                print("Try downlink...")
                premEnd, w, period, sf, signalBeg, found = detectPreamble(downsampled, fsd, bw, True)

            if not found or sf != sfF:
                print("! FAILED !")
                print("Spreading Factors do not match !")
                print("Source Spreading Factor is - %s estimated Spreading Factor is - %s" %(sfF, sf))
                err = "Spreading Factor S:%s/E:%s" %(sfF, sf)
                with open("testedFiles.txt", "a") as fwf:
                    fwf.write("File: %s - FAILED, reason: %s \n" %(f, err))
                continue

            # Dechirp signal's preamble
            preamble = dechirpSignal(downsampled[signalBeg:8*period+period//4+signalBeg], w, period)

            # Get premable's index
            premVal = getPreambleIndex(preamble, period, FFT_FACTOR)

            # Dechirp signal's data symbols
            data = dechirpSignal(downsampled[premEnd:], w, period)

            # Get value for each data symbol
            symVals = getSymbolValues(data, period, premVal, FFT_FACTOR, sf)


            ###### DECODER ######
            # Estimate if there is explicit header
            # TODO: if values < EXPLICIT_HEADER_LEN => SKIP
            isExplicit, isCRC, cr, rest, pLen = decodeExplicitHeader(symVals[:EXPLICIT_HEADER_LEN], sf)
            if isExplicitF:
                if not isExplicit:
                    print("! FAILED !")
                    print("Message should be explicit !")
                    err = "Header S:Explicit"
                    with open("testedFiles.txt", "a") as fwf:
                        fwf.write("File: %s - FAILED, reason: %s \n" %(f, err))
                    continue

                if cr != crF:
                    print("! FAILED !")
                    print("Coding Rates do not match !")
                    print("Source cr is - %s estimated cr is - %s" %(crF, cr))
                    err = "Coding Rate S:%s/E:%s" %(crF, cr)
                    with open("testedFiles.txt", "a") as fwf:
                        fwf.write("File: %s - FAILED, reason: %s \n" %(f, err))
                    continue

            toDecode = []
            if isExplicit:
                toDecode = symVals[EXPLICIT_HEADER_LEN:]
            
            # Decode demodulated values
            decoded = decodeValues(toDecode, sf, bw, isCRC, cr, rest, pLen)
            
            seq = generateSequence(lnF)
            invalid = {}
            invalid[f] = {}
            it = 0
            if len(decoded) != len(seq):
                print("! FAILED !")
                print("Lenghts of payloads do not match !")
                print("Source lenght is - %d estimated lenght is - %d" %(len(seq), len(decoded)))
                err = "Payload lenght S:%d/E:%d" %(len(seq), len(decoded))
                with open("testedFiles.txt", "a") as fwf:
                    fwf.write("File: %s - FAILED, reason: %s \n" %(f, err))
                continue

            for i in range(lnF):
                if decoded[i] != seq[i]:
                    it += 1
                    payFail = True
                    invalid[f][i] = {}
                    invalid[f][i]["source"] = seq[i]
                    invalid[f][i]["decoded"] = decoded[i]

            if payFail:
                print("! FAILED !")
                print("Payloads do not match !")
                with open("invalidPayloads.txt", "a") as fwp:
                    fwp.write("*************************** \n")
                    fwp.write(json.dumps(invalid, indent=2))
                
                err = "Payload - Wrong/Total: [%d/%d] bytes" %(it, lnF)
                with open("testedFiles.txt", "a") as fwf:
                    fwf.write("File: %s - FAILED, reason: %s \n" %(f, err))
            else:
                print("! Everything is OK !")
                with open("testedFiles.txt", "a") as fwf:
                    fwf.write("File: %s - PASSED \n" %(f))