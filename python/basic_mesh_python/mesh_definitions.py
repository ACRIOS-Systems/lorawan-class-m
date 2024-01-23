from enum import Enum
from pydantic import BaseModel
from construct import Struct, Int8ul, BitStruct, BitsInteger, Int16ul, GreedyRange, CancelParsing, Int32ul, Byte, Int64ul, Int24ul, BytesInteger
from construct import Enum as cEnum
from datetime import datetime
from astropy.time import Time
import json
from WiresharkStreamerHW import packetParam
from WiresharkStreamerHW import ws
from WiresharkStreamerHW import callTime

"""Lengths of the different type packets (used in packet parsing/building)"""
PACKET_INFO_LEN = 11                    #bytes 
SENDING_DATA_LEN_NO_PAYLOAD = 6         #length of the SendingDataType without the payload
MSG_THIS_NODE_LEN_NO_PAYLOAD = 13       #length of the MsgThisNodeType without the payload
MSG_FORWARD_LEN_NO_PAYLOAD = 17         #length of the MsgForwardType without the payload

"""Predefined addresses"""
HARDCODED_PARENT_ADDR = 1
NETWORK_SERVER_ADDR = 999

"""Connection retry number for unresponsive node 
(waiting on Parent's or Child's beacon = CONNECTION_RETRY_NUM)
(waiting on PotentialParent RegAck = CONNECTION_RETRY_NUM*NetworkDepth)"""
CONNECTION_RETRY_NUM = 3                #retry the connection x amount of times / wait for OTAA ACK 3 beacon periods after sending a request

"""Time slot RNG variables for a Registrantion Request"""
RNG_RANGE_L_TIME = 0                    #lowest time slot for RNG range for OTAARegReq
RNG_RANGE_H_TIME = 5                    #highest time slot for RNG range for OTAARegReq
RNG_STEP_TIME    = 1                    #step [ms]

"""PPM drift RNG variables"""
RNG_RANGE_L_DRIFT = 99                  #lowest value for RNG range for crystal drift   (drifting 1 milisecond per 50 ms of time passed)
RNG_RANGE_H_DRIFT = 100                 #highest value for RNG range for crystal drift
RNG_STEP_DRIFT    = 1                   #step

MeshEpochPeriodInMS = 60000
"""mesh epoch period in ms"""

MeshBeaconingFrequencies = [868100000, ]
"""mesh beaconing frequencies"""

MeshBeaconingSF = [8, ]
"""mesh beaconing spreadig factors"""

MeshBeaconingScanTime = int(0.9 * MeshEpochPeriodInMS)
"""mesh single beaconing frequency scan time"""

TimeSlotSize = 4000                        #MeshEpochPeriodInMS%TimeSlotSize == 0!! Has to be 0 so the time slots are correctly assigned.
TimeSlotPadding = 200
"""each time slot size and padding size at the end"""

RadioTimeoutPadding = 400
"""Radio timeout padding = gap [ms] between next time slot and timeout of this time slot"""

RadioTimeout = TimeSlotSize-RadioTimeoutPadding
"""timeout of TX and RX in case of not receiving a timeout interrupt from the radio"""

TransmissionDelay = int(RadioTimeout/2)
"""Transmission delay (the packet is sent in the middle of RX window reception)"""

CRWMAXCount = RNG_RANGE_H_TIME
"""Counting the CRW OTAARegReq amount of opened windows"""

"""Preamble times (BW125) [MS]""" 
PRE_SF7 = int(12544/1000)
PRE_SF8 = int(PRE_SF7*2/1000)
PRE_SF9 = int(PRE_SF7*4/1000)
PRE_SF10 = int(PRE_SF7*8/1000)
PRE_SF11 = int(PRE_SF7*16/1000)
PRE_SF12 = int(PRE_SF7*32/1000)

Timestamp_interface = 0
"""timestamp interface: 0=timestamp calcualted from GPStime 1=timestamp provided by node crystal"""


"""FSM states describing a single node operation mode"""
class MeshNodeState(Enum):
    idleState = 0,                          # idle state: if no parent, start search for it, etc.
    searchParent = 1,                       # scan band and keep receiving searching for beacons
    transmittingOTAARegReq = 2,             # transmitted the request to connect to the parent
    waitForPotentialParentWindow = 3,        # waiting for potential parent window
    waitForRequestConnectionAnswer = 4,     # asked parent to join in common receive window -> wait for answer

    connectedIdle = 5,                      # consume list of incoming events
    transmittingBeacon = 6,                 # sending our beacon
    transmittingCRWBeacon = 7,              # sending a CRW beacon
    
    waitForChildBeacon = 8,                # listening for start of child beacon
    waitForParentBeacon = 9,               # listening for start of parent beacon

    receivingNewChildNodes = 10,            # listening for any child nodes that want to connect         

