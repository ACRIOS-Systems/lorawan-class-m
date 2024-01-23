from time import *
from mesh_parsing_building import *
from Queues import *
from enum import IntEnum
from mesh_encryption import *
import base64

AES128_BLOCK_SIZE = 16


def appendNodeData(node, packet, SF):
    """
    appendNodeData(): checks if there is any packets to forward in the dataQueues of the neghbouring nodes
    and appends that data to the outgoing packet
    """

    delete_potential_children = []
    for potentialChildIndex in range(len(node.potentialChildren)):                                                                
        if node.potentialChildren[potentialChildIndex]["SF"] == SF:                                 #check if the node is on the current SF
            while node.potentialChildren[potentialChildIndex]["dataQueue"].returnSize() != 0:       #check if it has something in its dataQueue
                parsed_Frame =  node.potentialChildren[potentialChildIndex]["dataQueue"].readFrame()
                if parsed_Frame.MMType == MMTYPEType.OTAARegAck:
                    ####################################Adding node to the list of children
                    child = createChild(parsed_Frame.ChildAddress, node.potentialChildren[node.potentialChildIndex]["Frequency"], node.potentialChildren[node.potentialChildIndex]["SF"], node.setTimeSlot())
                    node.childIndex = len(node.children)
                    node.children.append(child)
                    print("New child added!")
                    if node.node_address != HARDCODED_PARENT_ADDR:
                        node.meshTimers.pushEvent(MeshNodeEvents.CHILD_BEACON, 0, node.childIndex) 

                    node.childrenToBeConfirmed.append(parsed_Frame.ChildAddress)                    #set this child to "to be confirmed" list
                    delete_potential_children.append(node.potentialChildren[potentialChildIndex]["DeviceEUI"])
                    packet = appendOTAARegAckBeacon(packet, parsed_Frame.DeviceEUI, node.children[node.childIndex]["timeSlot"], parsed_Frame.ChildAddress, parsed_Frame.Payload)
                else:
                    break
    while len(delete_potential_children) != 0:
        potentialChildIndex = node.findPotentialChild(delete_potential_children[0])
        del node.potentialChildren[node.potentialChildIndex]         #delete the potential child
        delete_potential_children.pop()

    for potentialParentIndex in range(len(node.potentialParents)):                                                                         
        if node.potentialParents[potentialParentIndex]["SF"] == SF:
            while node.potentialParents[potentialParentIndex]["dataQueue"].returnSize() != 0:
                parsed_Frame =  node.potentialParents[potentialParentIndex]["dataQueue"].readFrame()
                if parsed_Frame.MMType == MMTYPEType.OTAARegReq:
                    packet = appendOTAARegReqBeacon(packet, parsed_Frame.ConnectToDevice, parsed_Frame.DevNonce, parsed_Frame.JoinEUI, parsed_Frame.DeviceEUI)
                else:
                    break
                
    for childIndex in range(len(node.children)):                                                                         
        if node.children[childIndex]["SF"] == SF:
            appendMsg = b''
            while node.children[childIndex]["dataQueue"].returnSize() != 0:
                parsed_Frame = node.children[childIndex]["dataQueue"].readFrame()
                appendMsg = appendMessage(appendMsg, parsed_Frame, node.children[childIndex]["DeviceAddress"])
            if appendMsg != b'':
                packet = appendSendingDataBeacon(packet, appendMsg, node.children[childIndex]["DeviceAddress"])
    for parentIndex in range(len(node.parents)):                                                                         
        if node.parents[parentIndex]["SF"] == SF:
            appendMsg = b''
            while node.parents[parentIndex]["dataQueue"].returnSize() != 0:
                parsed_Frame =  node.parents[parentIndex]["dataQueue"].readFrame()
                appendMsg = appendMessage(appendMsg, parsed_Frame, node.parents[parentIndex]["DeviceAddress"])
            if appendMsg != b'':
                packet = appendSendingDataBeacon(packet, appendMsg, node.parents[parentIndex]["DeviceAddress"])
    return packet


def dataQueueCheck(node, pForwarder):
    """
    dataQueueCheck(): check if there is any data in my dataQueue and process the data
    """
