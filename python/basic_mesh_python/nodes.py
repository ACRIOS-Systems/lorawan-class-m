from main import * 
import argparse

"""NODES MAIN()"""
def main():
    if arguments.SerialInterface != "None":
        child_interface = RadioInterface(arguments.SerialInterface)#if there is a serial interface specified for the node, open RadioInterface with it
    else:
        child_interface = RadioInterface(None)

    child_node = MeshNodeContext("NODE", 0x00, arguments.DeviceEUI, child_interface, nodeCrystalTimestamp, arguments.CrystalPPM, 0, initialState=MeshNodeState.idleState, children=[], parents=[])
    assignMyTimeSlots(child_node)
    child_node.setState(MeshNodeState.idleState)
    while True:
        applicationData(child_node)                              #check for application data
        dataQueueCheck(child_node, 0)                               #check my dataQueue for packets
        checkRadioInterface(child_interface, child_node)         #check radio interface for new messages
        if(Timestamp_interface == 0):                            #if timestamp interface = 0, use normal interface
            eEvent = child_node.eQueue.consumeQueue()
            if eEvent == 0:
                child_node.processState(MeshNodeEvents.poll)
            else:
                child_node.processState(eEvent[0], eEvent[1])
        elif(Timestamp_interface == 1):                          #if timestamp interface = 1, use node hardware crystal interface and HWQueue for timestamp events
            if (child_node.state == MeshNodeState.idleState):
                child_node.processState(MeshNodeEvents.poll)
            rEvent = child_node.HWQueue.readRadioQueue()          #check radioQueue for TX/RX done, and timeout events
            if (rEvent):
                child_node.processState(rEvent[0], rEvent[1])
                rEvent = 0
            while (child_node.eventReady>0):                     #while there are timestamp signals from the node RTC clock
                eEvent = child_node.HWQueue.consumeQueue()       #check event Queue for the rest of the non-radio events
                if eEvent == 0:
                    pass
                else:
                    child_node.processState(eEvent[0], eEvent[1])
                child_node.eventReady -= 1
        sleep(0.00001)


if __name__ == "__main__":

    # Process arguments...
    parser = argparse.ArgumentParser(description='LoRa mesh python')
    parser.add_argument('-s', '--SerialInterface', type=str, help='ACM interface to the node', default="None")
    parser.add_argument('-p', '--CrystalPPM', type=float, help='Node crystal PPM simulation.', default=0)
    parser.add_argument('-d', '--DeviceEUI', type=lambda x: int(x.replace(":", ""),16), help='Device EUI')

    parser.add_argument('-k', '--AppKey', type=lambda x: int(x.replace(":", ""),16), help='App Key')
    parser.add_argument('-a', '--AppEUI', type=lambda x: int(x.replace(":", ""),16), help='App EUI')
    parser.add_argument('-j', '--JoinDR', type=int, help='Join DR')
    arguments = parser.parse_args()

    main()