import modules
from mesh_definitions import *
from mesh_parsing_building import *
from RadioInterface import *
from NodeInterface import *
import random
from mesh_encryption import *
from mesh_data import *
from mesh_createNodeRelations import *
from mesh_application import *
from mesh_clockEvents import *
import numpy as np


""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
def meshIdleState(node, event, eventData):
    """
    meshIdleState(): New Node starting point.
    The node can either be a Hardcoded parent or a node without a parent.\n
    Node without a parent -> Starts the parent acquisition procedure.\n
    Hardcoded parent -> Set the operating frequency and SF to be the same as his parent (gateway/NS) and
    adjusts his time slot to the parent's time slot +1 slot. Switches to the ConnectedIdle mode.
    """

    if len(node.parents) == 0:
        node.getBeaconingFrequency()
        node.getBeaconingSF()
        node.startReception(node.currentFrequency, node.currentSF, MeshBeaconingScanTime)
        node.timestamp = node.getTimestamp(node)
        node.setState(MeshNodeState.searchParent)

    elif node.node_address == HARDCODED_PARENT_ADDR:
        node.NetworkDepth = 0
        node.parentIndex = 0
        node.currentFrequency = node.parents[node.parentIndex]["Frequency"]
        node.currentSF = node.parents[node.parentIndex]["SF"]
        node.meshTimers.node_beacon_time = node.getTimestamp(node) + 5000                      #calcualte the time of this node beacon (current time)
        node.timestamp = node.getTimestamp(node)
        node.meshTimers.pushEvent(MeshNodeEvents.TRANSMITTING_BEACON, 0, 'None')
        node.setState(MeshNodeState.connectedIdle)
    return

""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
def meshSearchParent(node, event, eventData):
    """
    meshSearchParent(): Search for a potential parent for this node. If a CRW beacon is received, the node adds the potential parent to the \n
    list of potential parents with all its parameters and makes a decision wether to request a connection based on the parameters \n
    received and parameters saved from other potential parents in the area.\n
    Reopens the Reception until total scan time >= the duration of 1 epoch time on each SF/Frequency.
    """

    if event == MeshNodeEvents.poll:
        if meshHasElapsed(node, node.timestamp, MeshBeaconingScanTime):
            print("Scan timed out!")
            node.setState(MeshNodeState.idleState)

    elif event == MeshNodeEvents.IRQ_PREAMBLE_DETECTED:
        if Timestamp_interface == 0:
            node.beaconTimeEstimate = node.getTimestamp(node) - returnPreableLen(node) - TransmissionDelay      #sent beacon estimated GPS time
        else:
            node.beaconTimeEstimate = -TransmissionDelay

    elif event == MeshNodeEvents.IRQ_CRC_ERROR:
        node.startReception(node.currentFrequency, node.currentSF, (MeshBeaconingScanTime-(node.getTimestamp(node)-node.timestamp))) #scan more on the same SF and freq (for the rest of the beaconing period)

    elif event == MeshNodeEvents.IRQ_TX_DONE:
        node.startReception(node.currentFrequency, node.currentSF, (MeshBeaconingScanTime-(node.getTimestamp(node)-node.timestamp))) #scan more on the same SF and freq

    elif event == MeshNodeEvents.IRQ_RX_TX_TIMEOUT:
        print("Scan timed out!")
        node.setState(MeshNodeState.idleState)

    elif event == MeshNodeEvents.IRQ_RX_DONE:
        packet = IrqRxDoneEventDataType(**eventData)
        print("Packet SNR: " + str(packet.SNR))
        print("Packet RSSI: " + str(packet.RSSI))
        if parse_Packet(node, packet.payload) != True:
            print("Wrong packet!")
            node.startReception(node.currentFrequency, node.currentSF, MeshBeaconingScanTime)
            return
        for i in range(len(node.Packet_Beacon_Frames)):
            if node.Packet_Beacon_Frames[i].MMType == "CRWBeacon":

                """Sync potential parent time with my HW time"""
                node.GPSTime = node.Packet_timestamp + TransmissionDelay
                node.HWclockSynchronisedWithParent = node.synchronizeHWClock()
                """"""

                potentialParent = createPotentialParent(node.Packet_DevAddr, node.currentFrequency, node.currentSF, node.Packet_timestamp, node.Packet_Beacon_Frames[i].NetworkDepth, 0, node.Packet_Beacon_Frames[i].FreeSlots)
                #TODO-add RSSI^

                potentialParentIndex = node.findPotentialParent(potentialParent["DeviceAddress"])   #check if this potential parent is already on our list
                if potentialParentIndex == "None":
                    potentialParentIndex = len(node.potentialParents)
                    node.potentialParents.append(potentialParent)
                    print("New potentialParent with address "+ str(node.Packet_DevAddr) +" added!")
                else:
                    print("Device "+str(potentialParent["DeviceAddress"])+" already on the list of potential parents, time slot and Index updated.")
                    node.potentialParents[potentialParentIndex]["timeSlot"] = potentialParent["timeSlot"]

                #TODO - add algorithm to determine routing data/connection request here!
                    #- add a way for the algorithm to start searching for the chosen potential parent CRW beacon on some condition
                algorithm = True

                if algorithm == False:
                    node.setState(MeshNodeState.idleState)
                else:                               #request a connection to the parent
                    i = len(node.eQueue.eQueue)
                    while i>0:
                        node.eQueue.popQueue()      #empty the event queue
                        i-=1

                    node.meshTimers.pushEvent(MeshNodeEvents.potentialParent_BEACON, 0, node.potentialParentIndex)

                    node.NetworkDepth = node.potentialParents[node.potentialParentIndex]["NetworkDepth"]+1
                    sleep(((TimeSlotSize/2)/1000))                                                    #sleep until the end of this time slot
                    OTAARegReq_timeSlot = node.rng.randrange(RNG_RANGE_L_TIME, RNG_RANGE_H_TIME, RNG_STEP_TIME)
                    sleep(OTAARegReq_timeSlot*(TimeSlotSize/1000))                                  #choose a random time slot 1-5 to respond in with the OTAARegReq

                    mic = calculateMICRegReq(node.AppKey, node.JoinEUI, node.deviceEUI, node.getDevNonce())
                    packet = buildBeacon(node.node_address, node.getTimestamp(node))
                    packet = appendOTAARegReqBeacon(packet, node.Packet_DevAddr, node.DevNonce, node.JoinEUI, node.deviceEUI, int(mic, 16))

                    node.timestamp = node.getTimestamp(node)
                    node.startTransmission(node.currentFrequency, node.currentSF, packet)
                    node.setState(MeshNodeState.transmittingOTAARegReq)
                    return
            else:
                node.startReception(node.currentFrequency, node.currentSF, (MeshBeaconingScanTime-(node.getTimestamp(node)-node.timestamp))) #scan more on the same SF and freq

