from lora.crypto import loramac_decrypt
from config import (EXPLICIT_HEADER_LEN, EXPLICIT_HEADER_CODEWORDS, EXPLICIT_HEADER_CR, LDR_MS, 
                    VALID_CRS, W_SEQ, CR_5_8, CR_6_8, CR_7_8, CR_8_8, LOW_NIBBLE_MASK, HIGH_NIBBLE_MASK, KEYS)

def intToBinaryList(num, sf):
    """
    Converts integer into binary list.

    Parameters
    ----------
    num : int
        Value to be converted.
    sf : int
        If needed, fills zeroes corresponding to the value of sf.
    """

    return [int(digit) for digit in bin(num)[2:].zfill(sf)]

def binaryListToInt(bin):
    """
    Converts binary list into integer.

    Parameters
    ----------
    bin : array
        Array to be converted.
    """

    return int("".join(str(x) for x in bin), 2)

def gray(val):
    """
    Returns gray encoded value.

    Parameters
    ----------
    val : int
        Demodulated value to be encoded.
    """

    return val ^ (val >> 1) 

def deinterleave(grayed, sf, cwLen):
    """
    Returns deinterleaved values.

    Parameters
    ----------
    grayed : array
        Values to be deinterleaved.
    sf : int
        Signal's Spreading Factor.
    cwLen : int
        Length of codewords.

    Returns
    -------
    deinterleaved : array
        Deinterleaved values => codewords.
    """

    # Pre-create array to store codewords
    deinterleaved = []
    for f in range(sf):
        deinterleaved.append([0] * cwLen)

    # Convert integers to binary list
    grayedBin = []
    for g in grayed:
        grayedBin.append(intToBinaryList(g, sf))

    # Do the deinterleaving
    for i in range(cwLen):
        for j in range(sf):
            pos = (i - j - 1) % sf
            deinterleaved[pos][i] = grayedBin[i][j]

    return deinterleaved

def hammingDecode(codeword, cr):
    """
    Returns hamming decoded value.

    Parameters
    ----------
    codeword : array
        Codewords to be decoded.
    cr : int
        Used Coding Rate.

    Returns
    -------
    dataInt : int
        Decoded value.
    error : bool
        Parity error.
    """

    # data bits
    data = [codeword[3], codeword[2], codeword[1], codeword[0]]

    err = False
    if cr == CR_8_8:
        # get syndrom
        s0 = (codeword[0] ^ codeword[1] ^ codeword[2] ^ codeword[4])
        s1 = (codeword[1] ^ codeword[2] ^ codeword[3] ^ codeword[5])
        s2 = (codeword[0] ^ codeword[1] ^ codeword[3] ^ codeword[6])
        s3 = (codeword[0] ^ codeword[2] ^ codeword[3] ^ codeword[7])
        s = s0 + (s1 << 1) + (s2 << 2) + (s3 << 3)

        # if needed, correct appropriate bit
        if s == 13:
            data[3] = data[3] ^ 0x01
        elif s == 7:
            data[2] = data[2] ^ 0x01
        elif s == 11:
            data[1] = data[1] ^ 0x01
        elif s == 14:
            data[0] = data[0] ^ 0x01
        elif s == 0:
            pass
        else:
            err = True
    elif cr == CR_7_8:
        # get syndrom
        s0 = codeword[0] ^ codeword[1] ^ codeword[2] ^ codeword[4]
        s1 = codeword[1] ^ codeword[2] ^ codeword[3] ^ codeword[5]
        s2 = codeword[0] ^ codeword[1] ^ codeword[3] ^ codeword[6]
        s = s0 + (s1 << 1) + (s2 << 2)

        # if needed, correct appropriate bit
        if s == 5:
            data[3] = data[3] ^ 0x01
        elif s == 7:
            data[2] = data[2] ^ 0x01
        elif s == 3:
            data[1] = data[1] ^ 0x01
        elif s == 6:
            data[0] = data[0] ^ 0x01
        elif s == 0:
            pass
        else:
            err = True
    elif cr == CR_6_8:
        s0 = codeword[0] ^ codeword[1] ^ codeword[2] ^ codeword[4]
        s1 = codeword[1] ^ codeword[2] ^ codeword[3] ^ codeword[5]

        if (s0 | s1) != 0:
            err = True
    elif cr == CR_5_8:
        if (codeword[0] ^ codeword[1] ^ codeword[2] ^ codeword[3] ^ codeword[4]) != 0:
            err = True
    
    dataInt = binaryListToInt(data)
    return dataInt, err

def dewhiten(low, high, off):
    """
    Applies dewhitening sequence on nibbles.

    Parameters
    ----------
    low : int
        Low nibble.
    high : int
        High nibble.
    off : int
        Offset to determine position in whitening sequence.

    Returns
    -------
    b : int
        Byte constructed from dewhitened nibbles.
    """

    # Apply dewhitening sequence
    low = low  ^ (W_SEQ[off] & LOW_NIBBLE_MASK)
    high = high ^ (W_SEQ[off] & HIGH_NIBBLE_MASK) >> 4

    # Construct byte
    b = (high << 4 | low)

    return b

