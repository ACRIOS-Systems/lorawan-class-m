from time import time
import socket
from struct import pack, Struct
import re


class WiresharkStreamer:
    def __init__(self, ip: str = "127.0.0.1", port: int = 5555):
        self.ip = ip
        self.port = port
        self.st = Struct("!2BHIBB4BBQIBBH2BH")
        self.head_len = self.st.size            # header size is given by the struct size

    def _send_udp(self, packet):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(packet, (self.ip, self.port))
        sock.close()

    def packet(self, node_id: int, ts: time, par : dict, data : bytes):
        if par["crc_en"]:
            crc_ok = 1
            no_crc = 0
            crc_bad = 0
        else:
            crc_ok = 0
            no_crc = 1
            crc_bad = 0

        # TODO: preamble_length?
        # TODO: ramp_time
        # TODO: low_data_rate
        # TODO: datarate?

        # pack given parameters into loratap structure
        loratap_header = self.st.pack(
            1, # lt_version: 1 byte,
            0, # lt_padding: 1 byte,
            self.head_len, # lt_length: 2 bytes,
            
            # channel: 6 bytes:
            par["frequency"],       # frequency: 4 bytes,
            int(par["bandwidth_kHz"]),   # bandwidth: 1 byte, (1 = 125 kHz, 2 = 250 kHz, 3 = 500 kHz, ...)
            par["spreading_factor"],              # spreading factor: 1 byte

            # rssi: 4 bytes:
            0, # packet_rssi: 1 byte,
            255, # max_rssi: 1 byte,
            139+(-133), # current rssi: 1 byte,
            100, # snr * 4: 1 byte,

            0x34, # sync_word: 1 byte, always LoRaWAN 0x34
            node_id, # source_gw: 8 bytes,
            int(ts), # timestamp: 4 bytes,
                    
            # loratap_flags: 1 byte:
            (0 << 0) | # mod_fsk: 1 bit,
            (par["iq_inverted"] << 1) | # iq_inverted: 1 bit,
            (par["implicit_header"] << 2) | # implicit_header: 1 bit,
            (crc_ok << 3) | # crc_ok: 1 bit,
            (crc_bad << 4) | # crc_bad: 1 bit,
            (no_crc << 5), # no_crc: 1 bit

            par["coding_rate"], # cr: 1 byte,
            256, # datarate: 2 bytes,
            255, # if_channel (unused in simulator): 1 byte,
            255, # rf_chain (unused in simulator): 1 byte,
            1111 # tag (represents node id - for filtering): 2 bytes
            )

        # send the packet to WireShark
        self._send_udp(loratap_header + data)

