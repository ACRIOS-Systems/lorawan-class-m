from time import *
from mesh_parsing_building import *
from mesh_data import *

timePassed = time.time()

def applicationData(node):
    """
    applicationData(): schedule the application data every X seconds
    """
    global timePassed
    if node.node_address != HARDCODED_PARENT_ADDR and node.NwkSkey != False:
        if time.time() > timePassed+30:
            timePassed = time.time()
            data = [0xff, 0x96, 0x0c, 0x0a, 0x09, 0x08, 0x07, 0x06, 0x96, 0x04, 0x02, 0x96, 0x09, 0x96, 0x96, 0x96, 0xff, 0x96, 0x0c, 0x0a, 0x09, 0x08, 0x07, 0x06, 0x96, 0x04, 0x02, 0x96, 0x09, 0x96, 0x96, 0x96, 0xff, 0x96, 0x0c, 0x0a, 0x09, 0x08, 0x07, 0x06, 0x96, 0x04, 0x02, 0x96, 0x09, 0x96, 0x96, 0x96]
            data = bytearray(data)
            applicationDataSend(node, data)
        return


dataList = {
    "sender":       0,
    "Fport" :       0,
    "dataLength":   0,
    "data":         0
}

def dataToNS(node):
    dataList["sender"] = 0
    dataList["Fport"] = 0
    dataList["dataLength"] = 0
    dataList["data"] = 0
    node.packetForwarder.PF_DataQueues.NS_input_add(dataList)
    pass

def dataFromNS(node):
    data = node.packetForwarder.PF_DataQueues.NS_input_take()
    dataList["sender"] = 0
    dataList["Fport"] = 0
    dataList["dataLength"] = 0
    dataList["data"] = 0
    pass

def registerNodeToNS(node):
    pass

def getRegistrationResponse(node):
    pass
    