""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
def meshTransmittingOTAARegReq(node, event, eventData):
    """
    meshTransmittingOTAARegReq(): The Registration Request was transmitted, wait for the confirmation of transmission.
    """

    if event == MeshNodeEvents.poll:
        if meshHasElapsed(node, node.timestamp, RadioTimeout):
            print("Transmission of a packet timed out!")
            node.setState(MeshNodeState.idleState)

    elif event == MeshNodeEvents.IRQ_RX_TX_TIMEOUT:
        print("Transmission of a packet timed out!")
        node.setState(MeshNodeState.idleState)

    elif event == MeshNodeEvents.IRQ_TX_DONE:
        node.setState(MeshNodeState.waitForPotentialParentWindow)
    return

""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
def meshWaitForPotentialParentWindow(node, event, eventData):
    """
    meshWaitForPotentialParentWindow(): Wait for the next potentialParent beacon event to check for Registration Acknowledgement.
    """

    if event == MeshNodeEvents.poll:
        pass

    elif event == MeshNodeEvents.potentialParent_BEACON:  #start reception in potentialParent timeSlot
        node.startReception(node.currentFrequency, node.currentSF, RadioTimeout)
        node.timestamp = node.getTimestamp(node)
        node.setState(MeshNodeState.waitForRequestConnectionAnswer)
    return