################################################ NODE-SPECIFIC QUEUE ###############################################################
    while node.dQueue.returnSize() != 0:                                        #check my data queue
        frame = node.dQueue.readFrame()
        ################################################ GATEWAY ############################################################
        if (node.node_address == HARDCODED_PARENT_ADDR):

            ################################################ UPLINK REG REQUEST ############################################################
            if frame.MMType == MMTYPEType.OTAARegReq:                           #if OTAARegReq -> push to NS_input queue
                deviceEUI = frame.DeviceEUI.to_bytes(8, 'big')
                deviceEUI = deviceEUI.hex()
                nodeIndex = pForwarder.returnEndNodeIndex(deviceEUI)            #check if the node is registered in the NS
                if nodeIndex == 'None':
                    print("Node not provisioned on the Network Server!")
                    return
                appkey = pForwarder.NS_endNodeData[nodeIndex]["AppKey"]
                if((checkMIC(frame, appkey)) == True):
                    node.packetForwarder.PF_DataQueues.NS_input_add(frame)
                                                                                #else if Data message -> check devAddr, check MIC, Decrypt,  
            ################################################ UPLINK DATA ############################################################
            elif frame.MMType == MMTYPEType.MsgThisNode:                        #replace the packet payload with decrypted payload and put to NS_input queue
                nodeIndex = pForwarder.returnEndNodeIndexAddr(frame.Sender)
                if nodeIndex == 'None':
                    print("Node not provisioned on the Network Server!")
                    return

                packet = b''
                built_Frame = appendMSGForward(packet, HARDCODED_PARENT_ADDR, frame.Length, frame.Sender, frame.FPort, frame.FCnt, frame.Payload, 0)
                built_Frame = built_Frame[:-4]                      #remove MIC
                MIC = calcualteMIC(built_Frame, pForwarder.NS_endNodeData[nodeIndex]["NwkSkey"])
                if(frame.MIC != int(MIC, 16)):
                    print("MIC incorrect, dropping the packet!")
                    return

                pForwarder.NS_endNodeData[nodeIndex]["FCntUp"] = pForwarder.NS_endNodeData[nodeIndex]["FCntUp"] + 1     #increase the FCountUp
                if(frame.FCnt != pForwarder.NS_endNodeData[nodeIndex]["FCntUp"]):                                       #if frame counter is not correcct, return
                    return

                decrypted_payload = encryptDataPayloadGATEWAY(pForwarder, frame, nodeIndex)
                frame.Payload = decrypted_payload
                node.packetForwarder.PF_DataQueues.NS_input_add(frame)

        ################################################ END NODE - DOWNLINK DATA RECEPTED ############################################################
        if node.node_address != HARDCODED_PARENT_ADDR and frame.MMType == MMTYPEType.MsgThisNode:   #if there is a message for this node, send it to decryption and application
            applicationDataReceived(node, frame)