"""Events (radio events + FSM events)"""
class MeshNodeEvents(Enum):
    poll = 0,

    IRQ_TX_DONE = 1,
    IRQ_RX_DONE = 2,
    IRQ_PREAMBLE_DETECTED = 3,
    IRQ_HEADER_VALID = 4,
    IRQ_HEADER_ERROR = 5,
    IRQ_CRC_ERROR = 6,
    IRQ_CAD_DONE = 7,
    IRQ_CAD_ACTIVITY_DETECTED = 8,
    IRQ_RX_TX_TIMEOUT = 9,

    TRANSMITTING_BEACON = 10
    CHILD_BEACON = 11,
    PARENT_BEACON = 12,
    OTAARegReq_BEACON = 13,

    potentialParent_BEACON = 14,
    TIME_SLOT_EXPIRED = 15


##########################
class IrqPreambleDoneEventDataType(BaseModel):
    #info after preamble detected
    RSSI:           bytes
    timestamp:      int
##########################
class IrqHeaderDoneEventDataType(BaseModel):
    #info after explicit header
    payload_len:    bytes
##########################
class IrqRxDoneEventDataType(BaseModel):
    #info after RX_DONE
    size:           int
    payload :       bytes
    SNR:            int
    RSSI :          int
##########################


""""""""""""""""""""""""""""""""""""""""""""""""""""LoRa-Mesh frame model"""""""""""""""""""""""""""""""""""""""""""""""""""""
def getPayloadSize(obj, ctx):
    """
    getPayloadSize(): acquire the payload size of the packet
    """
    if ctx.MMType in FixedMMTypeToSize.keys():
        if ctx._index >= FixedMMTypeToSize[ctx.MMType]:
            raise CancelParsing
    else:                               #if the MMType is not listed in between fixed MMType (FixedMMTypeToSize) then use the length field instead.
        if ctx._index >= ctx.Length:
            raise CancelParsing

MMTYPEType = cEnum(Int8ul, CRWBeacon = 0x81, SyncBeacon = 0x80, RoutingBeacon = 0x82, SendingData = 0x83, OTAARegAck = 0x84, OTAARegReq = 0x85, RoutingBeaconRequest = 0x86, MsgThisNode=0x32, MsgForward=0x33)

MsgThisNodeType = Struct(
    "MMType" / MMTYPEType,
    "Length" / Int8ul,
    "Sender" / Int32ul,
    "FPort" / Int8ul,
    "FCnt" /Int16ul,
    "Payload" /GreedyRange(Int8ul * getPayloadSize),
    "MIC" /  Int32ul 
)

MsgForwardType = Struct(
    "MMType" / MMTYPEType,
    "DeviceAddress" /Int32ul,
    "Length" / Int8ul,
    "Sender" / Int32ul,
    "FPort" / Int8ul,
    "FCnt" /Int16ul,
    "Payload" /GreedyRange(Int8ul * getPayloadSize),  #encrypted
    "MIC" /  Int32ul
)

OTAARegAckType = Struct(
    "MMType" / MMTYPEType,
    "DeviceEUI" / Int64ul,
    "TimeSlot"   / Int32ul,
    "ChildAddress" /Int32ul,
    "Payload"      /BytesInteger(16)
)

OTAARegReqType = Struct(
    "MMType" / MMTYPEType,
    "ConnectToDevice" /Int32ul,
    "DevNonce"  / Int16ul,
    "JoinEUI"   / Int64ul,
    "DeviceEUI" / Int64ul,
    "MIC"   / Int32ul
)

SendingDataType = Struct(
    "MMType" / MMTYPEType,
    "Length"    /Int8ul,
    "DeviceAddress" / Int32ul,
    "Payload" / GreedyRange(Int8ul * getPayloadSize)
)

SyncBeaconType = Struct(
    "MMType" / MMTYPEType
)

CRWBeaconType = Struct(
    "MMType" / MMTYPEType,
    "FreeSlots" / Int8ul,
    "NetworkDepth" /Int8ul
)

MHDRType = BitStruct(
    "FType" / BitsInteger(3),
    "RFU" / BitsInteger(3),
    "Major" / BitsInteger(2)
)

PacketInfoType = Struct(
    "MHDR" / MHDRType,
    "DeviceAddress" / Int32ul,
    "GPSTime" / Int32ul,
    "MeshPhase" / Int16ul,
)

FixedMMTypeToSize = {"OTAARegAck" : OTAARegAckType.sizeof(), "OTAARegReq" : OTAARegReqType.sizeof() }


