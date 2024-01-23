from NodeInterface import *
from mesh_definitions import *

"""HW commands"""
GET_TIME = 0x01
PUSH_EVENT = 0x02

class mesh_Timers(object):
    def __init__(self, node):
        self.node = node
        self.HWtimers = HW_Timers(node)
        self.SWtimers = SW_Timers(node)
        self.node_beacon_time = 0      #calcualte the time of this node beacon (current time)  

    def setPParentTime(self, node, index):
        """
        setPParentTime(): returns the time slot of a potentialParent in real time - based on the potentialParent timeSlot index
        """
        node.potentialParents[index]["timeSlot"]+=MeshEpochPeriodInMS
        return node.potentialParents[index]["timeSlot"]

    def setParentTime(self, node, index):
        """
        setParentTime(): returns the time slot of a parent in real time - based on the parent timeSlot index
        """
        node.parents[index]["timeSlot"]+=MeshEpochPeriodInMS
        return node.parents[index]["timeSlot"]

    def setChildTime(self, node, index):
        """
        setChildTime(): returns the time slot of a child in real time - based on the child timeSlot index
        """
        return node.children[index]["timeSlot"] + self.node_beacon_time #return child time in upcoming epoch
        
    def setMyTime(self):
        """
        setMyTime(): returns this node time slot in real time
        """
        self.node_beacon_time+=MeshEpochPeriodInMS                  #update it
        return self.node_beacon_time                                #return the time slot
    
    
    def pushEvent(self, event, waitTime, nodeIndex):
        if Timestamp_interface == 0 or self.node.node_address == HARDCODED_PARENT_ADDR:
            if event == MeshNodeEvents.TRANSMITTING_BEACON:
                if self.node_beacon_time <= self.node.getTimestamp(self.node):
                    self.setMyTime()
                self.SWtimers.pushEvent(event, self.node_beacon_time, nodeIndex)
            elif event == MeshNodeEvents.potentialParent_BEACON:
                self.SWtimers.pushEvent(event, self.setPParentTime(self.node, nodeIndex), self.node.potentialParents[nodeIndex]["DeviceAddress"])
            elif event == MeshNodeEvents.PARENT_BEACON:
                self.SWtimers.pushEvent(event, self.setParentTime(self.node, nodeIndex), self.node.parents[nodeIndex]["DeviceAddress"])
            elif event == MeshNodeEvents.TIME_SLOT_EXPIRED:
                self.SWtimers.pushEvent(event, self.node.getTimestamp(self.node)+waitTime, nodeIndex)
            elif event == MeshNodeEvents.CHILD_BEACON:
                self.SWtimers.pushEvent(event, self.setChildTime(self.node, nodeIndex), self.node.children[nodeIndex]["DeviceAddress"])

        else:
            if event == MeshNodeEvents.TRANSMITTING_BEACON:
                waitTime = self.node.HWclockSynchronisedWithParent + (self.node_beacon_time - self.node.GPSTime)
                self.HWtimers.sendHWCommand(PUSH_EVENT, waitTime)
                self.HWtimers.pushEvent(event, self.node_beacon_time, nodeIndex)
            elif event == MeshNodeEvents.potentialParent_BEACON:
                nextPParentTime = self.setPParentTime(self.node, nodeIndex)
                waitTime = self.node.HWclockSynchronisedWithParent + (nextPParentTime - self.node.GPSTime)
                self.HWtimers.sendHWCommand(PUSH_EVENT, waitTime)
                self.HWtimers.pushEvent(event, nextPParentTime, self.node.potentialParents[nodeIndex]["DeviceAddress"])
            elif event == MeshNodeEvents.PARENT_BEACON:
                nextParentTime = self.setParentTime(self.node, nodeIndex)
                waitTime = self.node.HWclockSynchronisedWithParent + (nextParentTime - self.node.GPSTime)
                self.HWtimers.sendHWCommand(PUSH_EVENT, waitTime)
                self.HWtimers.pushEvent(event, nextParentTime, self.node.parents[nodeIndex]["DeviceAddress"])
            elif event == MeshNodeEvents.TIME_SLOT_EXPIRED:
                HWwaitTime = self.node.HWclockSynchronisedWithParent - TransmissionDelay + self.node.myTimeSlot + waitTime
                SWwaitTime = self.node.GPSTime - TransmissionDelay + self.node.myTimeSlot + waitTime
                self.HWtimers.sendHWCommand(PUSH_EVENT, HWwaitTime)
                self.HWtimers.pushEvent(event, SWwaitTime, nodeIndex)
            elif event == MeshNodeEvents.CHILD_BEACON:
                nextChildTime = self.setChildTime(self.node, nodeIndex)
                waitTime = self.node.HWclockSynchronisedWithParent + (nextChildTime - self.node.GPSTime)
                self.HWtimers.sendHWCommand(PUSH_EVENT, waitTime)
                self.HWtimers.pushEvent(event, nextChildTime, self.node.children[nodeIndex]["DeviceAddress"])

class HW_Timers(object):
    def __init__(self, node):
        self.node = node

    def sendHWCommand(self, command, milisecondsUntilEvent):
        """
        sendHWCommand(): send the radio event timestamp for RTC clock
        """ 
        self.node.sendEventTimestamp(command, milisecondsUntilEvent)
    
    def pushEvent(self, event, waitTime, eventData):
        self.node.HWQueue.pushQueue(event, waitTime, eventData)


class SW_Timers(object):
    def __init__(self, node):
        self.node = node

    def pushEvent(self, event, waitTime, eventData):
        self.node.eQueue.pushQueue(event, waitTime, eventData)



""""""""""""""""""""""""""""""""""""""""""""""""""""""""""Timestamps + GPS time"""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

### NODE CRYSTAL TIMESTAMP ##########################################
def nodeCrystalTimestamp(node):
    if (Timestamp_interface == 0):
        GetGPSTimeMSNow = meshGetGPSTimeMS(node)
        ticksMS = GetGPSTimeMSNow-node.GetGPSTimeMSPrev
        node.GetGPSTimeMSPrev = GetGPSTimeMSNow

        ticksMS = ticksMS*(1+(node.PPM/1000000))
        node.GPSTime = node.GPSTime + ticksMS
        return int(node.GPSTime)
    elif (Timestamp_interface == 1):
        return 0

## CURRENT GPS TIME ###################################################
def meshGetGPSTimeMS(node): #miliseconds
    t = Time(str(datetime.utcnow()), format='iso', scale='utc')
    GPS_time = str(t.gps)
    GPS_time = GPS_time.replace('.', '')
    return int(GPS_time[0:13])

## TIMESTAMP CHECK ###################################################
def meshHasElapsed(node, start, elapsed):
    nowts = node.getTimestamp(node)
    if (nowts - start) > elapsed:
        return True
    else:
        return False