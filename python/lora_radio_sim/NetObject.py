from geopy.distance import great_circle
from lora_sim_lib.Time import Time
#from AirInterface import AirInterface
from Packet import Packet

NET_ID = 0


class NetObject:
    def __init__(self, time: Time, air, gps: tuple, name, startDelayMs:Time) -> None:
        global NET_ID
        self._id = NET_ID
        NET_ID += 1

        self.name = name
        self.time = time
        self.air = air
        self.gps = gps

        self.startDelayMs = startDelayMs


    @property
    def id(self):
        return self._id

    @property
    def eui(self):
        try:
            return self.devEUI
        except:
            return self.gweui


    def __str__(self) -> str:
        s = f"{self.__class__.__name__} ID={self.id}"
        return s


    def distanceTo(self, obj) -> float:
        """
        Returns distance of this object to another network object.
        """
        return great_circle(self.gps, obj.gps).m


    def rxPacketFromAir(self, p: Packet):
        raise NotImplementedError(f"This method should be implemented in Node or Gateway class!")