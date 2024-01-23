# Based on: https://github.com/GillesC/LoRaEnergySim/blob/master/Framework/AirInterface.py

from geopy.distance import great_circle
import math
from termcolor import colored

from lora_sim_lib.Time import Time
from Packet import Packet
from NetObject import NetObject

PRINT_ENABLED = False

class AirInterface:

    NOISE_BASE_LEVEL = -90

    def __init__(self, time: Time):
        self.packetsInAir = []
        self.packetsToDeliver = []
        self.oldPackets = []
        self.netObjects = []
        self.time = time


    def addNetObjects(self, objects):
        if type(objects) is not list: objects = [objects]
        for netObj in objects:
            if isinstance(netObj, NetObject):
                self.netObjects.append(netObj)


    def newPacketToAir(self, packet: Packet):
        self.packetsInAir.append(packet)
        self.packetsToDeliver.append(packet)
        print(colored("{} starts transmitting a packet at {} with endtime at {}".format(packet.TxObj, self.time.ms, packet.endTime), "magenta"))
        return
    

    def deliverPackets(self):
        for packet in self.packetsToDeliver.copy():
            if self.time >= packet.criticalSectionStartTime:
                fromTxObj = packet.TxObj
                for o in self.netObjects:
                    if o is not fromTxObj:
                        # Limited packet reachability - LoRa can receive packets with SNR>-20dB
                        # Exact calculation is done on reception in Node.py/Gateway.py
                        if -20 < (AirInterface.rxPowerCalculation(packet, o)-AirInterface.NOISE_BASE_LEVEL):
                            o.rxPacketFromAir(packet)
                self.packetsToDeliver.remove(packet)


    def endPacketsInAir(self):
        for p in self.packetsInAir.copy(): # Need to iterate through copy of list as it changes during iterations
            if self.time >= p.endTime:
                print(colored("End of packet {} with endtime {} in {}".format(p.id, p.endTime, self.time.ms), "light_blue"))
                self.oldPackets.append(p)
                self.packetsInAir.remove(p)
        return


    def cleanupOldPackets(self):
        for oldP in self.oldPackets.copy(): # Need to iterate through copy of list as it changes during iterations
            rem = True
            for airP in self.packetsInAir:
                if oldP.endTime >= airP.startTime:
                    rem = False
                    break
            if rem:
                self.oldPackets.remove(oldP)
                for obj in self.netObjects:
                    obj.endPacketFromAir(oldP)
                #print("Removed old packet {} in {} ms.".format(oldP.id, self.time.ms))
        return


    def processPackets(self):
        self.deliverPackets()
        self.endPacketsInAir()
        self.cleanupOldPackets()




    @staticmethod
    def frequencyCollision(p1: Packet, p2: Packet) -> bool:
        """frequencyCollision conditions
                |f1-f2| <= 120 kHz if f1 or f2 has bw 500
                |f1-f2| <= 60 kHz if f1 or f2 has bw 250
                |f1-f2| <= 30 kHz if f1 or f2 has bw 125
        """

        p1_freq = p1.packetParam.frequency
        p2_freq = p2.packetParam.frequency

        p1_bw = p1.packetParam.bandwidth_kHz
        p2_bw = p2.packetParam.bandwidth_kHz

        if abs(p1_freq - p2_freq) <= 120 and (p1_bw == 500 or p2_bw == 500):
            return True
        elif abs(p1_freq - p2_freq) <= 60 and (p1_bw == 250 or p2_bw == 250):
            return True
        elif abs(p1_freq - p2_freq) <= 30 and (p1_bw == 125 or p2_bw == 125):
            return True

        return False

    @staticmethod
    def sfCollision(p1: Packet, p2: Packet) -> bool:
        # sfCollision condition:
        #       sf1 == sf2

        return p1.packetParam.spreading_factor == p2.packetParam.spreading_factor


    @staticmethod
    def timingCollision(receivingPacket: Packet, otherPacket: Packet) -> bool: # Parameters are non-commutative!
        # packet p1 collides with packet p2 when it overlaps in its critical section
        return 0 < (min(otherPacket.endTime.us-receivingPacket.criticalSectionStartTime.us, receivingPacket.endTime.us-otherPacket.startTime.us))


    @staticmethod
    def headerTimingCollision(receivingPacket: Packet, otherPacket: Packet) -> bool: # Parameters are non-commutative!
        # packet p1 collides with packet p2 when it overlaps in its critical section
        return 0 < (min(otherPacket.endTime.us-receivingPacket.criticalSectionStartTime.us, receivingPacket.headerEndTime.us-otherPacket.startTime.us))



    @staticmethod
    def rxPowerCalculation(p: Packet, receiver: NetObject) -> float:
        # Implementation of FSPL, returns power in dBm
        
        txDirectivity = 2.15 # dBi
        rxDirectivity = 2.15 # dBi
        
        txPower = p.packetParam.power
        txLocation = p.TxObj.gps
        rxLocation = receiver.gps
        freq = p.packetParam.frequency

        wavelength = (3.0*(10**8))/freq
        distance = great_circle(txLocation, rxLocation).m
        txPower = 10.0**((txPower)/10.0) # dBm -> mW
        txDirectivity = 10.0**((txDirectivity)/10.0) # dB -> G
        rxDirectivity = 10.0**((rxDirectivity)/10.0) # dB -> G
        
        # If the distance is zero, print a warning and make it 1 mm
        if distance==0:
            distance = 1e-3
            print("Warning! The device ID={p.TxObj.id} is at the same location as the ID{receiver.id}!")


        rxPower = txPower*txDirectivity*rxDirectivity*((wavelength/(4*math.pi*distance))**2) # in mW

        return 10.0*math.log10(rxPower) # in dBm




    @staticmethod
    def powerCollision(p1: Packet, p2: Packet, timeCollidedNodes):
        power_threshold = 6  # dB

        if abs(p1.rss - p2.rss) < power_threshold:
            if PRINT_ENABLED:
                print("collision pwr both node {} and node {} (too close to each other)".format(p1.node.id,
                                                                                                p2.node.id))
            if p1 in timeCollidedNodes:
                p1.collided = True
            if p2 in timeCollidedNodes:
                p2.collided = True

        elif p1.rss - p2.rss < power_threshold:
            # p1 has been overpowered by p2
            # p1 will collide if also time_collided

            if p1 in timeCollidedNodes:
                if PRINT_ENABLED:
                    print("collision pwr both node {} has collided by node {}".format(p1.TxObj.id, p2.node.id))
                p1.collided = True
        else:
            # p2 was overpowered by p1
            if p2 in timeCollidedNodes:
                if PRINT_ENABLED:
                    print("collision pwr both node {} has collided by node {}".format(p2.node.id, p1.node.id))
                p2.collided = True


    @staticmethod
    def addPowers(p1: float, p2: float) -> float:
        p = pow(10, p1/10) + pow(10, p2/10) # Power sum in mW
        return 10*math.log10(p)