################################################ PACKET FORWARDER INPUT QUEUE (for gateway only)###############################################################
    if (node.node_address == HARDCODED_PARENT_ADDR):
        if(node.packetForwarder.PF_DataQueues.NS_output_size() > 0):                #check the NS output queue
            frameToNetwork = node.packetForwarder.PF_DataQueues.NS_output_take()

            ################################################ DOWNLINK REG ACK ###############################################################
            if(frameToNetwork["packetType"] == int(MMTYPEType.OTAARegAck)):
                nodeIndex = pForwarder.returnEndNodeIndex(frameToNetwork["deviceEUI"])
                if nodeIndex == 'None':
                    return
                mic = calculateMICRegAck(pForwarder.NS_endNodeData[nodeIndex]["AppKey"], int(frameToNetwork["JoinNonce"], 16), int(frameToNetwork["NetID"], 16), int(frameToNetwork["DeviceAddress"], 16))
                
                framePayload =  bytearray.fromhex(frameToNetwork["JoinNonce"])  +\
                                bytearray.fromhex(frameToNetwork["NetID"])  +\
                                bytearray.fromhex(mic)
                
                encrypted_msg = LoRaEncrypt(pForwarder.NS_endNodeData[nodeIndex]["AppKey"], framePayload)
                                
                packet = b''
                AES_payload = int.from_bytes(encrypted_msg, "little")
                build_Frame = appendOTAARegAckBeacon(packet, int(frameToNetwork["deviceEUI"], 16), 0, int(frameToNetwork["DeviceAddress"], 16), AES_payload)
                parsed_Frame = OTAARegAckType.parse(build_Frame)
                sortData(node, parsed_Frame, parsed_Frame.DeviceEUI)

                for i in range(len(node.children)):
                    for j in range(len(node.children[i]["AccessNodes"])):             #replace the Device EUI address with Child Address (in the routing table)
                        if node.children[i]["AccessNodes"][j] == frame.DeviceEUI:
                            node.children[i]["AccessNodes"][j] = parsed_Frame.ChildAddress

            ################################################ DOWNLINK DATA ###############################################################
            if(frameToNetwork["packetType"] == int(MMTYPEType.MsgForward)):
                nodeIndex = pForwarder.returnEndNodeIndexAddr(int(frameToNetwork["EndDeviceAddr"], 16))
                if nodeIndex == 'None':
                    print("Device address not on the list, droping the packet.")
                    return

                pForwarder.NS_endNodeData[nodeIndex]["FCntDown"] = pForwarder.NS_endNodeData[nodeIndex]["FCntDown"] + 1     #increase the FCountDown
                if(frameToNetwork["FCnt"] != pForwarder.NS_endNodeData[nodeIndex]["FCntDown"]):                             #if frame counter is not correct, return
                    return
                
                encrypted_payload = encryptDataPayloadGATEWAY(pForwarder, frameToNetwork, nodeIndex)

                packet = b''
                built_Frame = appendMSGForward(packet, int(frameToNetwork["EndDeviceAddr"], 16), len(encrypted_payload), HARDCODED_PARENT_ADDR, frameToNetwork["FPort"], frameToNetwork["FCnt"], encrypted_payload, 0)
                built_Frame = built_Frame[:-4]                      #remove MIC
                MIC = calcualteMIC(built_Frame, pForwarder.NS_endNodeData[nodeIndex]["NwkSkey"])
                built_Frame = appendMSGForward(packet, int(frameToNetwork["EndDeviceAddr"], 16), len(encrypted_payload), HARDCODED_PARENT_ADDR, frameToNetwork["FPort"], frameToNetwork["FCnt"], encrypted_payload, int(MIC, 16))
                parsed_Frame = MsgForwardType.parse(built_Frame)
                sortData(node, parsed_Frame, parsed_Frame.DeviceAddress)


def applicationDataSend(node, data):
    """
    applicationDataSend(): send the application data from the node to the network on the next beacon time
    """

    node.getEndNodeFcntUP()
    sendtoaddr=HARDCODED_PARENT_ADDR
    encrypted_payload = encryptDataPayloadNODE(node, data, node.FcntUP, node.node_address)

    packet = b''
    built_Frame = appendMSGForward(packet, sendtoaddr, len(encrypted_payload), node.node_address, 200, node.FcntUP, encrypted_payload, 0)
    built_Frame = built_Frame[:-4]                                                                      #remove MIC
    MIC = calcualteMIC(built_Frame, node.NwkSkey)
    built_Frame = appendMSGForward(packet, sendtoaddr, len(encrypted_payload), node.node_address, 200, node.FcntUP, encrypted_payload, int(MIC, 16))
    parsed_Frame = MsgForwardType.parse(built_Frame)
    sortData(node, parsed_Frame, parsed_Frame.DeviceAddress)
    return


def applicationDataReceived(node, frame):
    """
    applicationDataReceived(): received the application data(for this node) from a neighbouring node
    """

    print("Data frame received!")    
    packet = b''
    built_Frame = appendMSGForward(packet, node.node_address, frame.Length, frame.Sender, frame.FPort, frame.FCnt, frame.Payload, 0)
    built_Frame = built_Frame[:-4]                      #remove MIC
    MIC = calcualteMIC(built_Frame, node.NwkSkey)
    if(frame.MIC == int(MIC, 16)):
        print("MIC correct!")
    else:
        print("MIC incorrect!")

    FCntDown = node.getEndNodeFcntDOWN()
    if (FCntDown != frame.FCnt):
        print("Frame counter incorrect, dropping the frame.")
        return
    decrypted_payload = encryptDataPayloadNODE(node, frame.Payload, FCntDown, frame.Sender)
    decrypted_payload = list(decrypted_payload)
    print("\n------------------------------------------")
    print("Payload received!!!! Payload:")
    print(decrypted_payload)
    print("\n\n")