""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
def meshWaitForRequestConnectionAnswer(node, event, eventData):
    """
    meshWaitForRequestConnectionAnswer(): Wait for OTAARegAck message from the chosen parent (confirmed by the NS). When received,
    save my parent on the list with its configurations, configure my settings (network depth, time slot, address,...) and derive
    networkSkey and appSkey for further app-data communication. Push my and my parent's beacon events to the eventQueue and set state to ConnectedIdle.\n
    If connection answer timeout number is larger than NetworkDepth of the chosen parent, drop the parent and search for a new one.
    """

    if event == MeshNodeEvents.poll:
        if meshHasElapsed(node, node.timestamp, RadioTimeout):                  #check for timeout
            print("Scan for confirmation reply timed out!")                     #if no confirmation received on the Xth try, delete the potential parent
            if node.potentialParents[node.potentialParentIndex]["connectionCounter"] >= (node.NetworkDepth*CONNECTION_RETRY_NUM):
                print("Potential parent with DeviceAddress "+str(node.potentialParents[node.potentialParentIndex]["DeviceAddress"])+" removed, beacon not received in "+str(node.NetworkDepth*CONNECTION_RETRY_NUM)+" tries.")
                del node.potentialParents[node.potentialParentIndex]
                node.setState(MeshNodeState.idleState)
            else:                                                               #if no confirmation received, QUEUE the event again
                node.potentialParents[node.potentialParentIndex]["connectionCounter"] += 1
                node.meshTimers.pushEvent(MeshNodeEvents.potentialParent_BEACON, 0, node.potentialParentIndex)
                node.setState(MeshNodeState.waitForPotentialParentWindow)

    elif event == MeshNodeEvents.IRQ_PREAMBLE_DETECTED:
        if Timestamp_interface == 0:
            node.beaconTimeEstimate = node.getTimestamp(node) - returnPreableLen(node) - TransmissionDelay      #sent beacon estimated GPS time
        else:
            node.beaconTimeEstimate = -TransmissionDelay

    elif event == MeshNodeEvents.IRQ_CRC_ERROR:
        node.setState(MeshNodeState.idleState)

    elif event == MeshNodeEvents.IRQ_RX_TX_TIMEOUT:
        print("Scan for confirmation reply timed out!")                     #if no confirmation received on the Xth try, delete the potential parent
        if node.potentialParents[node.potentialParentIndex]["connectionCounter"] >= (node.NetworkDepth*CONNECTION_RETRY_NUM):
            print("Potential parent with DeviceAddress "+str(node.potentialParents[node.potentialParentIndex]["DeviceAddress"])+" removed, beacon not received in "+str(node.NetworkDepth*CONNECTION_RETRY_NUM)+" tries.")
            del node.potentialParents[node.potentialParentIndex]
            node.setState(MeshNodeState.idleState)
        else:                                                               #if no confirmation received, QUEUE the event again
            node.potentialParents[node.potentialParentIndex]["connectionCounter"] += 1
            node.meshTimers.pushEvent(MeshNodeEvents.potentialParent_BEACON, 0, node.potentialParentIndex)

            node.setState(MeshNodeState.waitForPotentialParentWindow)

    elif event == MeshNodeEvents.IRQ_RX_DONE:
        packet = IrqRxDoneEventDataType(**eventData)
        print("Packet SNR: " + str(packet.SNR))
        print("Packet RSSI: " + str(packet.RSSI))
        if parse_Packet(node, packet.payload) != True:                      #parse the frames
            print("Wrong packet!")
            return

        for i in range(len(node.Packet_Beacon_Frames)):
            if node.Packet_Beacon_Frames[i].MMType == "OTAARegAck" and node.Packet_Beacon_Frames[i].DeviceEUI == node.deviceEUI \
                and node.potentialParents[node.potentialParentIndex]["DeviceAddress"] == node.Packet_DevAddr:  #if the packet is OTAARegAck and device addresses match

                """Configure my parent's settings"""
                parent = createParent(node.Packet_DevAddr, node.currentFrequency, node.currentSF, node.Packet_timestamp)
                node.parentIndex = len(node.parents)
                node.parents.append(parent)
                print("New parent confirmed!")
                node.parents[node.parentIndex]["AccessNodes"].append(1)   #append address of the highest parent in the topology (1) (hardcoded parent)

                """Fix my GPS time"""
                node.GPSTime = parent["timeSlot"] + TransmissionDelay           #update to the correct GPS time (this variable contains an error of UART+LoRa transmissions)
                node.HWclockSynchronisedWithParent = node.synchronizeHWClock()  #get the HW clock at this time - this is a HW clock equivalent to the GPS time - whenever the HW clock changes, the GPS time changes by the same amount

                """Configure my settings"""
                node.node_address = node.Packet_Beacon_Frames[i].ChildAddress
                print("MY ADDRESS IS " + str(node.node_address))
                node.myTimeSlot = node.Packet_Beacon_Frames[i].TimeSlot
                node.meshTimers.node_beacon_time = parent["timeSlot"] + node.myTimeSlot           #my beacon time is parent's time + the time slot number [in miliseconds] sent by the parent
                node.timeSlots[(len(node.timeSlots)-int(node.Packet_Beacon_Frames[i].TimeSlot/TimeSlotSize))] = True    #add the parent's time slot to the array
                print(node.timeSlots)
                del node.potentialParents[node.potentialParentIndex]      #delete the potential parent

                """Encryption Key derivation"""
                decrypted_bytes = LoRaDecrypt(node.AppKey, node.Packet_Beacon_Frames[i].Payload.to_bytes(16, byteorder ='little'))
                devNonce = node.DevNonce.to_bytes(2, 'big')
                devNonce = devNonce.hex()
                joinnonce = decrypted_bytes[0:3].hex()
                if(int(joinnonce, 16) <= node.JoinNonce):
                    print("Incorrect JoinNonce, dropping the Registration Acknowledgement.")
                    break
                else:
                    node.JoinNonce = joinnonce
                node.NetID = decrypted_bytes[3:6].hex()
                received_mic = decrypted_bytes[6:10].hex()
                mic = calculateMICRegAck(node.AppKey, int(node.JoinNonce, 16), int(node.NetID, 16), node.Packet_Beacon_Frames[i].ChildAddress)
                if (received_mic != mic):
                    print("Incorrect MIC, dropping the Registration Acknowledgement.")
                    break

                node.NwkSkey = list(getNwkSkey(node.AppKey, devNonce, node.JoinNonce, node.NetID))[0]           #calculate the keys
                node.AppSkey = list(getAppSkey(node.AppKey, devNonce, node.JoinNonce, node.NetID))[0]  

                print("NwkSkey: ")
                print(node.NwkSkey)
                print("AppSkey: ")
                print(node.AppSkey)

                """Push new events"""
                node.meshTimers.pushEvent(MeshNodeEvents.PARENT_BEACON, 0, node.parentIndex)     #push parents beacon
                node.meshTimers.pushEvent(MeshNodeEvents.TRANSMITTING_BEACON,  0, 'None')        #push my beacon

                node.setState(MeshNodeState.connectedIdle)
                return

        print("No Acknowledgement included in the packet.")
        node.potentialParents[node.potentialParentIndex]["connectionCounter"] += 1
        if node.potentialParents[node.potentialParentIndex]["connectionCounter"] >= (node.NetworkDepth*CONNECTION_RETRY_NUM):
                print("Potential parent with DeviceAddress "+str(node.potentialParents[node.potentialParentIndex]["DeviceAddress"])+" removed, beacon not received in "+str(node.NetworkDepth*CONNECTION_RETRY_NUM)+" tries.")
                del node.potentialParents[node.potentialParentIndex]
                node.setState(MeshNodeState.idleState)
                return
        node.potentialParents[node.potentialParentIndex]["timeSlot"] = node.Packet_timestamp
        node.HWclockSynchronisedWithParent = node.synchronizeHWClock()
        node.GPSTime = node.Packet_timestamp + TransmissionDelay
        node.meshTimers.pushEvent(MeshNodeEvents.potentialParent_BEACON, 0, node.potentialParentIndex)
        node.setState(MeshNodeState.waitForPotentialParentWindow)
    return

