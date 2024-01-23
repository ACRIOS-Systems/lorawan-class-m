import random
import networkx as nx
import threading
from .ReentrantSemaphore import RSemaphore

from .MeshPacket import MeshPacket as mp
from .GraphicDefinitions import GraphicDefinitions as gDef


class MeshDevice():

    devListLock = RSemaphore(1)
    deviceList = []
    unknownID = 0

    def __init__(self,
                latitude,
                longitude,
                altitude = 0,
                name = "Unknown name",
                type = "Unknown type",
                eui = "Unknown EUI",
                state = "Unknown state",
                description = "Unknown description"
            ):
        self.lock = RSemaphore(1)
        with self.lock:
            self.latitude = latitude
            self.longitude = longitude
            self.altitude = altitude
            self.name = name
            self.type = type

            # Make sure the EUI is a unique value if not specified
            if eui=="Unknown EUI":
                self.eui = eui+" "+str(MeshDevice.unknownID)
                MeshDevice.unknownID = MeshDevice.unknownID+1
            else:
                self.eui = eui

            self.state = state
            self.description = description

            self.parent = None
            self.children = []
            self.packets = []

        with MeshDevice.devListLock:
            MeshDevice.deviceList.append(self)


    def delete(self):
        with MeshDevice.devListLock:
            MeshDevice.deviceList.remove(self)
        with self.lock:
            with mp.packetListLock:
                for p in self.packets:
                    mp.packetList.remove(p)
            self.packets = []

            for ch in self.children:
                with ch.lock:
                    ch.parent = None
            with self.parent.lock:
                self.parent.children.remove(self)
            self.parent = None
            self.children = []

        


    def appendPacket(self, packet: mp):
        with self.lock:
            self.packets.append(packet)


    def getPacketByTimestamp(self, ts):
        with self.lock:
            for p in self.packets:
                if p.startTime == ts:
                    return p
        return None


    @staticmethod
    def getAllDevices():
        with MeshDevice.devListLock:
            return MeshDevice.deviceList.copy()


    @staticmethod
    def getDeviceByEUI(eui):
        devList = MeshDevice.getAllDevices()
        if isinstance(eui, str):
            for dev in devList:
                with dev.lock:
                    if dev.eui == eui:
                        return dev
            return None
        elif isinstance(eui, list):
            ret = []
            for dev in devList:
                with dev.lock:
                    if dev.eui in eui:
                        ret.append(dev)
            return ret
        else:
            raise Exception("The function takes str or list of str as a parameter!")


    @staticmethod
    def getAllDevicesAsDicts():
        list = []
        for dev in MeshDevice.getAllDevices():
            with dev.lock:
                d = dev.__dict__.copy()
            if isinstance(d['parent'], MeshDevice):
                d['parent'] = d['parent'].eui
            else:
                d['parent'] = []
            d['children'] = [ch.eui for ch in d['children']]
            del d['packets']
            del d['lock']
            list.append(d)
        return list

    @staticmethod
    def getNetwork():
        G = nx.DiGraph()
        devList = MeshDevice.getAllDevices()
        for dev in devList:
            G.add_node(dev)

        for dev in devList:
            with dev.lock:
                if not (dev.parent is None):
                    G.add_edge(dev, dev.parent)
                for ch in dev.children:
                    G.add_edge(dev, ch)

        return G


    @staticmethod
    def newExampleDevice():
        dev = MeshDevice(
            latitude=random.uniform(49.15, 49.4),
            longitude=random.uniform(16.5, 16.7)
        )

        list = MeshDevice.getAllDevices()
        if len(list)>1:
            list.remove(dev)

            with dev.lock:
                dev.parent = random.choice(list)
                if random.uniform(0,1)<0.5:
                    dev.parent.children.append(dev)

                dev.state = random.choice([key for key in gDef.deviceStatusColor])

        return dev