def decodeExplicitHeader(header, sf):
    # TODO: Do description
    shifted = []
    for h in header:
        shifted.append(gray(h >> 2))

    codewords = deinterleave(shifted, (sf - 2), EXPLICIT_HEADER_LEN)

    cr, _ = hammingDecode(codewords[2], EXPLICIT_HEADER_CR)
    cr = cr >> 1
    isValid = False
    payLen = 0
    isCRC = 0

    if cr in VALID_CRS:
        data = []
        for c in codewords:
            outHamming, err = hammingDecode(c, EXPLICIT_HEADER_CR)
            data.append(outHamming)

        if err:
            print("Parity error !")
        checksum = ((data[3] & 1) << 4) + data[4]

        # header checksum
        c4 = (data[0] & 0b1000) >> 3 ^ (data[0] & 0b0100) >> 2 ^ (data[0] & 0b0010) >> 1 ^ (data[0] & 0b0001)
        c3 = (data[0] & 0b1000) >> 3 ^ (data[1] & 0b1000) >> 3 ^ (data[1] & 0b0100) >> 2 ^ (data[1] & 0b0010) >> 1 ^ (data[2] & 0b0001)
        c2 = (data[0] & 0b0100) >> 2 ^ (data[1] & 0b1000) >> 3 ^ (data[1] & 0b0001) ^ (data[2] & 0b1000) >> 3 ^ (data[2] & 0b0010) >> 1
        c1 = (data[0] & 0b0010) >> 1 ^ (data[1] & 0b0100) >> 2 ^ (data[1] & 0b0001) ^ (data[2] & 0b0100) >> 2 ^ (data[2] & 0b0010) >> 1 ^ (data[2] & 0b0001)
        c0 = (data[0] & 0b0001) ^ (data[1] & 0b0010) >> 1 ^ (data[2] & 0b1000) >> 3 ^ (data[2] & 0b0100) >> 2 ^ (data[2] & 0b0010) >> 1 ^ (data[2] & 0b0001)

        if (checksum == ((c4 << 4) + (c3 << 3) + (c2 << 2) + (c1 << 1) + c0)):
            print("Header checksum is valid")
            isValid = True
            payLen = (data[0] << 4) + data[1]
            isCRC = data[2] & 1
            return isValid, isCRC, cr, data[EXPLICIT_HEADER_CODEWORDS:], payLen
        else:
            print("Header checksum is invalid")
            return isValid, isCRC, cr, [], payLen
    else:
         print("Invalid CR - estimated CR is: %d" %(cr))
         return isValid, isCRC, cr, [], payLen

def calculateCRC(data):
    crc = 0x0000
    for i in range(len(data)):
        b = data[i] & 0xFF
        for _ in range(8):
            if (((crc & 0x8000) >> 8) ^ (b & 0x80)):
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF

            b = (b << 1) & 0xFF
        
    return crc

def checkCRC(dewhitened, pLen, payCrc):
    if len(payCrc) < 4:
        return False

    crc = calculateCRC(dewhitened[:pLen - 2]) 

    crc = crc ^ (dewhitened[pLen - 1] ^ (dewhitened[pLen - 2] << 8))
    
    if ((payCrc[1] << 4 | payCrc[0]) | ((payCrc[3] << 4 | payCrc[2]) << 8)) == crc:
        return True
    else:
        return False
    
def decodeValues(values, sf, bw, isCRC, cr, rest = [], pLen = 0):
    # TODO: Do description
    # TODO: Maybe for sake of paralization it would be better to operate with SF x CR blocks of values
    isLDR =  ((1 << sf) * 1e3 / bw) > LDR_MS
    if isLDR:
        sf -= 2

    grayed = []
    for v in values:
        v -= 1
        if isLDR:
            v = v >> 2
        grayed.append(gray(v))

    cwLen = 4 + cr
    s = 0
    e = s + cwLen
    deinterleaved = []
    while e <= len(grayed):
            deinterleaved.extend(deinterleave(grayed[s : e], sf, cwLen))
            s += cwLen
            e = s + cwLen

    data = []

    data.extend(rest) # append rest of the data from explicit header (if there are any)
    for d in deinterleaved:
        outHamming, err = hammingDecode(d, cr)
        data.append(outHamming)

    if err:
        print("Parity error !")

    dewhitened = []
    offset = 0
    for i in range(pLen):
        dewhitened.append(dewhiten(data[2 * i], data[2 * i + 1], offset))
        offset += 1

        if (i + 1) >= (len(data)//2):
            print("Payload length is bigger than received data")
            return dewhitened

    if isCRC:
        if checkCRC(dewhitened, pLen, data[2*pLen:]):
            print("CRC is valid")
        else:
            print("CRC is invalid")

    return dewhitened

def getLoRaWANPayload(b):
    devAddr = "".join(["%02X" % x for x in b[1:5][::-1]])
    optsLen = (b[5] & 0x0F)
    skip = 8 + optsLen
    sequenceCounter = int("".join(["%02X" % x for x in b[6:8][::-1]]), 16)
    pay = b[(skip+1):(skip+1) + (len(b[skip+1:]) - 4)]

    payload = "".join(["%02X" % x for x in pay])

    if devAddr in KEYS:
        if "appsKey" in KEYS[devAddr]:
            key = KEYS[devAddr]["appsKey"]
            decrypted = loramac_decrypt(payload, sequenceCounter, key, devAddr)
        else:
            return []
    else:
        return []
    
    return decrypted