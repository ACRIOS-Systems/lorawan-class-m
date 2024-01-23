import socket
import json
from .NS_packetForwarderQueues import *
from time import *
import random
from enum import IntEnum, Enum
from mesh_encryption import *

from ns_chirpstack3_api.sqlCleanup import sqlCleanup,redisCleanup
import ns_chirpstack3_api.nsConnector as nsConn
from time import sleep
import os

from MoteEmulator.mac import Gateway
from MoteEmulator.mac import Mote
from MoteEmulator.network import UDPClient
import base64
import json

HARDCODED_PARENT_ADDR = 1

class LoRaM_PacketTypes(IntEnum):
    CRWBeacon = 0x81,                        
    SyncBeacon = 0x80,                     
    RoutingBeacon = 0x82,           
    SendingData = 0x83,      
    OTAARegAck = 0x84,
    OTAARegReq = 0x85,
    RoutingBeaconRequest = 0x86,
    MsgThisNode = 0x32,
    MsgForward = 0x33

class LoRaPacketTypes(IntEnum):
    JoinRequest = 0x00,                        
    JoinAccept = 0x01,                     
    UnconfirmedDataUp = 0x02,           
    UnconfirmedDataDown = 0x03,      
    ConfirmedDataUp = 0x04,
    ConfirmedDataDown = 0x05,
    RFU = 0x06,
    Proprietary = 0x07