""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
def meshConnectedIdle(node, event, eventData):
    """
    meshConnectedIdle(): Process the events, consumed by the node from eventQueue.\n
    TRANSMITTING_BEACON -> build a beacon (CRW/Sync/SendingData), aggregate data from the node dataQueues to it and transmit it. If CRW beacon was sent,
    set state to transmittingCRWBeacon, othervise transmittingBeacon.\n
    CHILD_BEACON -> start the reception for child beacon.\n
    PARENT_BEACON -> start the reception for parent beacon.
    """

    if event == MeshNodeEvents.poll:
        pass

    elif event == MeshNodeEvents.TRANSMITTING_BEACON:
        if Timestamp_interface == 0 or node.node_address == HARDCODED_PARENT_ADDR:
            packet = buildBeacon(node.node_address, node.getTimestamp(node))    #prepare the initial packet INFO
        else:
            packet = buildBeacon(node.node_address, node.GPSTime + node.myTimeSlot)    #prepare the initial packet INFO
        CRW_time = node.isCRWTime()
        if CRW_time == True:                                                #determine if it is time for crw beacon or not
            packet = appendCRWBeacon(packet, len(node.timeSlots)-node.timeSlotsTaken, node.NetworkDepth)
        packet = appendNodeData(node, packet, node.currentSF)               #check if there is any data to send

        if len(packet) <= PACKET_INFO_LEN:                                  #if packet only contains the packet INFO and nothing else add sync beacon
            packet = appendSyncBeacon(packet)

        if CRW_time == True:
            for i in range(1, CRWMAXCount + 2):   #  Push 6 events for expiring time slots (CRW Registration Request related)
                node.meshTimers.pushEvent(MeshNodeEvents.TIME_SLOT_EXPIRED, (TimeSlotSize*(i)-TimeSlotPadding), 'None')

            node.setState(MeshNodeState.transmittingCRWBeacon)
        else:
            node.setState(MeshNodeState.transmittingBeacon)

        node.timestamp = node.getTimestamp(node)
        node.startTransmission(node.currentFrequency, node.currentSF, packet)

        if node.node_address == HARDCODED_PARENT_ADDR:
            for childIndex in range(len(node.children)):                                         #children beacons
                node.meshTimers.pushEvent(MeshNodeEvents.CHILD_BEACON, 0, childIndex)
            node.meshTimers.pushEvent(MeshNodeEvents.TRANSMITTING_BEACON, 0, 'None')

    elif event == MeshNodeEvents.CHILD_BEACON:
        node.startReception(node.currentFrequency, node.currentSF, RadioTimeout)
        node.childIndex = node.findChild(eventData)
        node.timestamp = node.getTimestamp(node)
        node.setState(MeshNodeState.waitForChildBeacon)

    elif event == MeshNodeEvents.PARENT_BEACON:
        node.startReception(node.currentFrequency, node.currentSF, RadioTimeout)
        node.parentIndex = node.findParent(eventData)
        node.timestamp = node.getTimestamp(node)
        node.setState(MeshNodeState.waitForParentBeacon)

    return

""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
def meshTransmittingBeacon(node, event, eventData):
    """
    meshTransmittingBeacon(): Transmit my beacon.
    """

    if event == MeshNodeEvents.poll:
        if meshHasElapsed(node, node.timestamp, RadioTimeout):
            print("Beacon transmission timed out!")
            node.setState(MeshNodeState.connectedIdle)

    elif event == MeshNodeEvents.IRQ_RX_TX_TIMEOUT:
        print("Beacon transmission timed out!")
        node.setState(MeshNodeState.connectedIdle)

    elif event == MeshNodeEvents.IRQ_TX_DONE:
        print("Beacon/Data sent!")
        node.setState(MeshNodeState.connectedIdle)
    return

""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
def meshTransmittingCRWBeacon(node, event, eventData):
    """
    meshTransmittingCRWBeacon(): Transmit a CRW beacon. When the Beacon time slot expires, switch to receivingChildNodes state.
    """

    if event == MeshNodeEvents.poll:
        pass

    elif event == MeshNodeEvents.IRQ_RX_TX_TIMEOUT:
        print("CRW beacon transmission timed out!")
        node.setState(MeshNodeState.connectedIdle)

    elif event == MeshNodeEvents.TIME_SLOT_EXPIRED:
        print(node.eventReady)
        print("TimeSlot expired!")
        node.startReception(node.currentFrequency, node.currentSF, RadioTimeout)
        node.setState(MeshNodeState.receivingNewChildNodes)

    elif event == MeshNodeEvents.IRQ_TX_DONE:
        print("CRW Beacon/Data sent!")

    return

""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
def meshReceivingNewChildNodes(node, event, eventData):
    """
    meshReceivingNewChildNodes(): Reopen next 5 time slots one after another to receive child RegistrationRequests.\n
    When a RegistrationRequest is received, create a potentialChild dict with all its parameters and append it to potentialChildren list.
    """

    if event == MeshNodeEvents.poll:
        pass

    elif event == MeshNodeEvents.IRQ_PREAMBLE_DETECTED:
        pass

    elif event == MeshNodeEvents.IRQ_CRC_ERROR:
        print("CRC ERROR!")

    elif event == MeshNodeEvents.TIME_SLOT_EXPIRED:
        if node.CRWCounter >= CRWMAXCount:
            print("CRW window expired!")
            node.CRWCounter = 1
            node.setState(MeshNodeState.connectedIdle)
        elif node.CRWCounter < CRWMAXCount:
            node.CRWCounter = node.CRWCounter+1
            print(node.CRWCounter)
            print("Reopening!")
            node.startReception(node.currentFrequency, node.currentSF, RadioTimeout)

    elif event == MeshNodeEvents.IRQ_RX_TX_TIMEOUT:
        pass

    elif event == MeshNodeEvents.IRQ_RX_DONE:
        packet = IrqRxDoneEventDataType(**eventData)
        print("Packet SNR: " + str(packet.SNR))
        print("Packet RSSI: " + str(packet.RSSI))
        if parse_Packet(node, packet.payload) != True:                          #parse the frames
            print("Wrong packet!")
            return

        for i in range(len(node.Packet_Beacon_Frames)):
            #if it is a Request for connection and it is trying to connect to me (my address)
            if node.Packet_Beacon_Frames[i].MMType == "OTAARegReq" and node.Packet_Beacon_Frames[i].ConnectToDevice == node.node_address:
                print("Potential child with device EUI "+ str(node.Packet_Beacon_Frames[i].DeviceEUI) +" OTAARegReq accepted!")
                potentialChild = createPotentialChild(node.Packet_Beacon_Frames[i].DeviceEUI, node.currentFrequency, node.currentSF)
                potentialChildIndex = node.findPotentialChild(potentialChild["DeviceEUI"])             #check if the potential child is already saved
                if potentialChildIndex == "None":
                    potentialChildIndex = len(node.potentialChildren)
                    node.potentialChildren.append(potentialChild)                                      #append the potential child and set the Index
                    print("New potentialChild with device EUI "+ str(node.Packet_Beacon_Frames[i].DeviceEUI) +" added!")
                else:
                    print("Device "+str(potentialChild["DeviceEUI"])+" already on the list of potential children.")
    return

