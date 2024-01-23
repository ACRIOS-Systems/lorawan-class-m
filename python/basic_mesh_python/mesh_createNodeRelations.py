from Queues import *

def createPotentialParent(deviceAddress, Frequency, SpreadingFactor, timeSlot, networkDepth, RSSI, freeSlots):
    """
    createPotentialParent(): create a potential parent dict with all the parameters of the selected node\n
    deviceAddress: address of the node
    Frequency: frequency the node is operating on
    SpreadingFactor: SF the node is operating on
    timeSlot: assign the time slot this node is operating in
    networkDepth: how deep in the network is this node
    RSSI: signal strength to this node
    freeSlots: number of free time slots to connect to on this node
    """
    potentialParentObject = {}
    potentialParentObject["DeviceAddress"] = deviceAddress
    potentialParentObject["Frequency"] = Frequency
    potentialParentObject["SF"] = SpreadingFactor
    potentialParentObject["timeSlot"] = timeSlot
    potentialParentObject["connectionCounter"] = 0
    potentialParentObject["dataQueue"] = dataQueue()
    potentialParentObject["NetworkDepth"] = networkDepth
    potentialParentObject["RSSI"] = RSSI
    potentialParentObject["FreeSlots"] = freeSlots
    return potentialParentObject


def createParent(deviceAddress, Frequency, SpreadingFactor, timeSlot):
    """
    createParent(): create a parent dict with all the parameters of the selected node\n
    deviceAddress: address of the node
    Frequency: frequency the node is operating on
    SpreadingFactor: SF the node is operating on
    timeSlot: assign the time slot this node is operating in
    """
    parentObject = {}
    parentObject["DeviceAddress"] = deviceAddress
    parentObject["Frequency"] = Frequency
    parentObject["SF"] = SpreadingFactor
    parentObject["timeSlot"] = timeSlot
    parentObject["connectionCounter"] = 0
    parentObject["dataQueue"] = dataQueue()
    parentObject["AccessNodes"] = []
    return parentObject

def createPotentialChild(DeviceEUI, Frequency, SpreadingFactor):
    """
    createPotentialChild(): create a potential child dict with all the parameters of the selected node\n
    deviceEUI: EUI address of the node
    Frequency: frequency the node is operating on
    SpreadingFactor: SF the node is operating on
    """
    potentialChildObject = {}
    potentialChildObject["DeviceEUI"] = DeviceEUI
    potentialChildObject["Frequency"] = Frequency
    potentialChildObject["SF"] = SpreadingFactor
    potentialChildObject["timeSlot"] = 'Null'
    potentialChildObject["connectionCounter"] = 0
    potentialChildObject["dataQueue"] = dataQueue()
    return potentialChildObject

def createChild(deviceAddress, Frequency, SpreadingFactor, timeSlot):
    """
    createChild(): create a child dict with all the parameters of the selected node\n
    deviceAddress: address of the node
    Frequency: frequency the node is operating on
    SpreadingFactor: SF the node is operating on
    timeSlot: assign the time slot this node is operating in
    """
    childObject = {}
    childObject["DeviceAddress"] = deviceAddress
    childObject["Frequency"] = Frequency
    childObject["SF"] = SpreadingFactor
    childObject["timeSlot"] = timeSlot
    childObject["connectionCounter"] = 0
    childObject["dataQueue"] = dataQueue()
    childObject["AccessNodes"] = []
    return childObject