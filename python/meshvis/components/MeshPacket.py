import random
import requests # Used to download word list for example packet data
import threading
from .ReentrantSemaphore import RSemaphore


class MeshPacket():

    packetListLock = RSemaphore(1)
    packetList = []
    wordList = None # Used for example packet data

    def __init__(self, reporterEUI, direction, startTime, endTime, data=""):
        self.lock = RSemaphore(1)

        with self.lock:
            self.reporterEUI=reporterEUI
            self.direction=direction
            self.startTime=startTime # seconds
            self.endTime=endTime # seconds
            self.data = data

        with MeshPacket.packetListLock:
            MeshPacket.packetList.append(self)

    
    def delete(self):
        with self.packetListLock:
            MeshPacket.packetList.remove(self)


    @staticmethod
    def getAllPackets():  
        with MeshPacket.packetListLock:              
            return MeshPacket.packetList.copy()


    @staticmethod
    def getAllPacketsAsDicts():
        list = []
        for p in MeshPacket.packetList:
            with p.lock:
                pkt = p.__dict__.copy()
            del pkt['lock']
            list.append(pkt)
        return list


    @staticmethod
    def getDumbPacket():                
        packet = MeshPacket("", "Tx", 0, 0)
        packet.delete()
        return packet


    lastPacketTimestamp = 0
    exampleLock = threading.Lock()
    @staticmethod
    def newExamplePacket():
        from .MeshDevice import MeshDevice as md
        
        devList = md.getAllDevices()

        if len(devList)<2:
            return

        [sender, receiver] = random.sample(devList, k=2)

        with MeshPacket.exampleLock:
            sTime = MeshPacket.lastPacketTimestamp + 10*random.uniform(0, 1)
            eTime = sTime + 0.1*random.uniform(0, 1)
            MeshPacket.lastPacketTimestamp = sTime

            # Get random data
            if __class__.wordList==None:
                wordSite = "https://www.mit.edu/~ecprice/wordlist.10000"
                response = requests.get(wordSite)
                __class__.wordList = [word.decode('utf-8') for word in response.content.splitlines()]

        MeshPacket(reporterEUI=sender.eui, direction="Tx", startTime=sTime, endTime=eTime, data=random.choices(__class__.wordList, k=3))
        MeshPacket(reporterEUI=receiver.eui, direction="Rx", startTime=sTime, endTime=eTime, data=random.choices(__class__.wordList, k=3))