""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
def meshWaitForChildBeacon(node, event, eventData):
    """
    meshWaitForChildBeacon(): Wait for child beacon.\n
    If RECEIVED -> Child beacon received. If the beacon is carrying an OTAA RegReq for a different node,
    add it to the list of nodes accessible through that child.\n
    If NOT RECEIVED -> Reschedule the CHILD beacon unless it was not received for CONNECTION_RETRY_NUM times, in that case remove the child.
    """

    if event == MeshNodeEvents.poll:
        if meshHasElapsed(node, node.timestamp, RadioTimeout):                                                  #check for timeout
            print("Child "+str(node.children[node.childIndex]["DeviceAddress"])+" node beacon not detected!")   #if no beacon received on the Xth try, delete the child
            if node.children[node.childIndex]["connectionCounter"] >= CONNECTION_RETRY_NUM:
                print("Child with DeviceAddress"+str(node.children[node.childIndex]["DeviceAddress"])+" removed, beacon not received in "+str(CONNECTION_RETRY_NUM)+" tries.")
                node.removeTimeSlot(int((node.children[node.childIndex]["timeSlot"])/TimeSlotSize)) #remove the time slot of this child
                del node.children[node.childIndex]                                                          #delete the child
                node.setState(MeshNodeState.connectedIdle)
            else:                                                                                           #if no beacon received, QUEUE the event again
                node.children[node.childIndex]["connectionCounter"] += 1
                print("Connection counter increased to "+str(node.children[node.childIndex]["connectionCounter"])+"!")
                #TODO - make reception window wider after failure?
                node.setState(MeshNodeState.connectedIdle)

    elif event == MeshNodeEvents.IRQ_PREAMBLE_DETECTED:
        pass

    elif event == MeshNodeEvents.IRQ_CRC_ERROR:
        node.setState(MeshNodeState.connectedIdle)

    elif event == MeshNodeEvents.IRQ_RX_TX_TIMEOUT:
        print("Child "+str(node.children[node.childIndex]["DeviceAddress"])+" node beacon not detected!")   #if no beacon received on the Xth try, delete the child
        if node.children[node.childIndex]["connectionCounter"] >= CONNECTION_RETRY_NUM:
            print("Child with DeviceAddress"+str(node.children[node.childIndex]["DeviceAddress"])+" removed, beacon not received in "+str(CONNECTION_RETRY_NUM)+" tries.")
            node.removeTimeSlot(int((node.children[node.childIndex]["timeSlot"])/TimeSlotSize))             #remove the time slot of this child
            del node.children[node.childIndex]                                                              #delete the child
            node.setState(MeshNodeState.connectedIdle)
        else:                                                                                               #if no beacon received, QUEUE the event again
            node.children[node.childIndex]["connectionCounter"] += 1
            print("Connection counter increased to "+str(node.children[node.childIndex]["connectionCounter"])+"!")
            #TODO - make reception window wider after failure?
            node.setState(MeshNodeState.connectedIdle)

    elif event == MeshNodeEvents.IRQ_RX_DONE:

        packet = IrqRxDoneEventDataType(**eventData)
        print("Packet SNR: " + str(packet.SNR))
        print("Packet RSSI: " + str(packet.RSSI))
        if parse_Packet(node, packet.payload) != True:
            print("Wrong packet!")
            node.setState(MeshNodeState.connectedIdle)
            return

        if node.Packet_DevAddr == node.children[node.childIndex]["DeviceAddress"]:  #if the node is the child in question
            print("Child "+str(node.Packet_DevAddr)+" node beacon received!")
            if node.Packet_DevAddr in node.childrenToBeConfirmed:                   #check if this is the first response of a newly acquired child
                print("New Child Confirmed!")
                node.childrenToBeConfirmed.remove(node.Packet_DevAddr)
            for i in range(len(node.Packet_Data_Frames)):
                if node.Packet_Data_Frames[i].MMType == "OTAARegReq":               #if we acquired a registration request from a child for some unconnected node
                    node.children[node.childIndex]["AccessNodes"].append(node.Packet_Data_Frames[i].DeviceEUI) #add the unconnected node to the list of nodes
            node.setState(MeshNodeState.connectedIdle)
        else:
            print("Incorrect device address.")
            node.setState(MeshNodeState.connectedIdle)
    return

