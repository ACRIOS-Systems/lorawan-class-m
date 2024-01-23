from mesh_definitions import *
from Queues import *
from mesh_createNodeRelations import *

"""""""""""""""""""""""""""""""""""""""""""""""""""" PACKET PARSING + ROUTING """""""""""""""""""""""""""""""""""""""""""""""""""""

def findNextHop(node, endNodeAddress):
    """
    findNextHop(): find next node address to send the message to (by checking routing table - based on end node address)
    """
    if endNodeAddress == HARDCODED_PARENT_ADDR:
        if len(node.parents) != 0:
            return node.parents[0]["DeviceAddress"]
        else:
            return False
    elif endNodeAddress != HARDCODED_PARENT_ADDR:
        for i in range(len(node.children)):
            for j in range(len(node.children[i]["AccessNodes"])):
                if node.children[i]["AccessNodes"][j] == endNodeAddress:
                    return node.children[i]["DeviceAddress"]
    else:
        print("Next hop not found!")
        return False


def sortData(node, parsed_Frame, endDevice):
    """
    sortData(): sort data into dataQueues of the next hop nodes
    """
    for i in range(2):
        receiverIndex = False
        if endDevice == node.node_address:
            node.dQueue.writeData(parsed_Frame)
            return True
        elif node.findParent(endDevice) != 'None':  #check if the endDevice is on my list parents or children
            receiverIndex = node.findParent(endDevice)
            node.parents[receiverIndex]["dataQueue"].writeData(parsed_Frame)
            return True
        elif node.findChild(endDevice) != 'None':
            receiverIndex = node.findChild(endDevice)
            node.children[receiverIndex]["dataQueue"].writeData(parsed_Frame)
            return True
        elif node.findPotentialChild(endDevice) != 'None':
            receiverIndex = node.findPotentialChild(endDevice)
            node.potentialChildren[receiverIndex]["dataQueue"].writeData(parsed_Frame)
            return True
        elif node.findPotentialParent(endDevice) != 'None':
            receiverIndex = node.findPotentialParent(endDevice)
            node.potentialParents[receiverIndex]["dataQueue"].writeData(parsed_Frame)
            return True
        else:                                       #else find next node to send the message to (by checking routing table)
            endDevice = findNextHop(node, endDevice)
            if endDevice == False:
                return False
    return False


