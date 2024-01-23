from mesh_definitions import *
from mesh_clockEvents import *


"""
eventQueue: Has two event queues:\n
eQueue -> used when timestampInterface == 0 by all nodes + hardcoded parent (real GPS time used)
rQueue -> used when timestampInterface == 1 by all nodes - hardcoded parent (node crystal clock used for time calculation)
"""
class eventQueue():
    def __init__(self, node):
        self.eQueue = []        #event queue
        self.node = node

    def storeQueue(self, event:MeshNodeEvents, waitTime={}, eventData={}):
        return (event, waitTime, eventData)

    def pushQueue(self, event:MeshNodeEvents, waitTime={}, eventData={}):
        queueItem = self.storeQueue(event, waitTime, eventData)
        if len(self.eQueue)==0:
            self.eQueue.append(queueItem)
        else:
            for i in range(len(self.eQueue)):
                if queueItem[1]<self.eQueue[i][1]:
                    self.eQueue.insert(i, queueItem)
                    return
            self.eQueue.insert(len(self.eQueue), queueItem)

    def popQueue(self):
        self.eQueue.pop(0)
        return

    def consumeQueue(self):
        if len(self.eQueue) == 0:
            return 0
        if self.node.getTimestamp(self.node) >= self.eQueue[0][1]:
            queueEvent = (self.eQueue[0][0], self.eQueue[0][2])
            self.popQueue()
            return queueEvent
        else:
            return 0


class HWQueue():
    def __init__(self, node):
        self.rQueue = []        #radio events queue
        self.eQueue = []
        self.node = node

        """""""""""""""""""""""""""""timestamp events queue"""""""""""""""""""""""""""""
    def storeQueue(self, event:MeshNodeEvents, waitTime={}, eventData={}):
        return (event, waitTime, eventData)

    def pushQueue(self, event:MeshNodeEvents, waitTime={}, eventData={}):
        queueItem = self.storeQueue(event, waitTime, eventData)
        if len(self.eQueue)==0:
            self.eQueue.append(queueItem)
        else:
            for i in range(len(self.eQueue)):
                if queueItem[1]<self.eQueue[i][1]:
                    self.eQueue.insert(i, queueItem)
                    return
            self.eQueue.insert(len(self.eQueue), queueItem)
    
    def popQueue(self):
        self.eQueue.pop(0)
        return
    
    def consumeQueue(self):
        if len(self.eQueue) == 0:
            return 0
        else:
            queueEvent = (self.eQueue[0][0], self.eQueue[0][2])
            self.popQueue()
            return queueEvent
    

        """""""""""""""""""""""""""""radio events queue"""""""""""""""""""""""""""""
    def popRadioQueue(self):
        self.rQueue.pop(0)
        return
    
    def storeRadioQueue(self, event:MeshNodeEvents, eventData={}):
        return (event, eventData)
    
    def readRadioQueue(self):
        if len(self.rQueue) == 0:
            return 0
        else:
            queueEvent = (self.rQueue[0][0], self.rQueue[0][1])
            self.popRadioQueue()
            return queueEvent
        
    def pushRadioQueue(self, event:MeshNodeEvents, eventData={}):
        queueItem = self.storeRadioQueue(event, eventData)
        self.rQueue.append(queueItem)


"""
dataQueue: each node has dataQueues for each of its neighbouring nodes. The data intended for this node is put in the queue on packet parsing.\n
The data is taken out of the Queue on packet building.
"""
class dataQueue():
    def __init__(self):
        self.listBuffer = []

    def writeData(self, Frame):
        self.listBuffer.append(Frame)

    def readFrame(self):
        Frame = self.listBuffer[0]
        self.listBuffer.pop(0)
        return Frame

    def returnSize(self):
        return len(self.listBuffer)