""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
def meshWaitForParentBeacon(node, event, eventData):
    """
    meshWaitForParentBeacon(): Wait for parent beacon.\n
    If RECEIVED -> Parent beacon recepted, sycnhronise the GPS time to the recepted beacon. If the beacon is carrying an OTAA RegAck for a different node
    and that node is in my subnetwork, change the deviceEUI to the assigned node address, saved on the list of nodes accessible through one of my children.\n
    If NOT RECEIVED -> Reschedule the PARENT beacon unless it was not recepted for CONNECTION_RETRY_NUM times, in that case remove the parent and
    set state to idleState (start searching for a new parent).
    """

    if event == MeshNodeEvents.poll:
        if meshHasElapsed(node, node.timestamp, RadioTimeout):                                                  #check for timeout
            print("Parent "+str(node.parents[node.parentIndex]["DeviceAddress"])+" node beacon not detected!")  #if no beacon received on the Xth try, delete the parent
            if node.parents[node.parentIndex]["connectionCounter"] >= CONNECTION_RETRY_NUM:
                print("Parent with DeviceAddress "+str(node.parents[node.parentIndex]["DeviceAddress"])+" removed, beacon not received in "+str(CONNECTION_RETRY_NUM)+" tries.")
                node.removeTimeSlot(len(node.timeSlots)-node.myTimeSlot/TimeSlotSize) #remove my parent slot time

                del node.parents[node.parentIndex]
                node.setState(MeshNodeState.idleState)
            else:                                                                                               #if no beacon received, QUEUE the event again
                node.parents[node.parentIndex]["connectionCounter"] += 1
                print("Connection counter increased to "+str(node.parents[node.parentIndex]["connectionCounter"])+"!")
                #TODO - make reception window wider after failure?
                node.meshTimers.pushEvent(MeshNodeEvents.PARENT_BEACON, 0, node.parentIndex)
                node.meshTimers.pushEvent(MeshNodeEvents.TRANSMITTING_BEACON, 0, 'None')
                for childIndex in range(len(node.children)):                                     #children beacons
                    node.meshTimers.pushEvent(MeshNodeEvents.CHILD_BEACON, 0, childIndex) 
                node.setState(MeshNodeState.connectedIdle)

    elif event == MeshNodeEvents.IRQ_PREAMBLE_DETECTED:
        if Timestamp_interface == 0:
            node.beaconTimeEstimate = node.getTimestamp(node) - returnPreableLen(node) - TransmissionDelay      #sent beacon estimated GPS time
        else:
            node.beaconTimeEstimate = -TransmissionDelay

    elif event == MeshNodeEvents.IRQ_CRC_ERROR:
        node.meshTimers.pushEvent(MeshNodeEvents.PARENT_BEACON, 0, node.parentIndex)
        node.setState(MeshNodeState.connectedIdle)

    elif event == MeshNodeEvents.IRQ_RX_TX_TIMEOUT:
        print("Parent "+str(node.parents[node.parentIndex]["DeviceAddress"])+" node beacon not detected!")  #if no beacon received on the Xth try, delete the parent
        if node.parents[node.parentIndex]["connectionCounter"] >= CONNECTION_RETRY_NUM:
            print("Parent with DeviceAddress "+str(node.parents[node.parentIndex]["DeviceAddress"])+" removed, beacon not received in "+str(CONNECTION_RETRY_NUM)+" tries.")
            node.removeTimeSlot(len(node.timeSlots)-node.myTimeSlot/TimeSlotSize) #remove my parent slot time
            del node.parents[node.parentIndex]
            node.setState(MeshNodeState.idleState)
        else:                                                                                               #if no beacon received, QUEUE the event again
            node.parents[node.parentIndex]["connectionCounter"] += 1
            print("Connection counter increased to "+str(node.parents[node.parentIndex]["connectionCounter"])+"!")

            node.parents[node.parentIndex]["timeSlot"] += MeshEpochPeriodInMS
            node.HWclockSynchronisedWithParent = np.uint32(node.HWclockSynchronisedWithParent + MeshEpochPeriodInMS)
            node.GPSTime = node.parents[node.parentIndex]["timeSlot"]+TransmissionDelay
            node.meshTimers.node_beacon_time = node.parents[node.parentIndex]["timeSlot"] + node.myTimeSlot #my time is parent's time + the time slot number [miliseconds]
            
            node.meshTimers.pushEvent(MeshNodeEvents.PARENT_BEACON, 0, node.parentIndex)
            node.meshTimers.pushEvent(MeshNodeEvents.TRANSMITTING_BEACON, 0, 'None')
            for childIndex in range(len(node.children)):                                     #children beacons
                node.meshTimers.pushEvent(MeshNodeEvents.CHILD_BEACON, 0, childIndex) 
            node.setState(MeshNodeState.connectedIdle)

    elif event == MeshNodeEvents.IRQ_RX_DONE:
        packet = IrqRxDoneEventDataType(**eventData)
        print("Packet SNR: " + str(packet.SNR))
        print("Packet RSSI: " + str(packet.RSSI))
        if parse_Packet(node, packet.payload) != True:
            print("Wrong packet!")
            node.setState(MeshNodeState.connectedIdle)
            return

        if node.Packet_DevAddr  == node.parents[node.parentIndex]["DeviceAddress"]:     #if the node is the parent in question
            print("Parent "+str(node.Packet_DevAddr)+" node beacon received!")

            """Fix my GPS time and parent's time slot"""
            node.timestamp = node.getTimestamp(node)
            print("GPS Time corrected by "+str(node.GPSTime-(node.Packet_timestamp+TransmissionDelay))+"ms")
            node.parents[node.parentIndex]["timeSlot"] = node.Packet_timestamp
            node.HWclockSynchronisedWithParent = node.synchronizeHWClock()  #get the HW clock at this time - this is a HW clock equivalent to the GPS time - whenever the HW clock changes, the GPS time changes by the same amount
            node.GPSTime = node.parents[node.parentIndex]["timeSlot"]+TransmissionDelay
            node.meshTimers.node_beacon_time = node.parents[node.parentIndex]["timeSlot"] + node.myTimeSlot #my time is parent's time + the time slot number [miliseconds]

            for i in range(len(node.Packet_Data_Frames)):
                if node.Packet_Data_Frames[i].MMType == "OTAARegAck":                   #if one of our parents is carrying a confirmation for a new node - register the confirmation
                    for j in range(len(node.children)):
                        for k in range(len(node.children[j]["AccessNodes"])):           #check through which child this node can be acessed
                            if node.children[i]["AccessNodes"][k] == node.Packet_Data_Frames[i].DeviceEUI:
                                node.children[i]["AccessNodes"][k] = node.Packet_Data_Frames[i].ChildAddress #change the deviceEUI to the assigned node address
                                print(node.children)
            node.meshTimers.pushEvent(MeshNodeEvents.PARENT_BEACON, 0, node.parentIndex)
            node.meshTimers.pushEvent(MeshNodeEvents.TRANSMITTING_BEACON, 0, 'None')
            for childIndex in range(len(node.children)):                                     #children beacons
                node.meshTimers.pushEvent(MeshNodeEvents.CHILD_BEACON, 0, childIndex)
            node.setState(MeshNodeState.connectedIdle)

        else:
            print("Not our parent.")

            node.parents[node.parentIndex]["timeSlot"] += MeshEpochPeriodInMS
            node.HWclockSynchronisedWithParent = np.uint32(node.HWclockSynchronisedWithParent + MeshEpochPeriodInMS)
            node.GPSTime = node.parents[node.parentIndex]["timeSlot"]+TransmissionDelay
            node.meshTimers.node_beacon_time = node.parents[node.parentIndex]["timeSlot"] + node.myTimeSlot #my time is parent's time + the time slot number [miliseconds]
            
            node.meshTimers.pushEvent(MeshNodeEvents.PARENT_BEACON, 0, node.parentIndex)
            node.meshTimers.pushEvent(MeshNodeEvents.TRANSMITTING_BEACON, 0, 'None')
            for childIndex in range(len(node.children)):                                     #children beacons
                node.meshTimers.pushEvent(MeshNodeEvents.CHILD_BEACON, 0, childIndex)
            node.setState(MeshNodeState.connectedIdle)
    return
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

