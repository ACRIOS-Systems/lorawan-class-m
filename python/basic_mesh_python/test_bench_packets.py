from mesh_definitions import *
from mesh_functions import *
from main import *
from astropy.time import Time
#packet1 = bytes.fromhex(b'+\x02\x00\x00\x00\xe2\xdfed\x01\x00\x84\xae\x08\x00\x00\x00\x00\x00\x00\x05\x00\x00\x00\x03\x00\x00\x00\x83\x15\x01\x00\x00\x00\n\x02\x03\x00\x85\xae\x08\x00\x00\x00\x00\x00\x00X\x00\x00\x00')
#packet2 = bytes.fromhex("6A801A2B3C4DEEEE1234819A2B3C4DEEAA5678828A2B3C4DEEAA8A2B3C4DEE9ABC832A2B3C4DEEAAFFDEF0846A2B3C4DEE001234855A2B3C4DEE115678")

#t = Time('2019-12-03 23:55:32', format='iso', scale='utc')
#print(t.gps)
"""
while(1):
    sleep(1)
    print('\n')
    t = Time(str(datetime.utcnow()), format='iso', scale='utc')
    print(int(t.gps))
    GPSTIME_seconds = str(t.gps)
    print(GPSTIME_seconds)
    GPSTIME_miliseconds = GPSTIME_seconds.replace('.', '')
    GPSTIME_miliseconds = GPSTIME_miliseconds[:-3]
    print(GPSTIME_miliseconds)
"""

child_node = MeshNodeContext("NODE-B", 2, 2222, 0, initialState=MeshNodeState.idleState, children=[], parents=[])
packet = parse_Packet(child_node, b'\xe0\x01\x00\x00\x00\x88\xf6md\x01\x00\x84\x03\x00\xff\xee\xdd\xcc\xbb\xaa\r\x00\x00\x00\x02\x00\x00\x00\x84\x06\x00\xff\xee\xdd\xcc\xbb\xaa\x10\x00\x00\x00\x03\x00\x00\x00\x84\x04\x00\xff\xee\xdd\xcc\xbb\xaa\x13\x00\x00\x00\x04\x00\x00\x00\x84\x05\x00\xff\xee\xdd\xcc\xbb\xaa\x16\x00\x00\x00\x05\x00\x00\x00\x83\x15\xe7\x03\x00\x00\n\x02\x03\x00\x85\x03\x00\xff\xee\xdd\xcc\xbb\xaaX\x00\x00\x00\x83\x15\xe7\x03\x00\x00\n\x02\x03\x00\x85\x06\x00\xff\xee\xdd\xcc\xbb\xaaX\x00\x00\x00\x83\x15\xe7\x03\x00\x00\n\x02\x03\x00\x85\x04\x00\xff\xee\xdd\xcc\xbb\xaaX\x00\x00\x00\x83\x15\xe7\x03\x00\x00\n\x02\x03\x00\x85\x05\x00\xff\xee\xdd\xcc\xbb\xaaX\x00\x00\x00')
print(packet)
print(child_node.Packet_Data_Frame)
#test of the parsing function:
#packet1_parsed=PHYPayloadType.parse(packet1)
#print(packet1_parsed.Frames[0])
#print(packet1_parsed.Frames[0].MMType)
#if packet1_parsed.Frames[0].MMType == "SyncBeacon":
#    print("Correct")
#print(packet1_parsed)


#packet1_build = PHYPayloadType.build(dict(MHDR = MHDRType.build(dict(FType = 1, RFU = 2, Major = 3)),
#                                          Frames = ClassMFrameType.build(dict(MMType=CRWBeaconType,
#                                                                     Payload = MMTYPEType.build(dict(DeviceAddress = 10, GPSTime = 12, MeshPhase = 11)),
#                                                                     CRC = 0xFA))))

#packetPayload = CRWBeaconType.build(dict(DeviceAddress = 15, GPSTime = 12, MeshPhase = 10))
#packet1_build = PHYPayloadType.build(dict(MHDR = dict(FType = 1, RFU = 2, Major = 3), 
#                                          Frames = [dict(MMType = MMTYPEType.CRWBeacon,
#                                                        Payload = packetPayload,
#                                                        CRC = crc16(packetPayload))]))
"""
def buildCRWBeacon(devAddr, currentTime):

    packetPayload = CRWBeaconType.build(dict(DeviceAddress = devAddr, GPSTime = currentTime, MeshPhase = 10))
    #print(packetPayload)

    packet = PHYPayloadType.build(dict( MHDR = dict(FType = 1, RFU = 2, Major = 3), 
                                        Frames = [dict( MMType = MMTYPEType.CRWBeacon,
                                                        Payload = packetPayload,
                                                        CRC = crc16(packetPayload))]))
    return packet


build = buildCRWBeacon(300, meshGetTimestamp())
parsePayload = PHYPayloadType.parse(build)
print(parsePayload)
parseBeacon = CRWBeaconType.parse(bytes(parsePayload.Frames[0].Payload))
print(parseBeacon)
#print(" ".join(["%02X" % x for x in packet1_build]) )
#print(packet1_build)


from pydantic import BaseModel

eventData = {'id':10, 'name':'ASD', 'birth_year':2010}

class Person(BaseModel):
    id: int
    name: str
    birth_year: int

person1 = Person(**eventData)
print(person1.dict())

"""