from lora_sim_lib.LoRaParameters import PacketParameters
from lora_sim_lib.WiresharkStreamer import WiresharkStreamer
from lora_sim_lib.Time import Time

packetParam = PacketParameters(
    frequency           = 868100000,
    bandwidth_kHz       = 125,
    spreading_factor    = 7,
    coding_rate         = 5,
    iq_inverted         = 0,
    low_data_rate       = 1,
    implicit_header     = 0,
    crc_en              = 1,
    preamble_length     = 8,
    power               = 0, #Tx power
    # momentarily unused - "ramp_time", "tx_timeout"
)

def callTime(microseconds):
    return Time(us=microseconds)

ws = WiresharkStreamer()
