import math
import numpy as np
import cmath

def nibbleToBinary(nibble):
    # Convert the data to binary representation and remove '0b' prefix
    toBin = bin(nibble)[2:]

    # Pad the binary digits to the desired length
    padBin = toBin.zfill(4)

    # Convert each character in the padded binary string to an integer
    return [int(char) for char in padBin]

def listToInt(values):
    toInt = []
    for binary in values:
        toStr = ''.join(map(str, binary))
        toInt.append(int(toStr, 2))

    return toInt

# Parity calculation
def encodeCR1(nibble):
    # Convert to binary array
    nibble = nibbleToBinary(nibble)

    # Count the number of 1 bits in the nibble
    ones = sum(1 for bit in nibble if bit == 1)
    
    # Calculate the parity bit
    p1 = 0 if ones % 2 == 0 else 1
    
    # Concatenate the nibble bits and the parity bits    
    return [p1, nibble[0], nibble[1], nibble[2], nibble[3]]

# Parity calculation
def encodeCR2(nibble):
    # Convert to binary array
    nibble = nibbleToBinary(nibble)

    # Calculate the first parity bit
    p1 = nibble[0] ^ nibble[1] ^ nibble[2] ^ nibble[3]
    
    # Calculate the second parity bit
    p2 = (nibble[0] ^ nibble[1]) ^ (nibble[2] ^ nibble[3])
    
    # Concatenate the nibble bits and the parity bits    
    return [p1, p2, nibble[0], nibble[1], nibble[2], nibble[3]]

# Hamming (7, 4)
def encodeCR3(nibble):
    # Convert to binary array
    nibble = nibbleToBinary(nibble)

    # Create the parity bits
    p1 = nibble[0] ^ nibble[1] ^ nibble[3]
    p2 = nibble[0] ^ nibble[2] ^ nibble[3]
    p3 = nibble[1] ^ nibble[2] ^ nibble[3]
    
    # Concatenate the nibble bits and the parity bits    
    return [p1, p2, p3, nibble[0], nibble[1], nibble[2], nibble[3]]

# Hamming (8, 4)
def encodeCR4(nibble):
    # Convert to binary array
    nibble = nibbleToBinary(nibble)

    # Create the parity bits
    p1 = nibble[0] ^ nibble[1] ^ nibble[3]
    p2 = nibble[0] ^ nibble[2] ^ nibble[3]
    p3 = nibble[1] ^ nibble[2] ^ nibble[3]
    p4 = nibble[0] ^ nibble[1] ^ nibble[2] ^ nibble[3] ^ p1 ^ p2 ^ p3
    
    # Concatenate the nibble bits and the parity bits
    return [p1, p2, p4, p3, nibble[0], nibble[1], nibble[2], nibble[3]]


def interleaver(codewords, sf, cr):
    codewordsCount = len(codewords)//sf
    interleaved = [0] * (codewordsCount * (cr + 4))
    for i in range(codewordsCount):
        # {0, 1}^(SF x (4 + CR))
        cwOff = i*sf
        symOff = i*(cr + 4)
        for j in range(cr + 4):
            for k in range(sf):
                v = (k + j + sf) % sf
                bit = (codewords[cwOff + v] >> j) & 0x1
                interleaved[symOff + j] |= (bit << k)

    return interleaved


def whitening(grayed, cr):
    whitened = [0] * len(grayed)

    ofs0 = [6,4,2,0,-112,-114,-302,-34]
    ofs1 = [6,4,2,0,-360]
    whiten_len = 510
    whiten_seq = [0x0102291EA751AAFF,0xD24B050A8D643A17,0x5B279B671120B8F4,0x032B37B9F6FB55A2,
    0x994E0F87E95E2D16,0x7CBCFC7631984C26,0x281C8E4F0DAEF7F9,0x1741886EB7733B15]

    if cr == 1:
        ofs = ofs1
    else:
        ofs = ofs0

    for i in range(len(grayed)):
        x = 0
        for j in range(cr + 4):
            t = (ofs[j] + i + whiten_len) % whiten_len
            if whiten_seq[t >> 6] & (1 << (t & 0x3F)):
                x |= 1 << j

        whitened[i] = grayed[i] ^ x

    return whitened

def grayDecode(whitened):
    for i in range(len(whitened)):
        whitened[i] = whitened[i] ^ (whitened[i] >> 16)
        whitened[i] = whitened[i] ^ (whitened[i] >>  8)
        whitened[i] = whitened[i] ^ (whitened[i] >>  4)
        whitened[i] = whitened[i] ^ (whitened[i] >>  2)
        whitened[i] = whitened[i] ^ (whitened[i] >>  1)
    
    return whitened

def modulate(N, sym=0, numSamps=None):
    if numSamps is None: numSamps = N
    phase = -math.pi
    samps = list()
    accum = 0
    off = (2*math.pi*sym)/N
    for i in range(numSamps):
        accum += phase + off
        samps.append(cmath.rect(1.0, accum))
        phase += (2*math.pi)/numSamps
    return np.array(samps)

def modulateReal(bw, fs, sf, value):
    chips = 2**sf
    symbolDuration = chips/bw
    samplesPerSymbol = int(symbolDuration*fs)
    t = np.linspace(0, symbolDuration, samplesPerSymbol)
    
    fStart = (value/chips) * bw
    offset = int(((bw - fStart)/bw)*samplesPerSymbol)

    # Generate chirp signal
    generatedChirp = np.exp(1j * 2 * np.pi * (0 * t + (bw - 0) * t**2 / (2 * symbolDuration)))

    chirp = np.hstack([generatedChirp[samplesPerSymbol - offset:], generatedChirp[:samplesPerSymbol - offset]])

    return chirp

def generateDownchirp(bw, fs, sf):
    chips = 2**sf
    symbolDuration = chips/bw
    samplesPerSymbol = int(symbolDuration*fs)
    tw = np.linspace(0, symbolDuration, samplesPerSymbol)


    wDown = np.exp(1j * 2 * np.pi * (bw * tw + (0 - bw) * tw**2 / (2 * symbolDuration)))

    return wDown

if __name__ == "__main__":
    # nibble = "dGVzdERhdGE="
    sf = 8
    cr = 1

    bytes = [74, 65, 73, 74, 44, 61, 74, 61]
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
    
    pass

    