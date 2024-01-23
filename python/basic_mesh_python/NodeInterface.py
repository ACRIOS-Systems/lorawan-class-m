import subprocess
import sys
from WiresharkStreamerHW import *

try:
    assert sys.version_info >= (3, 4)
except:
    print("USE python3 instead of python or python2!!!")
    sys.exit(0)

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

from RadioInterface import *

#COMMON PARAMETERS

bandwidth = 125
preamble_len = 8        #(0-65535) 
implicit_header = 0     #(0/1) 0=explicit
crc_en =  1             #(0/1)
iq_inverted = 0         #(0-normal/1-inverted)
coding_rate = 5         #(5-8)
LDR = 1                 #(0/1)
ts = 0
ramp_time = 40
symbol_timeout = 2000

#RX PARAMETERS
rx_payload = 0            #no payload for RX nodes
payload_len_rx = 0

#TX PARAMETERS
TX_power = 14
TX_timeout = 2000

def TX_CONFIG(node, interface, frequency, SF, tx_payload):
    size = 0
    for i in tx_payload:
        if(i ==':'):
            pass
        else:
            size = size+1
    payload_len_tx = len(tx_payload)
    payload_size = size/2
    packet = ":TX,ts="+str(ts)+",frequency="+str(frequency)+",preamble_length="+str(preamble_len)+",implicit_header="+str(implicit_header)+"\
,payload_length="+str(payload_len_tx)+",crc_en="+str(crc_en)+",iq_inverted="+str(iq_inverted)+"\
,spreading_factor="+str(SF)+",bandwidth_kHz="+str(bandwidth)+",coding_rate="+str(coding_rate)+",low_data_rate="+str(LDR)+"\
,power="+str(TX_power)+",ramp_time="+str(ramp_time)+",tx_timeout="+str(TX_timeout)+",symbol_timeout="+str(symbol_timeout)+"\
,size="+str(payload_size)+",data="+str(tx_payload)

    tx_payload_hex_integers = []
    for i in range(0, len(tx_payload), 3):
        hex_str = tx_payload[i] + tx_payload[i+1]
        tx_payload_hex_integers.append(int(hex_str, 16))
    ws.packet(node.deviceEUI, False, callTime(10), packetParam.toDict(), bytes(tx_payload_hex_integers), 1000, 1000)
    interface.sendCommand(packet)
    return

def RX_CONFIG(interface, frequency, SF, RX_timeout):
    packet = ":RX,"+"ts="+str(ts)+",frequency="+str(frequency)+",preamble_length="+str(preamble_len)+",implicit_header="+str(implicit_header)+"\
,payload_length="+str(payload_len_rx)+",crc_en="+str(crc_en)+",iq_inverted="+str(iq_inverted)+"\
,spreading_factor="+str(SF)+",bandwidth_kHz="+str(bandwidth)+",coding_rate="+str(coding_rate)+",low_data_rate="+str(LDR)+"\
,rx_timeout="+str(RX_timeout)+",symbol_timeout="+str(symbol_timeout)
    interface.sendCommand(packet)
    return

def EVENT_TS(interface, eventTimestamp):
    packet = ":TS,"+"event_timestamp="+str(eventTimestamp)
    interface.sendCommand(packet)
    return

def TS_REQ(interface):
    packet = ":TR"
    interface.sendCommand(packet)
    return
