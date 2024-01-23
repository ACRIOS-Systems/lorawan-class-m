from main import *
import argparse
from threading import Thread
from packetForwarder import NS_packetForwarder

#########################################################################################################
parentObject = {}
parentObject["DeviceAddress"] = NETWORK_SERVER_ADDR
parentObject["Frequency"] = MeshBeaconingFrequencies[0]
parentObject["SF"] = MeshBeaconingSF[0]
parentObject["dataQueue"] = dataQueue()
#########################################################################################################

"""HADCODED PARENT MAIN()"""
def main():
    if arguments.SerialInterface != "None":              #if there is a serial interface specified for the node, open RadioInterface with it
        hardcoded_parent_interface = RadioInterface(arguments.SerialInterface)
    else:
        hardcoded_parent_interface = RadioInterface(None)
    hardcoded_parent = MeshNodeContext("HardCoded Parent", HARDCODED_PARENT_ADDR, arguments.DeviceEUI, hardcoded_parent_interface, meshGetGPSTimeMS, arguments.CrystalPPM,
                                                            pForwarder, initialState=MeshNodeState.idleState, children=[], parents=[parentObject])
    hardcoded_parent.timeSlots[-1] = True                   #add predefined parent (NS)
    assignMyTimeSlots(hardcoded_parent)
    hardcoded_parent.setState(MeshNodeState.idleState)
    hardcoded_parent.processState(MeshNodeEvents.poll)
    while True:
        dataQueueCheck(hardcoded_parent, pForwarder)                        #check my dataQueue for packets
        checkRadioInterface(hardcoded_parent_interface, hardcoded_parent)   #check radio interface for new messages
        eEvent = hardcoded_parent.eQueue.consumeQueue()
        if eEvent == 0:
            hardcoded_parent.processState(MeshNodeEvents.poll)
        else:
            hardcoded_parent.processState(eEvent[0], eEvent[1])
        sleep(0.00001)

if __name__ == "__main__":

    # Process arguments...
    parser = argparse.ArgumentParser(description='LoRa mesh python')
    parser.add_argument('--SerialInterface', type=str, help='ACM interface to the node')
    parser.add_argument('--CrystalPPM', type=str, help='Node crystal PPM simulation.')
    parser.add_argument('-d', '--DeviceEUI', type=lambda x: int(x.replace(":", ""),16), help='Device EUI')

    parser.add_argument('-k', '--AppKey', type=lambda x: int(x.replace(":", ""),16), help='App Key')
    parser.add_argument('-a', '--AppEUI', type=lambda x: int(x.replace(":", ""),16), help='App EUI')
    parser.add_argument('-j', '--JoinDR', type=int, help='Join DR')
    arguments = parser.parse_args()

    pForwarder = NS_packetForwarder.packetForwarder(arguments.DeviceEUI)
    thread = Thread(target = NS_packetForwarder.packetForwarderLoop, args = (pForwarder, ))
    thread.start()

    main()