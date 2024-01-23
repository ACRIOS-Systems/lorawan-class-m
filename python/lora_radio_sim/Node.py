from lora_sim_lib.Time import Time
from lora_sim_lib.LoRaParameters import RxParameters
from lora_sim_lib.JSONlogger import JSONlogger
import Settings
from NetObject import NetObject
from NodeStack import NodeStack
from AirInterface import AirInterface
from Packet import Packet
from enum import Enum
from termcolor import colored

if Settings.WIRESHARK_RX or Settings.WIRESHARK_TX:
    from lora_sim_lib.WiresharkStreamer import WiresharkStreamer
if Settings.MESHVIS_EN:
    from lora_sim_lib.MeshVisAPI import MeshVisAPI

class NodeState(Enum):
    IDLE = 0
    TX = 1
    RX = 2

    # redefine __str__ to print the name of the enum
    def __str__(self) -> str:
        return self.name

class Node(NetObject):

    def __str__(self) -> str:
        return super().__str__()

    def __init__(self, time: Time, air: AirInterface, exec: str, gps: tuple, devEUI, appEUI, appKey, joinDR, name, timingCmds : bool, startDelayMs:Time=Time(ms=0)) -> None:
        super().__init__(time, air, gps, name, startDelayMs)
        self.devEUI = devEUI
        self.appEUI = appEUI
        self.appKey = appKey
        self.joinDR = joinDR
        self.timingCmds = timingCmds
        self._mode = NodeState.IDLE
        self.modeLastTime = Time(-1.0)
        self.currentTxPacket = None
        self.currentRxPacket = None
        self.allRxPackets = []
        self.rxParam = None
        self.stack = NodeStack(self, exec)
        self.preambleDetected = False
        self.headerDetected = False

        if Settings.WIRESHARK_RX or Settings.WIRESHARK_TX:
            self.ws = WiresharkStreamer()

    def __del__(self):
        self.stack.__del__()

    @property
    def mode(self) -> NodeState:
        return self._mode

    @mode.setter
    def mode(self, mode : NodeState) -> None:
        # print(f"Node ID={self.id} changed mode to {mode} at {self.time}")
        self._mode = mode
        self.modeLastTime = self.time.copy()

    def receive(self, ts : Time, par : dict):
        #print(f"Node ID={self.id} receiving at {ts}:")
        #for key, val in par.items():
        #    print(f"    {key} = {val}")

        self.mode = NodeState.RX
        self.rxParam = RxParameters(
                frequency            = par["frequency"],
                bandwidth_kHz        = par["bandwidth_kHz"],
                coding_rate          = par["coding_rate"],
                crc_en               = par["crc_en"],
                low_data_rate        = par["low_data_rate"],
                implicit_header      = par["implicit_header"],
                spreading_factor     = par["spreading_factor"],
                iq_inverted          = par["iq_inverted"],
                preamble_length      = par["preamble_length"],
                rx_timeout           = par["rx_timeout"],
            )

        self.preambleDetected = False
        self.headerDetected = False


    def transmit(self, ts : Time, par : dict, data : bytes):
        #print(f"Node ID={self.id} transmitting at {ts}:")
        #for key, val in par.items():
        #    print(f"    {key} = {val}")

        self.mode = NodeState.TX
        packet = Packet(self, par, data, self.time)
        self.currentTxPacket = packet
        self.air.newPacketToAir(packet)

        JSONlogger.event("nodeTx", int(self.time.ms), EUI=self.devEUI)            
        if Settings.WIRESHARK_TX:
            # send packet to wireshark
            self.ws.packet(int(self.devEUI, 16), False, self.time.copy(), packet.packetParam.toDict(), packet.data, 1000, 1000)# send packet to wireshark, arbitrarily high values for SNR and RSSI
        if Settings.MESHVIS_EN:
            MeshVisAPI.instance.report_packet(MeshVisAPI.Packet(
                reporterEUI=self.devEUI,
                startTime=packet.startTime.sec,
                endTime=packet.endTime.sec,
                data=packet.data.hex(),
                direction="Tx",
            ))


    def idle(self) -> None:
        self.mode = NodeState.IDLE
        self.rxParam = None
        self.currentRxPacket = None

    def step(self) -> int:
        idle = self.stack.step()

        if self.mode == NodeState.RX:
            if (self.currentRxPacket is None):
                if (self.time.us > (self.rxParam.rx_timeout*1000+self.modeLastTime.us+(5000))): # Time out 5ms later, nodes timed out internally and started Tx just before this timeout which cancelled the starting Tx
                    JSONlogger.event("nodeRxTimeout", int(self.time.ms), EUI=self.devEUI)
                    self.stack.timeout()    # RX Timeout (didn't receive any packet)
                    self.idle()

            elif (self.currentRxPacket is not None):
                if not self.preambleDetected:
                    if (self.time >= self.currentRxPacket.preambleEndTime):
                        self.preambleDetected = True
                        self.stack.preambleDetected()

                if (self.rxParam.implicit_header == 0) and (not self.headerDetected):
                    if (self.time >= self.currentRxPacket.headerEndTime):
                        self.headerDetected = True

                        if self.currentRxPacket.packetParam.implicit_header == 1:
                            self.stack.headerCRCerror()
                            return

                        collided = False
                        noise=self.air.NOISE_BASE_LEVEL
                        for p in self.allRxPackets:
                            if self.currentRxPacket == p:
                                continue
                            noise = AirInterface.addPowers(noise, AirInterface.rxPowerCalculation(p, self))
                            if AirInterface.sfCollision(self.currentRxPacket, p):
                                if AirInterface.frequencyCollision(self.currentRxPacket, p):
                                    if AirInterface.headerTimingCollision(self.currentRxPacket, p):
                                        collided = True
                                        break
                        if collided:
                            self.stack.headerCRCerror()
                        else:
                            rssi = AirInterface.rxPowerCalculation(self.currentRxPacket, self)
                            snr = rssi-noise

                            # SNR needed for demod.: https://www.thethingsnetwork.org/docs/lorawan/rssi-and-snr/#snr
                            #   ??? https://www.thethingsnetwork.org/docs/lorawan/spreading-factors/#receiver-sensitivity
                            snr_min = 10-(5/2*self.currentRxPacket.packetParam.spreading_factor)

                            if snr > snr_min:
                                self.stack.headerDetected(int(snr), int(rssi))  # Header successfully detected
                            else:
                                self.stack.headerCRCerror() # Reception is below the noise level


                if (self.time >= self.currentRxPacket.endTime):
                    collided = False
                    noise = self.air.NOISE_BASE_LEVEL
                    for p in self.allRxPackets:
                        if self.currentRxPacket == p:
                            continue
                        noise = AirInterface.addPowers(noise, AirInterface.rxPowerCalculation(p, self))
                        if AirInterface.sfCollision(self.currentRxPacket, p):
                            if AirInterface.frequencyCollision(self.currentRxPacket, p):
                                if AirInterface.timingCollision(self.currentRxPacket, p):
                                    collided = True
                                    break
                    if collided:
                        JSONlogger.event("nodeRxCollision", int(self.time.ms), EUI=self.devEUI)
                        self.stack.rxCRCerror()

                    else:
                        rssi = AirInterface.rxPowerCalculation(self.currentRxPacket, self)
                        snr = rssi-noise

                        # SNR needed for demod.: https://www.thethingsnetwork.org/docs/lorawan/rssi-and-snr/#snr
                        #   ??? https://www.thethingsnetwork.org/docs/lorawan/spreading-factors/#receiver-sensitivity
                        snr_min = 10-(5/2*self.currentRxPacket.packetParam.spreading_factor)

                        if snr > snr_min:
                            JSONlogger.event("nodeRxOK", int(self.time.ms), EUI=self.devEUI)
                            if Settings.WIRESHARK_RX:
                                self.ws.packet(int(self.devEUI, 16), True, self.currentRxPacket.endTime, self.currentRxPacket.packetParam.toDict(), self.currentRxPacket.data, snr, rssi)# send packet to wireshark
                            if Settings.MESHVIS_EN:
                                MeshVisAPI.instance.report_packet(MeshVisAPI.Packet(
                                    reporterEUI=self.devEUI,
                                    startTime=self.currentRxPacket.startTime.sec,
                                    endTime=self.currentRxPacket.endTime.sec,
                                    data=self.currentRxPacket.data.hex(),
                                    direction="Rx",
                                ))
                                MeshVisAPI.instance.report_device(MeshVisAPI.Device(
                                    eui=self.devEUI,
                                    parent=self.currentRxPacket.TxObj.eui
                                ))

                            self.stack.rxDone(self.currentRxPacket.data, int(snr), int(rssi))  # RX Done
                        else:
                            JSONlogger.event("nodeRxBelowNoise", int(self.time.ms), EUI=self.devEUI)
                            self.stack.rxCRCerror()

                    self.idle()

        elif self.mode == NodeState.TX:
            if self.time >= self.currentTxPacket.endTime:
                self.mode = NodeState.IDLE
                self.currentTxPacket = None
                self.stack.txDone()        # TX Done

        return idle

    def rxPacketFromAir(self, p: Packet):
        self.allRxPackets.append(p)
        if (self.mode == NodeState.RX):
            if (self.currentRxPacket is None):
                if self.rxParam.canHear(p.packetParam):
                    if (self.modeLastTime <= p.criticalSectionStartTime) and (p.preambleEndTime <= (Time(ms=self.rxParam.rx_timeout)+self.modeLastTime)):
                        self.currentRxPacket = p
                        print(colored("{} starts receiving of packet {} from {} at {} ms.".format(self, p.id, p.TxObj, self.time.ms), "cyan"))


    def endPacketFromAir(self, p: Packet):
        if p in self.allRxPackets:
            self.allRxPackets.remove(p)
