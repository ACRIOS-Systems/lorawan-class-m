from lora_sim_lib.Time import Time
from lora_sim_lib.LoRaParameters import PacketParameters
import math
import random
import copy
#from NetObject import NetObject

PCKT_ID = 0

class Packet:
    def __init__(self, TxObj, par: dict, data: bytes, time: Time) -> None:
        # packet ID
        global PCKT_ID
        self._id = PCKT_ID
        PCKT_ID += 1

        # save radio parameters
        self._packetParam = PacketParameters(
                frequency           = par["frequency"],
                bandwidth_kHz       = par["bandwidth_kHz"],
                spreading_factor    = par["spreading_factor"],
                coding_rate         = par["coding_rate"],
                iq_inverted         = par["iq_inverted"],
                low_data_rate       = par["low_data_rate"],
                implicit_header     = par["implicit_header"],
                crc_en              = par["crc_en"],
                preamble_length     = par["preamble_length"],
                power               = par["power"], #Tx power
                # momentarily unused - "ramp_time", "tx_timeout"
            )

        # save transmitter of this object
        self.TxObj = TxObj

        # save data
        self._data = data

        # save packet size
        self._size = par["size"]

        # save important timestamps
        #self._criticalSectionStartTime = Time(ms = self.criticalSectionStart())
        #self._preambleEndTime = self._startTime + self.preambleTime()
        #self._endTime = self._startTime + self.timeOnAir()

        self._startTime = time.copy()
        self.calculateTimestamps()

    # End of init()


    @property
    def id(self) -> int:
        return self._id

    @property
    def packetParam(self) -> PacketParameters:
        return self._packetParam

    @property
    def data(self) -> bytes:
        return self._data

    @property
    def preambleLength(self):
        return self.packetParam.preamble_length

    @property
    def payloadLength(self):
        return self._size

    @property
    def startTime(self):
        return self._startTime

    @property
    def criticalSectionStartTime(self):
        return self._criticalSectionStartTime

    @property
    def preambleEndTime(self):
        return self._preambleEndTime

    @property
    def headerEndTime(self):
        return self._headerEndTime

    @property
    def endTime(self):
        return self._endTime



    def calculateTimestamps(self):
        n_pream = self.packetParam.preamble_length      # https://www.google.com/patents/EP2763321A1?cl=en
        t_sym = (2.0 ** self.packetParam.spreading_factor) / (self.packetParam.bandwidth_kHz / 1000.0) # in us!
        t_pream = (n_pream + 4.25) * t_sym
        t_critical = t_sym * (n_pream - 5)
        payload_symb_n_b = 8 + max(
            math.ceil(
                (
                        8.0 * self._size - 4.0 * self.packetParam.spreading_factor + 28 + 16 * self.packetParam.crc_en - 20 * self.packetParam.implicit_header) / (
                        4.0 * (self.packetParam.spreading_factor - 2 * self.packetParam.low_data_rate)))
            * (self.packetParam.coding_rate), 0) # coding_rate is expected in range 5-8
        t_payload = payload_symb_n_b * t_sym

        self._preambleEndTime = self.startTime + Time(us=t_pream)
        self._criticalSectionStartTime = self.startTime + Time(us=t_critical)
        self._endTime = self.preambleEndTime + Time(us=t_payload)

        self._headerEndTime = None
        if self.packetParam.implicit_header == 0:
            # If present, the header is always encoded in the first 8 symbols
            self._headerEndTime = self.preambleEndTime + Time(us=8.0*t_sym)


    def corruptData(self):
        p = copy.copy(self)
        data = bytearray(p.data)
        n = int(len(data)*8*0.5) # Number of bits to be corrupted (50%)

        for _ in range(n):
            byteIndex = random.randint(0, len(data) - 1)
            bitIndex = random.randint(0, 7)
            data[byteIndex] ^= (1<<bitIndex)
        data = bytes(data)
        p._data = data
        return p


#    def timeOnAir(self):
#        n_pream = self.packetParam.preamble_length  # https://www.google.com/patents/EP2763321A1?cl=en
#
#        t_sym = (2.0 ** self.packetParam.spreading_factor) / (self.packetParam.bandwidth_kHz / 1000.0)      # in us, therefore bw in MHz
#        t_pream = (n_pream + 4.25) * t_sym
#        payload_symb_n_b = 8 + max(
#            math.ceil(
#                (
#                        8.0 * self._size - 4.0 * self.packetParam.spreading_factor + 28 + 16 * self.packetParam.crc_en - 20 * self.packetParam.implicit_header) / (
#                        4.0 * (self.packetParam.spreading_factor - 2 * self.packetParam.low_data_rate)))
#            * (self.packetParam.coding_rate), 0) # coding_rate is expected in range 5-8
#        t_payload = payload_symb_n_b * t_sym
#
#        return Time.Time(us = t_pream + t_payload)
#
#    def preambleTime(self):
#        n_pream = self.packetParam.preamble_length  # https://www.google.com/patents/EP2763321A1?cl=en
#
#        t_sym = (2.0 ** self.packetParam.spreading_factor) / self.packetParam.bandwidth_kHz * 1000
#        t_pream = (n_pream + 4.25) * t_sym
#        return Time.Time(us = t_pream)
#
#    def criticalSectionStart(self):
#        symDuration = 2 ** self.packetParam.spreading_factor / (1.0 * self.packetParam.bandwidth_kHz) # in ms
#        numPreamble = 8
#        return self.startTime.ms + symDuration * (numPreamble - 5)