meshNodeStateHandlers = {
    MeshNodeState.idleState: meshIdleState,
    MeshNodeState.searchParent: meshSearchParent,
    MeshNodeState.transmittingOTAARegReq: meshTransmittingOTAARegReq,
    MeshNodeState.waitForPotentialParentWindow: meshWaitForPotentialParentWindow,
    MeshNodeState.waitForRequestConnectionAnswer: meshWaitForRequestConnectionAnswer,

    MeshNodeState.connectedIdle: meshConnectedIdle,
    MeshNodeState.transmittingBeacon: meshTransmittingBeacon,
    MeshNodeState.transmittingCRWBeacon: meshTransmittingCRWBeacon,
    MeshNodeState.receivingNewChildNodes: meshReceivingNewChildNodes,
    MeshNodeState.waitForChildBeacon: meshWaitForChildBeacon,
    MeshNodeState.waitForParentBeacon: meshWaitForParentBeacon,
}


"""""""""""""""""""""""""""""""""""""""""""""""""""""""""node class"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""
class MeshNodeContext(object):
    def __init__(self, name, node_address, deviceEUI, interface, timestampFunct, PPM, pForwarder, initialState=MeshNodeState.idleState, children=[], parents=[]):
        self.name = name
        self.state = initialState
        self.node_address = node_address
        self.deviceEUI = deviceEUI
        self.eQueue = eventQueue(self)
        self.HWQueue = HWQueue(self)
        self.dQueue = dataQueue()
        self.interface = interface
        self.children = children
        self.parents = parents
        self.timestamp = 0
        self.NetworkDepth = 0
        self.beaconTimeEstimate = 0
        self.rng = random.SystemRandom()    #random number generator
        self.meshTimers = mesh_Timers(self)
        self.packetForwarder = pForwarder

        """Timestamps related (GPS time interface):"""
        self.GPSTime = 0
        self.GetGPSTimeMSPrev = meshGetGPSTimeMS(self)
        self.getTimestamp = timestampFunct
        self.PPM = PPM

        """Timestamps related (HW crystal interface):"""
        self.eventReady = 0 #eventReady increases by 1 when we receive the Event Timestamp Timeout confirmation from the HW radio node.
        self.HWclockSync = False;
        self.HWclock = 0
        self.HWclockSynchronisedWithParent = 0

        """Time Slotting"""
        self.myTimeSlot = 0                                             #my time slot relative to my parent [in miliseconds] - sent by the parent on RegReq
        self.timeSlots = [False]*int(MeshEpochPeriodInMS/TimeSlotSize)  #time slots for 1 epoch
        self.timeSlotsTaken = 0                                         #number of currently taken time slots

        self.childAddressesCounter = 1                                  #children address counter

        self.potentialParents = []
        self.potentialChildren = []

        """children already added but to be still confirmed (first packet from the child received)"""
        self.childrenToBeConfirmed = []

        self.currentFrequency = 0
        self.currentSF = 0
        self.beaconingFrequencyIndex = 0
        self.beaconingSFIndex = 0

        """indexes to Access the self.children and self.parents in lists"""
        self.potentialParentIndex = 0
        self.potentialChildIndex = 0
        self.childIndex = 0
        self.parentIndex = 0

        """beacon type counter variable"""
        self.BeaconCounter = 0
        self.CRWCounter = 1

        """received packet data"""
        self.Packet_MHDR = 0
        self.Packet_DevAddr = 0
        self.Packet_timestamp = 0
        self.Packet_Phase = 0
        self.Packet_Beacon_Frames = []
        self.Packet_Data_Frames = []

        """LoRa end device activation related (OTAA - node side)"""
        self.DevNonce = 0               #random variable used in Join procedure - call from function getDevNonce()
        self.JoinNonce = 0
        self.NetID = 0
        self.AppKey = "e2c982801d7198d7772dab3b6917db83"
        self.JoinEUI = int("aabbccddeeff3333", 16)
        self.NwkSkey = 0x00
        self.AppSkey = 0x00
        """LoRa end device messaging related (node side)"""
        self.FcntUP = -1
        self.FcntDOWN = -1

    def processState(self, event: MeshNodeEvents, eventData={}):
        """
        processState(): Process the current state with a chosen event and eventData.
        """
        handler = meshNodeStateHandlers.get(self.state, None)
        if handler == None:
            print("Unknown state -> switch to searchParent")
            handler = meshNodeStateHandlers.get(MeshNodeState.connectedIdle)
        handler(self, event, eventData)

    def setState(self, newState):
        """
        setState(): Set a new state.
        """
        if self.state != newState:
            print("##########################################################################################")
            print(f"{self.name} changed state from {self.state} to {newState}")
        self.state = newState


    def findParent(self, nodeAddress):
        """
        findParent(): returns a list index of a chosen parent.
        """
        for parentIndex in range(len(self.parents)):
            if self.parents[parentIndex]["DeviceAddress"] == nodeAddress:
                return parentIndex
        return 'None'

    def findPotentialParent(self, nodeAddress):
        """
        findPotentialParent(): returns a list index of a chosen potentialParent.
        """
        for potentialParentIndex in range(len(self.potentialParents)):
            if self.potentialParents[potentialParentIndex]["DeviceAddress"] == nodeAddress:
                return potentialParentIndex
        return 'None'

    def findChild(self, nodeAddress):
        """
        findChild(): returns a list index of a chosen child.
        """
        for childIndex in range(len(self.children)):
            if self.children[childIndex]["DeviceAddress"] == nodeAddress:
                return childIndex
        return 'None'

    def findPotentialChild(self, nodeAddress):
        """
        findPotentialChild(): returns a list index of a chosen potentialChild.
        """
        for potentialChildIndex in range(len(self.potentialChildren)):
            if self.potentialChildren[potentialChildIndex]["DeviceEUI"] == nodeAddress:
                return potentialChildIndex
        return 'None'

    def getBeaconingFrequency(self):
        """
        getBeaconingFrequency(): set a next beaconing frequency index
        """
        self.currentFrequency = MeshBeaconingFrequencies[self.beaconingFrequencyIndex]
        self.beaconingFrequencyIndex += 1
        if self.beaconingFrequencyIndex >= len(MeshBeaconingFrequencies):
            self.beaconingFrequencyIndex = 0
        return

    def getBeaconingSF(self):
        """
        getBeaconingSF(): set a next beaconing SF index
        """
        self.currentSF = MeshBeaconingSF[self.beaconingSFIndex]
        self.beaconingSFIndex += 1
        if self.beaconingSFIndex >= len(MeshBeaconingSF):
            self.beaconingSFIndex = 0
        return

    def isCRWTime(self):
        """
        isCRWTime(): is it time for the CRW beacon? (crw beacon every 3rd sync beacon if there is space for a new node)
        """
        if self.timeSlotsTaken >= int(MeshEpochPeriodInMS/TimeSlotSize): #all the time slots taken
            retval = False
        elif self.BeaconCounter % 3 == 0:
            retval = True
        else:
            retval = False
        self.BeaconCounter+=1
        return retval

    def setTimeSlot(self):
        """
        setTimeSlot(): returns next free timeSlot for a new child
        """
        for i in range(len(self.timeSlots)):
            if self.timeSlots[i] == False:
                self.timeSlots[i] = True
                print(self.timeSlots)
                self.timeSlotsTaken=self.timeSlotsTaken+1
                return i*TimeSlotSize                                   #return time slot (in miliseconds from 0)
        print("All time slots on this node taken!")

    def removeTimeSlot(self, timeSlotNumber):
        self.timeSlots[int(timeSlotNumber)] = False #remove my parent slot time
        self.timeSlotsTaken=self.timeSlotsTaken-1
        return

    def getDevNonce(self):
        """
        getDevNonce(): increases DevNonce by 1 and returns it (used in Join procedure)
        """
        self.DevNonce += 1
        return self.DevNonce

    def getEndNodeFcntUP(self):
        """
        getEndNodeFCnt(): increases FcntUP by 1 and returns it
        """
        self.FcntUP += 1
        return self.FcntUP
    
    def getEndNodeFcntDOWN(self):
        """
        getEndNodeFCnt(): increases FcntUP by 1 and returns it
        """
        self.FcntDOWN += 1
        return self.FcntDOWN

    def startReception(self, frequency, SF, RX_timeout):
        """
        startReception(): start the radio reception
        """
        print(f"Reception started @ {frequency}Hz, SF:{SF}")
        RX_CONFIG(self.interface, 868100000, SF, RX_timeout)            #(timeout is passed as miliseconds to the radio)

    def startTransmission(self, frequency, SF, TX_message):
        """
        startTransmission(): start the transmission of a packet
        """
        TX_message = ":".join(["%02X" % x for x in TX_message])         #deconstruct the payload to correct format for the simulator
        sleep(TransmissionDelay/1000)                                   #each transmission is sent in the middle of a reception window of other nodes [ms]
        print(f"Transmission started @ {frequency}Hz, SF:{SF}")
        TX_CONFIG(self, self.interface, 868100000, SF, TX_message)

    def sendEventTimestamp(self, command, eventTimestamp):
        """
        sendEventTimestamp(): send the radio event timestamp for RTC clock
        """
        if command == PUSH_EVENT:
            print(f"Sending Event Timestamp: "+str(eventTimestamp))
            EVENT_TS(self.interface, eventTimestamp)
        elif command == GET_TIME:
            print(f"Sending Timestamp Request.")
            TS_REQ(self.interface)

    def synchronizeHWClock(self):
        if((Timestamp_interface == 1 and self.node_address != HARDCODED_PARENT_ADDR)):
            self.meshTimers.HWtimers.sendHWCommand(GET_TIME, 0)
            self.HWclockSync = False
            while(self.HWclockSync != True):
                checkRadioInterface(self.interface, self)         #check radio interface for new messages
            return self.HWclock
