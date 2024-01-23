from receiver import SDRReceive, createRadio
from preprocessor import estimateBandwidth, detectCarrierFrequency, downConvertSignal, downSampleSignal
from demodulator import detectPreamble, dechirpSignal, getPreambleIndex, getSymbolValues
from decoder import decodeExplicitHeader, decodeValues, getLoRaWANPayload
from config import (EXPLICIT_HEADER_LEN, SAMPLING_FREQUENCY, CARRIER_SIZE, T_OFFSET, FFT_FACTOR, DOWNSAMPLING_FREQUENCIES, IS_LORAWAN)
from WiresharkStreamer import WiresharkStreamer
import time

def processSDROutput(input, streamer, timestamp):
    """
    Apply all procedures to decode received signal.

    Parameters
    ----------
    input : array
        Received signal.
    streamer : WiresharkStreamer.WiresharkStreamer
        Interface to pass decoded data.
    timestamp : float
        Current timestamp.
    """


    ###### PREPROCESSOR ######
    # Find signal's carrier frequency
    carrier = detectCarrierFrequency(input, SAMPLING_FREQUENCY, T_OFFSET, CARRIER_SIZE)

    # Downconvert signal to the estimated carrier frequency
    downconverted = downConvertSignal(input, SAMPLING_FREQUENCY, carrier)

    # Estimate bandwidth
    bw = estimateBandwidth(downconverted, SAMPLING_FREQUENCY, T_OFFSET)
    if bw == 0:
        print("BANDWIDTH not found")
        return

    # Choose downsampling frequency based on bandwidth
    fsd = DOWNSAMPLING_FREQUENCIES[int(bw/125e3)-1]

    # Downsample signal
    downsampled = downSampleSignal(downconverted, SAMPLING_FREQUENCY, fsd)


    ###### DEMODULATOR ######
    # Estimate signal's beginning, Spreading Factor, symbol period, end of preamble and downchirp
    isDowlink = 0
    premEnd, w, period, sf, signalBeg, found = detectPreamble(downsampled, fsd, bw)
    if not found:
        print("SPREADING FACTOR not found for uplink")
        print("Try downlink...")
        premEnd, w, period, sf, signalBeg, found = detectPreamble(downsampled, fsd, bw, True)
        if not found:
            return
        else:
            isDowlink = 1
    
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
    isExplicit, isCRC, cr, rest, pLen = decodeExplicitHeader(symVals[:EXPLICIT_HEADER_LEN], sf)
    if pLen == 0:
        return
    toDecode = []

    if isExplicit:
        toDecode = symVals[EXPLICIT_HEADER_LEN:]
    else:
        # TODO: should be probably implicit message, not yet supported
        return
    
    # Decode demodulated values
    decoded = decodeValues(toDecode, sf, bw, isCRC, cr, rest, pLen)


    ###### OUTPUT ######
    # Create LoRaTap header
    header = {}
    header["crc_en"] = 0
    header["frequency"] = int(868.5e6)
    header["bandwidth_kHz"] = int(bw/125000) # TODO: 500 khz bug
    header["spreading_factor"] = int(sf)
    header["implicit_header"] = 1
    header["coding_rate"] = cr
    header["iq_inverted"] = isDowlink

    if IS_LORAWAN:
        outWAN = getLoRaWANPayload(decoded)
        if len(outWAN) != 0:
            decoded = outWAN

    # Create bytes
    payload = b''
    for b in decoded:
        payload += b.to_bytes(2, "big")
    
    # Send to wireshark
    streamer.packet(node_id=0, ts = timestamp, par = header, data = payload)

if __name__ == "__main__":
    radio = createRadio(fc=869525000, rxRfBw=200000, fs = 1000000, buffer = 2500000)
    streamer = WiresharkStreamer() # wireshark -i udpdump -k
    debug = False

    while True:
        try:
            output = SDRReceive(radio, 100000, debug)

            if debug:
                break

            if len(output) != 0:
                ts = time.time()
                processSDROutput(output, streamer, ts)
            else:
                print("Nothing found...")

        except Exception as e:
            print(str(e))