class   donwlinkDotDict(dict):
    """dot notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

################################## PROVISIONING #########################################

def RxCallback(ReceivedData, port, timestamp, context, deveui, userdata):
    pass
    #print("Received data at port %d" % port)
    #print(userdata)

def JoinedCallback(timestamp, context, deveui, userdata):
    pass
    #print(deveui + " successfully joined!")
    #print(userdata)
    
def JoinRequestCallback(timestamp, deveui, joinRequestData):
    pass
    #print(deveui + " wants to join!")

def initialProvisioning(packetForwarder):
    nsConn.networkServerRegisterGateway({"identification": "test", "description": "test gateway", "latitude": 49, "longitude": 15, "altitude": 330, "gweui": packetForwarder.deviceEUI})
    nsConn.networkServerRegisterNode({"deveui":"aabbccddeeff0002", "name":"testDevice", "appkey":"e2c982801d7198d7772dab3b6917db83", "description": "This is my test device"}, RxCallback, JoinedCallback, JoinRequestCallback, "")
    nsConn.networkServerRegisterNode({"deveui":"aabbccddeeff0003", "name":"testDevice2", "appkey":"e2c982801d7198d7772dab3b6917db83", "description": "This is my test device2"}, RxCallback, JoinedCallback, JoinRequestCallback,"")


################################## PACKET FORWARDER #########################################

class packetForwarder:
    def __init__(self, DeviceEUI):
        self.pullTime = 5
        self.PF_timestamp = 0
        self.deviceEUI = (DeviceEUI.to_bytes(8, 'big')).hex()
        self.PF_DataQueues = NS_Queue()
        self.NS_endNodeData = []

    ################################ CHIRPSTACK PROVISIONING REQUESTS ###############################

    def initialiseNS(self):
        nsConn.networkServerInitialize("192.168.32.161", "192.168.32.161", "astest")
        # Cleanup NS and nonces in its database
        nsConn.networkServerPurge()
        sleep(1) # Program hangs without this
        # Live LoRaWAN frames keep sitting somewhere in the ChirpStack database even if the gateway is removed.
        # They are in Redis database!
        sqlCleanup()
        redisCleanup()
        
    def getNodeKeys(self, deveui):
        return nsConn.networkServerGetNodeKeys(deveui)
    
    def getProvosionedGateways(self):
        return nsConn.listProvisionedGateways()
    
    def getProvosionedDevices(self):
        return nsConn.listProvisionedDevices()
    
    
    def NSaddEndNode(self, DeviceEUI, AppKey, JoinEUI, DevNonce, MoteClass, DeviceAddress, JoinNonce, NetID, NwkSkey, AppSkey, FCntUp, FCntDown):
        """
        NSaddEndNode(): adds end node to the list of end nodes for the NS
        """
        #Filled on provisioning search
        NS_endNode = {}
        NS_endNode["DeviceEUI"] = DeviceEUI
        NS_endNode["AppKey"] = AppKey
        #Filled on Join-request
        NS_endNode["JoinEUI"] = JoinEUI
        NS_endNode["DevNonce"] = DevNonce
        NS_endNode["MoteClass"] = MoteClass
        #Filled on Join-Accept
        NS_endNode["DeviceAddress"] = DeviceAddress
        NS_endNode["JoinNonce"] = JoinNonce
        NS_endNode["NetID"] = NetID
        NS_endNode["NwkSkey"] = NwkSkey
        NS_endNode["AppSkey"] = AppSkey
        #Updated on every data packet
        NS_endNode["FCntUp"] = FCntUp
        NS_endNode["FCntDown"] = FCntDown
        self.NS_endNodeData.append(NS_endNode)

    def returnEndNodeIndex(self, devEUI):
        """
        returnEndNodeIndex(): return the list index of an end node
        """
        for index in range(len(self.NS_endNodeData)):
            if(self.NS_endNodeData[index]["DeviceEUI"] == devEUI):
                return index
        return "None"
            
    def returnEndNodeIndexAddr(self, devAddr:int):
        """
        returnEndNodeIndex(): return the list index of an end node
        """
        for index in range(len(self.NS_endNodeData)):
            if(int(self.NS_endNodeData[index]["DeviceAddress"], 16) == devAddr):
                return index
            return "None"
            
    def NSdeleteEndNode(self, index):
        """
        NSdeleteEndNode(): delete the end node
        """
        del self.NSendNodeData[index]


def packetForwarderLoop(pForwarder):

    pForwarder.initialiseNS()                                           #Initialise the NS
    initialProvisioning(pForwarder)                                     #Provision the GW + NODES

    ProvisionedGateway = pForwarder.getProvosionedGateways()            #get a list of provosioned GW PARAMETERS
    ProvisionedDevices = pForwarder.getProvosionedDevices()             #get a list of provisioned nodes with parameters
    for ProvisionedDevice_deveui in ProvisionedDevices._values:         #retreive and store AppKey and DevEUI for each device
        ProvisionedDevice_appkey = pForwarder.getNodeKeys(ProvisionedDevice_deveui.dev_eui)
        pForwarder.NSaddEndNode(ProvisionedDevice_deveui.dev_eui, ProvisionedDevice_appkey, JoinEUI=0, DevNonce=0, MoteClass=0, DeviceAddress='0', JoinNonce=0, NetID=0, NwkSkey=0, AppSkey=0, FCntUp=-1, FCntDown=-1)

    UDP = UDPClient(('127.0.0.1', 1700), ('127.0.0.1', 3333), timeout=10)
    HP = Gateway(ProvisionedGateway._values[0].id)
    while(1):
        runMote(pForwarder, UDP, HP)

def runMote(pForwarder, UDP:UDPClient, HP:Gateway):
    ################################### NETWORK SERVER INPUT QUEUE ###############################################
    if(pForwarder.PF_DataQueues.NS_input_size() > 0):                   #check queue
        packet = pForwarder.PF_DataQueues.NS_input_take()

        ################################### REG REQUEST + REG ACK ##############################################
        if(int(packet.MMType) == LoRaM_PacketTypes.OTAARegReq.value):   #if packet is RegReq
            deviceEUI = packet.DeviceEUI.to_bytes(8, 'big')
            deviceEUI = deviceEUI.hex()
            joinEUI = packet.JoinEUI.to_bytes(8, 'big')
            joinEUI = joinEUI.hex()
            devNonce = packet.DevNonce.to_bytes(2, 'big')
            devNonce = devNonce.hex()
            nodeIndex = pForwarder.returnEndNodeIndex(deviceEUI)                #check if the node is registered in the NS

            if(nodeIndex != 'None'):
                appkey = pForwarder.NS_endNodeData[nodeIndex]["AppKey"]
                nwkkey=appkey #lora 1.0 spec -> appkey == nwkkey
                MoteNode = Mote(joinEUI, deviceEUI, appkey, nwkkey)             
                pForwarder.NS_endNodeData[nodeIndex]["JoinEUI"] = joinEUI       #update the end node dictionary
                pForwarder.NS_endNodeData[nodeIndex]["DevNonce"] = devNonce
                pForwarder.NS_endNodeData[nodeIndex]["MoteClass"] = MoteNode
                joinRequest = MoteNode.form_join(devNonce)                      #form LoRa join request

                parsedPacket = HP.push(UDP, joinRequest, MoteNode)              #push the JoinRequest packet to the NS
                if (parsedPacket != False):
                    if(parsedPacket["MType"] == LoRaPacketTypes.JoinAccept.value):
                        packetToGateway = {}
                        packetToGateway["packetType"] = LoRaM_PacketTypes.OTAARegAck.value   
                        packetToGateway["deviceEUI"] = deviceEUI
                        packetToGateway["DeviceAddress"] = parsedPacket["DevAddr"]
                        packetToGateway["NetID"] = parsedPacket["NetID"]
                        packetToGateway["JoinNonce"] = parsedPacket["JoinNonce"]
                        pForwarder.PF_DataQueues.NS_output_add(packetToGateway)             #put the RegAck data to the NS_output queue

                        pForwarder.NS_endNodeData[nodeIndex]["DeviceAddress"] = parsedPacket["DevAddr"] #update the end node dictionary
                        pForwarder.NS_endNodeData[nodeIndex]["JoinNonce"] = parsedPacket["JoinNonce"]
                        pForwarder.NS_endNodeData[nodeIndex]["NetID"] = parsedPacket["NetID"]
                        pForwarder.NS_endNodeData[nodeIndex]["NwkSkey"] = list(getNwkSkey(pForwarder.NS_endNodeData[nodeIndex]["AppKey"], pForwarder.NS_endNodeData[nodeIndex]["DevNonce"], parsedPacket["JoinNonce"], parsedPacket["NetID"]))[0]
                        pForwarder.NS_endNodeData[nodeIndex]["AppSkey"] = list(getAppSkey(pForwarder.NS_endNodeData[nodeIndex]["AppKey"], pForwarder.NS_endNodeData[nodeIndex]["DevNonce"], parsedPacket["JoinNonce"], parsedPacket["NetID"]))[0]

        ################################### INPUT DATA ##############################################
        if(int(packet.MMType) == LoRaM_PacketTypes.MsgThisNode.value):
            nodeIndex = pForwarder.returnEndNodeIndexAddr(packet.Sender)
            if nodeIndex != 'None':
                MoteNode = pForwarder.NS_endNodeData[nodeIndex]["MoteClass"]
                try:
                    uplink_payload = MoteNode.form_phypld(packet.FPort, packet.Payload)
                    HP.push(UDP, uplink_payload, MoteNode)
                except:
                    print("Error - forming/trasmitting the payload.")
    
    ################################### NETWORK SERVER OUPUT QUEUE ##############################################
    elif (time() > pForwarder.PF_timestamp+pForwarder.pullTime):              #TODO-timer overflow fix?
        pForwarder.PF_timestamp = time()
        response = HP.pull(UDP)

    try:
        response = UDP.recv()
        if response != 0 and response != None:                                         
            dataPayload = HP.parse_pullresp(response[0], None, True)                                                #remove the Semtech UDP packet       
            mtype, deviceAddress = HP.extractDeviceAddressAndMtype(dataPayload)                                     #extract the device address (to obtain the correct Mote)
            #if(mtype == LoRaPacketTypes.ConfirmedDataDown.value):
            HP.TX_ACK(pForwarder.deviceEUI, response, UDP)                                                          #send back the ACK packet
            if deviceAddress == False:
                print("Unknown downstream packet.")                         
                return                          
            nodeIndex = pForwarder.returnEndNodeIndexAddr(int(deviceAddress, 16))                                        #find the Device index
            if nodeIndex != 'None':
                downlink_packet = HP.parse_pullresp(response[0], pForwarder.NS_endNodeData[nodeIndex]["MoteClass"], False)   #parse the payload with the correct encryption keys
                print(downlink_packet)
                if(downlink_packet["MType"] == LoRaPacketTypes.UnconfirmedDataDown.value or downlink_packet["MType"] == LoRaPacketTypes.ConfirmedDataDown.value):
                    packetToGateway = {}
                    packetToGateway["packetType"] = LoRaM_PacketTypes.MsgForward.value
                    packetToGateway["EndDeviceAddr"] = downlink_packet["EndDeviceAddr"]
                    packetToGateway["Sender"] = HARDCODED_PARENT_ADDR                                       #sender will be hardcoded parent (sending downling data message)
                    packetToGateway["FPort"] = downlink_packet["FPort"]
                    packetToGateway["FCnt"] = downlink_packet["FCntDown"]
                    payloadList = list(downlink_packet["Payload"])
                    packetToGateway["Payload"] = payloadList
                    packetToGateway = donwlinkDotDict(packetToGateway)
                    pForwarder.PF_DataQueues.NS_output_add(packetToGateway)
    except:
        print("No packets sent by the Network Server. Continuing...")

#TODO:  - rejoin requests, removing node upon disconnection etc...
    #   - connect lora-m FCnt with the mote emulator one... (also check devnonce and port)
    #   - retransmission of a packet to/from NS in case of failed communications
    #   - implementation of network variables to the Semtech protocol (RSSI/SF/bandwidth/SNR etc..)
    #   - error printouts
    #   - timer overflow
    #   - recheck B0 and A0 encryption frames and add them where necessarry
    #   - queue thread protection