def parse_Packet(node, packet):
    """
    parse_Packet(): parse the received packet and sort any appended data to the correct dataQueues of the nodes.
    """
    try:
        parsed_info = PacketInfoType.parse(packet)
        node.Packet_MHDR = parsed_info.MHDR
        node.Packet_DevAddr = parsed_info.DeviceAddress                     #extract the information about the packet sender
        node.Packet_timestamp = int(str(parsed_info.GPSTime)+"000")         #convert to miliseconds
        node.Packet_Phase = parsed_info.MeshPhase
        node.Packet_Beacon_Frames.clear()
        node.Packet_Data_Frames.clear()

        parsed_Beacon_Frame = 0
        parsed_Data_Frame = 0
        packet = packet[PACKET_INFO_LEN:]                                   #remove the packet info from the packet
        while len(packet) > 0:
            MMType = packet[0]
            if MMType == int(MMTYPEType.CRWBeacon):                         #CRW beacon
                parsed_Beacon_Frame = CRWBeaconType.parse(packet)
                packet = packet[CRWBeaconType.sizeof(): ]
            elif MMType == int(MMTYPEType.SyncBeacon):                      #Sync beacon
                parsed_Beacon_Frame = SyncBeaconType.parse(packet)
                packet = packet[SyncBeaconType.sizeof(): ]
            elif MMType == int(MMTYPEType.OTAARegReq):                      #if the packet is OTAARegReq (this can only be recepted as a response to a CRW beacon)
                parsed_Beacon_Frame = OTAARegReqType.parse(packet)
                packet = packet[OTAARegReqType.sizeof(): ]
                if parsed_Beacon_Frame.ConnectToDevice == node.node_address:        #if the request is for this device
                    sortData(node, parsed_Beacon_Frame, HARDCODED_PARENT_ADDR)      #send to HP
            elif MMType == int(MMTYPEType.OTAARegAck):                              #if the packet is OTAARegAck
                parsed_Beacon_Frame = OTAARegAckType.parse(packet)
                packet = packet[OTAARegAckType.sizeof(): ]
                if parsed_Beacon_Frame.DeviceEUI == node.deviceEUI:                 #if the node receiving this is the node being acknowledged 
                    node.Packet_Data_Frame = parsed_Beacon_Frame
                elif node.findChild(node.Packet_DevAddr) != 'None':                 #if the parent of a child that is acknowledging a new node
                    node.Packet_Data_Frame = parsed_Beacon_Frame
                    sortData(node, parsed_Beacon_Frame, HARDCODED_PARENT_ADDR)      #propagate the message uplink

            elif MMType == int(MMTYPEType.SendingData):
                parsed_Beacon_Frame = SendingDataType.parse(packet)
                packet = packet[SENDING_DATA_LEN_NO_PAYLOAD: ]                      #remove the parsed frame from the packet
                if node.node_address == parsed_Beacon_Frame.DeviceAddress:          #if my address == Frame destination address
                    parsed_Frame_Payload_Size = 0
                    while parsed_Frame_Payload_Size < len(parsed_Beacon_Frame.Payload):                 #while payload is not 0
                        nextFrame = parsed_Beacon_Frame.Payload[parsed_Frame_Payload_Size:len(parsed_Beacon_Frame.Payload)]
                        MMType = nextFrame[0]
                        if MMType == int(MMTYPEType.MsgThisNode):                                       #if the message is for this node
                            parsed_Data_Frame = MsgThisNodeType.parse(bytes(nextFrame))
                            parsed_Frame_Payload_Size += (MSG_THIS_NODE_LEN_NO_PAYLOAD+parsed_Data_Frame.Length)
                            sortData(node, parsed_Data_Frame, node.node_address)
                            node.Packet_Data_Frames.append(parsed_Data_Frame)
                        elif MMType == int(MMTYPEType.MsgForward):                                      #elif message is for some other node on the network 
                            parsed_Data_Frame = MsgForwardType.parse(bytes(nextFrame))
                            parsed_Frame_Payload_Size += (MSG_FORWARD_LEN_NO_PAYLOAD+parsed_Data_Frame.Length)
                            sortData(node, parsed_Data_Frame, parsed_Data_Frame.DeviceAddress)
                            node.Packet_Data_Frames.append(parsed_Data_Frame)
                        elif MMType == int(MMTYPEType.OTAARegAck):                          #elif message is OTAARegAckType (This message was send by a neighbouring node-we need to forward it towards the potential child(or its neighbouring node))
                            parsed_Data_Frame = OTAARegAckType.parse(bytes(nextFrame))
                            parsed_Frame_Payload_Size += (OTAARegAckType.sizeof())
                            sortData(node, parsed_Data_Frame, parsed_Data_Frame.DeviceEUI)
                            node.Packet_Data_Frames.append(parsed_Data_Frame)
                        elif MMType == int(MMTYPEType.OTAARegReq):                          #elif message is OTAARegReq (This message was send by a neighbouring node-we need to forward it towards HP)
                            parsed_Data_Frame = OTAARegReqType.parse(bytes(nextFrame))
                            parsed_Frame_Payload_Size += (OTAARegReqType.sizeof())
                            sortData(node, parsed_Data_Frame, HARDCODED_PARENT_ADDR)
                            node.Packet_Data_Frames.append(parsed_Data_Frame)
                packet = packet[len(parsed_Beacon_Frame.Payload): ]                         #remove the parsed frame payload + MIC from the packet
            node.Packet_Beacon_Frames.append(parsed_Beacon_Frame)
        return True
    except:
        return False


"""""""""""""""""""""""""""""""""""""""""""""""""""" PACKET BUILDING """""""""""""""""""""""""""""""""""""""""""""""""""""

def buildBeacon(devAddr, gpsTime):
    gpsTime = int(str(gpsTime)[0:10])                                                   #convert to seconds
    packet = PacketInfoType.build(dict( MHDR = dict(FType = 7, RFU = 0, Major = 0),     #7 is proprietary
                                        DeviceAddress = devAddr,
                                        GPSTime = gpsTime,
                                        MeshPhase = 1))
    return packet