""""""""""""""""""""""""""""""""""""""""""""""""""""""""""Radio Events + serial data reception"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
serialDataToEvent = {
    ":TX_DONE": MeshNodeEvents.IRQ_TX_DONE,
    ":RX_DONE": MeshNodeEvents.IRQ_RX_DONE,
    ":PREAMBLE_DETECTED": MeshNodeEvents.IRQ_PREAMBLE_DETECTED,
    ":IRQ_HEADER_VALID": MeshNodeEvents.IRQ_HEADER_VALID,
    "IRQ_HEADER_ERROR": MeshNodeEvents.IRQ_HEADER_ERROR,
    "CRC_ERROR": MeshNodeEvents.IRQ_CRC_ERROR,
    "IRQ_CAD_DONE": MeshNodeEvents.IRQ_CAD_DONE,
    "IRQ_CAD_ACTIVITY_DETECTED": MeshNodeEvents.IRQ_CAD_ACTIVITY_DETECTED,
    ":IRQ_RX_TX_TIMEOUT": MeshNodeEvents.IRQ_RX_TX_TIMEOUT,
}

def meshAsynchronousEvent(node, event, eventData):
    """
    meshAsynchronousEvent(): Events are pushed to the Queue if timestampInterface == 0 or node is a hardcoded parent.
    Otherives events are pushed to Radio-Queue. (node hardware crystal clock is used)
    """
    if (Timestamp_interface == 0 or node.node_address == HARDCODED_PARENT_ADDR): #if timestamp interface == 0 or node address is hardcoded parent
        node.eQueue.pushQueue(event, node.getTimestamp(node), eventData)         #push events to Queue
    elif (Timestamp_interface == 1):                                             #else
        node.HWQueue.pushRadioQueue(event, eventData)                            #push events to radio Queue

def receiveSerialData(node, serialData):
    """
    receiveSerialData(): sort events and eventData coming from the serial interface (Radio).
    """
    data = serialData.split(",")
    eventName = data[0]
    if eventName == ":RX_DONE":
        if data[1] == "CRC_ERROR":
            eventName = data[1]
            eventData = 0
            meshAsynchronousEvent(node, serialDataToEvent[eventName], eventData)
        else:
            size = data[1][5:]
            payload = data[2][5:]
            SNR = data[3][4:]
            RSSI = data[4][5:]
            #reconstruct payload back to bytes, so that they can be parsed:
            payload = payload.split(":")
            payload = ''.join(payload)
            payload = bytes.fromhex(payload)
            ws.packet(node.deviceEUI, True, callTime(10), packetParam.toDict(), bytes(payload), 1000, 1000)
            #save the eventData:
            eventData = {'size':int(size), 'payload':payload, 'SNR':int(SNR), 'RSSI': int(RSSI)}
            print(json.dumps(eventName, indent=2))
            #print(json.dumps(eventData, indent=2))
            meshAsynchronousEvent(node, serialDataToEvent[eventName], eventData)

    elif eventName == ":TX_DONE":
        eventData = serialData[len(eventName):]
        print(json.dumps(eventName, indent=2))
        meshAsynchronousEvent(node, serialDataToEvent[eventName], eventData)
    elif eventName == ":IRQ_RX_TX_TIMEOUT":
        eventData = serialData[len(eventName):]
        print(json.dumps(eventName, indent=2))
        meshAsynchronousEvent(node, serialDataToEvent[eventName], eventData)
    elif eventName == ":PREAMBLE_DETECTED":
        eventData = serialData[len(eventName):]
        print(json.dumps(eventName, indent=2))
        meshAsynchronousEvent(node, serialDataToEvent[eventName], eventData)
    elif eventName == ":TS_DONE":           #timestamp event when using node RTC clock
        node.eventReady += 1
        print("Event Timestamp received!")
    elif eventName == ":TS_REQ_DONE":           #timestamp event when using node RTC clock
        node.HWclockSync = True
        node.HWclock = int(data[1])
    return

def checkRadioInterface(interface, node):
    """
    checkRadioInterface(): check if there is any data received by the radio interface.
    """
    radioReceived = interface.readCommand()
    if radioReceived != None:
        receiveSerialData(node, radioReceived)

def assignMyTimeSlots(node):
    """
    assignMyTimeSlots(): node assigns time slots for itself and for its CRW windows
    """
    node.timeSlots[0] = True            #my timeslot
    for i in range(CRWMAXCount):        #CRW window time slots
        node.timeSlots[i+1] = True      #disable first 5 time slots! -reserved for parent CRW time slots
        node.timeSlots[-i-1] = True     #disable last 5 time slots! -reserved for children CRW time slots


""""""""""""""""""""""""""""""""""""""""""""""""""""""""""Preamble Length check"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
def returnPreableLen(node):
    """
    returnPreableLen(): returns the current SF preamble length (BW125) [miliseconds]
    """
    if(node.currentSF == 7):
        return PRE_SF7
    elif (node.currentSF == 8):
        return PRE_SF8
    elif (node.currentSF == 9):
        return PRE_SF9
    elif (node.currentSF == 10):
        return PRE_SF10
    elif (node.currentSF == 11):
        return PRE_SF11
    elif (node.currentSF == 12):
        return PRE_SF12