def encryptDataPayloadNODE(node, payload, Fcnt, Sender):
    """
    encryptDataPayloadNODE(): encrypt or decrypt a payload on the NODE (for outgoing or received packet)
    """
    encrypted_payload = b''
    numOfBlocks = int(len(payload)/AES128_BLOCK_SIZE)                                                    #how many blocks of 16 bytes will we have
    if (len(payload)%AES128_BLOCK_SIZE != 0):
        numOfBlocks+=1
    for i in range(numOfBlocks):
        encryptionBytes = bytearray()
        encryptionBytes.append(1)
        pad = 0
        encryptionBytes.extend(pad.to_bytes(length=4, byteorder='big'))
        encryptionBytes.append(0)
        encryptionBytes.extend(Sender.to_bytes(length=4, byteorder='big'))
        encryptionBytes.extend(Fcnt.to_bytes(length=4, byteorder='big'))
        encryptionBytes.append(i)
        data_block = payload[i*AES128_BLOCK_SIZE:((i+1)*AES128_BLOCK_SIZE)]                               #extract each block of data
        Si_block = LoRaEncrypt(node.AppSkey, encryptionBytes)                                             #encrypt the bytes into a 16 bytes key
        encrypted_payload = encrypted_payload + XOR_bytes(data_block, Si_block)                           #XOR the key block and data block
    return encrypted_payload
    
def encryptDataPayloadGATEWAY(pForwarder, frame, senderNodeIndex):
    """
    encryptDataPayloadGATEWAY(): encrypt or decrypt a payload on the GATEWAY(HP) (for outgoing or received packet)
    """
    numOfBlocks = int(len(frame.Payload)/AES128_BLOCK_SIZE)                                               #how many blocks of 16 bytes will we have
    if (len(frame.Payload)%AES128_BLOCK_SIZE != 0):
        numOfBlocks+=1
    encrypted_payload = b''
    for i in range(numOfBlocks):
        encryptionBytes = bytearray()
        encryptionBytes.append(1)
        pad = 0
        encryptionBytes.extend(pad.to_bytes(length=4, byteorder='big'))
        encryptionBytes.append(0)
        encryptionBytes.extend(frame.Sender.to_bytes(length=4, byteorder='big'))
        encryptionBytes.extend(frame.FCnt.to_bytes(length=4, byteorder='big'))
        encryptionBytes.append(i)
        data_block = bytearray(frame.Payload)[i*AES128_BLOCK_SIZE:((i+1)*AES128_BLOCK_SIZE)]               #extract each block of data
        Si_block = LoRaEncrypt(pForwarder.NS_endNodeData[senderNodeIndex]["AppSkey"], encryptionBytes)
        encrypted_payload = encrypted_payload + XOR_bytes(data_block, Si_block)          
    return encrypted_payload

def calcualteMIC(built_Frame, key):
    """
    calcualteMIC(): calculate MIC for a new packet
    """
    appendBytes = 0
    if(built_Frame[0] == int(MMTYPEType.MsgThisNode)):   
        built_Frame = built_Frame + appendBytes.to_bytes(5, byteorder ='big')   #needs 5 additional bytes to form an AES block
    elif(built_Frame[0] == int(MMTYPEType.MsgForward)):
        built_Frame = built_Frame + appendBytes.to_bytes(1, byteorder ='big')   #needs 1 additional byte to form an AES block
    MIC = calculateMsgMIC(key , built_Frame.hex())
    return MIC

def checkMIC(built_Frame, key):
    """
    checkMIC(): check MIC for a received packet
    """
    if int(built_Frame.MMType) == int(MMTYPEType.OTAARegReq):
        MIC = calculateMICRegReq(key,  built_Frame.JoinEUI, built_Frame.DeviceEUI, built_Frame.DevNonce)
    elif int(built_Frame.MMType) == int(MMTYPEType.OTAARegAck):
        MIC = calculateMICRegAck(key, built_Frame.AppNonce, built_Frame.NetID, built_Frame.DevAddr)
    if (int(MIC, 16) == built_Frame.MIC):      
        print("MIC CORRECT, forwarding the packet.")
        return True
    else:
        print("MIC incorrect, droping the packet.")
        return False


def XOR_bytes(data, Si):
    data, Si = Si[:len(data)], data[:len(Si)]
    int_data = int.from_bytes(data, "big")
    int_Si = int.from_bytes(Si, "big")
    int_enc = int_data ^ int_Si
    return int_enc.to_bytes(len(data), "big")