def appendCRWBeacon(packet, freeSlots, networkDepth):
    packetMMType = CRWBeaconType.build(dict(MMType = MMTYPEType.CRWBeacon, FreeSlots = freeSlots, NetworkDepth = networkDepth))
    packet += packetMMType
    return packet
    
def appendSyncBeacon(packet):
    packetMMType = SyncBeaconType.build(dict(MMType = MMTYPEType.SyncBeacon))
    packet += packetMMType
    return packet

def appendMessage(appendMessage, parsed_Frame, nextNodeAddr):
    packetMessage = b''
    TypeOfFrame = parsed_Frame.MMType
    if TypeOfFrame == MMTYPEType.MsgForward and nextNodeAddr == parsed_Frame.DeviceAddress:  #mesgThisNode (message is for my neighbouring node so I will package it in MsgThisNode packet)
        packetMessage = MsgThisNodeType.build(dict(MMType = MMTYPEType.MsgThisNode, Length=parsed_Frame.Length, Sender=parsed_Frame.Sender, FPort = parsed_Frame.FPort, FCnt = parsed_Frame.FCnt, Payload = parsed_Frame.Payload, MIC=parsed_Frame.MIC))

    elif TypeOfFrame == MMTYPEType.MsgForward:                                               #MsgForward
        packetMessage = MsgForwardType.build(dict(MMType = MMTYPEType.MsgForward, DeviceAddress=parsed_Frame.DeviceAddress, Length=parsed_Frame.Length, Sender=parsed_Frame.Sender, FPort = parsed_Frame.FPort, FCnt = parsed_Frame.FCnt, Payload = parsed_Frame.Payload, MIC=parsed_Frame.MIC))

    elif TypeOfFrame == MMTYPEType.OTAARegReq:
        packetMessage = OTAARegReqType.build(dict(MMType = TypeOfFrame, ConnectToDevice=parsed_Frame.ConnectToDevice, DevNonce=parsed_Frame.DevNonce, JoinEUI=parsed_Frame.JoinEUI, DeviceEUI=parsed_Frame.DeviceEUI))

    elif TypeOfFrame == MMTYPEType.OTAARegAck:
        packetMessage = OTAARegAckType.build(dict(MMType = TypeOfFrame, DeviceEUI=parsed_Frame.DeviceEUI, TimeSlot = parsed_Frame.TimeSlot, ChildAddress = parsed_Frame.ChildAddress,  Payload = parsed_Frame.Payload))

    appendMessage = appendMessage + packetMessage
    return appendMessage

def appendSendingDataBeacon(packet, appendMessage, nextNodeAddr):
    packetMMType = b''
    packetMMType = SendingDataType.build(dict(MMType = MMTYPEType.SendingData, Length=len(appendMessage), DeviceAddress=nextNodeAddr, Payload=appendMessage))
    packet = packet + packetMMType
    return packet

def appendOTAARegAckBeacon(packet, deviceEUI, timeSlot, childAddress, payload):
    packetMMType = OTAARegAckType.build(dict(MMType = MMTYPEType.OTAARegAck, DeviceEUI=deviceEUI, TimeSlot = timeSlot, ChildAddress = childAddress, Payload = payload))
    packet += packetMMType
    return packet

def appendOTAARegReqBeacon(packet, ConnectToDev, devNonce, joinEUI, deviceEUI, mic):
    packetMMType = OTAARegReqType.build(dict(MMType = MMTYPEType.OTAARegReq, ConnectToDevice=ConnectToDev, DevNonce=devNonce, JoinEUI=joinEUI, DeviceEUI=deviceEUI, MIC = mic))
    packet += packetMMType
    return packet

def appendMSGForward(packet, devAddr, len, sender, FPort, FCnt, payload, mic):
    packetMMType = MsgForwardType.build(dict(MMType = MMTYPEType.MsgForward, DeviceAddress=devAddr, Length=len, Sender=sender, FPort = FPort, FCnt = FCnt, Payload = payload, MIC=mic))
    packet += packetMMType
    return packet
