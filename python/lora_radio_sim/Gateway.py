import Settings
from lora_sim_lib.Time import Time
from lora_sim_lib.JSONlogger import JSONlogger
from AirInterface import AirInterface
from Packet import Packet
from NetObject import NetObject
from GatewayStack import GatewayStack
from lora_sim_lib.LoRaParameters import LoRaParameters
from termcolor import colored

if Settings.WIRESHARK_RX or Settings.WIRESHARK_TX:
    from lora_sim_lib.WiresharkStreamer import WiresharkStreamer
if Settings.MESHVIS_EN:
    from lora_sim_lib.MeshVisAPI import MeshVisAPI


class Gateway(NetObject):

    def __str__(self) -> str:
        return super().__str__()

        
    def __init__(self, time: Time, air: AirInterface, exec: str, gps: tuple, gweui, name, startDelayMs:Time=Time(ms=0)) -> None:
        super().__init__(time, air, gps, name, startDelayMs)
        self.gweui = gweui
        self.currentTxPackets = []
        self.currentRxPackets = {}
        self.allRxPackets = []
        self.rxRadios = {}
        self.rxChannels = []
        self.stack = GatewayStack(self, exec)

        if Settings.WIRESHARK_RX or Settings.WIRESHARK_TX:
            self.ws = WiresharkStreamer()
        if Settings.MESHVIS_EN:
            self.heardEUIs = set()


    def __del__(self):
        self.stack.__del__()


    def newRxRadio(self, params):
        if params["en"] == 1:
            radio = {
                "freq": params["freq"]
            }
            self.rxRadios[params["rf_chain"]] = radio


    def newRxChannel(self, params):
        if (params["en"] == 1) and (params["type"].lower().startswith("lora")):
            baseFreq = self.rxRadios[params["rf_chain"]]["freq"]
            for sf in params["SF_mask"]:
                channel = LoRaParameters(
                    frequency = baseFreq+params["freq"],
                    bandwidth_kHz = params["bw"]/1000,
                    spreading_factor = sf,
                    coding_rate = None,
                    iq_inverted = 0, # GWs always listen only for non-inverted IQ
                    low_data_rate = None,
                    implicit_header = None,
                    crc_en = None,
                    preamble_length = None
                )
                self.rxChannels.append(channel)


    def transmit(self, ts : Time, par : dict, data : bytes):
        packet = Packet(self, par, data, self.time)
        self.currentTxPackets = packet
        self.air.newPacketToAir(packet)
        
        JSONlogger.event("gatewayTx", int(self.time.ms), EUI=self.gweui)
        if Settings.WIRESHARK_TX:
            self.ws.packet(int(self.gweui, 16), False, self.time.copy(), packet.packetParam.toDict(), packet.data, 1000, 1000)# send packet to wireshark, arbitrarily high values for SNR and RSSI 
        if Settings.MESHVIS_EN:
            MeshVisAPI.instance.report_packet(MeshVisAPI.Packet(
                reporterEUI=self.gweui,
                startTime=packet.startTime.sec,
                endTime=packet.endTime.sec,
                data=packet.data.hex(),
                direction="Tx",
            ))


    def step(self) -> int:
        # step() function is never blocking since the GWs are always running in real time
        idle = self.stack.step()

        if len(self.currentRxPackets): # if there are packets to receive
            for channel, packet in self.currentRxPackets.copy().items():
                if (self.time >= packet.endTime):

                    collided = False
                    noise=self.air.NOISE_BASE_LEVEL
                    for p in self.allRxPackets:
                        if packet == p:
                            continue
                        noise = AirInterface.addPowers(noise, AirInterface.rxPowerCalculation(p, self))
                        if AirInterface.sfCollision(packet, p):
                            if AirInterface.frequencyCollision(packet, p):
                                if AirInterface.timingCollision(packet, p):
                                    collided = True
                                    break
                    
                    rssi = AirInterface.rxPowerCalculation(packet, self)
                    snr = rssi-noise

                    if collided:
                        JSONlogger.event("gatewayRxCollision", int(self.time.ms), EUI=self.gweui)
                        # Corrupted packet with CRC error
                        self.stack.rxDone(packet.corruptData(), crcStatus=2, snr=int(snr), rssi=int(rssi))

                    else:
                        # SNR needed for demod.: https://www.thethingsnetwork.org/docs/lorawan/rssi-and-snr/#snr
                        #   https://www.thethingsnetwork.org/docs/lorawan/spreading-factors/#receiver-sensitivity
                        snr_min = 10-(5/2*packet.packetParam.spreading_factor)

                        if snr > snr_min:
                            JSONlogger.event("gatewayRxOK", int(self.time.ms), EUI=self.gweui)
                            if Settings.WIRESHARK_RX:
                                self.ws.packet(int(self.gweui, 16), True, packet.endTime, packet.packetParam.toDict(), packet.data, snr, rssi)# send packet to wireshark
                            if Settings.MESHVIS_EN:
                                self.heardEUIs.add(packet.TxObj.eui)
                                MeshVisAPI.instance.report_packet(MeshVisAPI.Packet(
                                    reporterEUI=self.gweui,
                                    startTime=packet.startTime.sec,
                                    endTime=packet.endTime.sec,
                                    data=packet.data.hex(),
                                    direction="Rx",
                                ))
                                MeshVisAPI.instance.report_device(MeshVisAPI.Device(
                                    eui=self.gweui,
                                    children=list(self.heardEUIs)
                                ))
                            
                            # Correctly received
                            self.stack.rxDone(packet, crcStatus=1 if packet.packetParam.crc_en==1 else 0, snr=int(snr), rssi=int(rssi))  # crcStatus: 0=NO_CRC, 1=CRC_OK, 2=CRC_BAD
                        else:
                            JSONlogger.event("gatewayRxBelowNoise", int(self.time.ms), EUI=self.gweui)
                            # Corrupted packet with CRC error
                            self.stack.rxDone(packet.corruptData(), crcStatus=2, snr=int(snr), rssi=int(rssi))
                    
                    self.currentRxPackets = {key:val for key, val in self.currentRxPackets.items() if val!=packet}


        return 1 # always idle


    def rxPacketFromAir(self, p: Packet):
        self.allRxPackets.append(p)
        rxChannel = None
        for channel in self.rxChannels:
            if channel.canHear(p.packetParam):
                rxChannel = channel
        if rxChannel == None:
            return

        if (self.currentRxPackets.get(rxChannel) is None):
            self.currentRxPackets[rxChannel] = p
            print(colored("{} starts receiving of packet {} from {} at {} ms.".format(self, p.id, p.TxObj, self.time.ms), "cyan"))

    def endPacketFromAir(self, p: Packet):
        if p in self.allRxPackets:
            self.allRxPackets.remove(p)