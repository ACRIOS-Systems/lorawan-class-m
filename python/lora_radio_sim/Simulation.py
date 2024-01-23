import modules # DO NOT REMOVE! It links the lora_sim_lib
from lora_sim_lib.Time import Time
from lora_sim_lib.MeshVisAPI import MeshVisAPI
from lora_sim_lib.JSONlogger import JSONlogger
import Settings
from AirInterface import AirInterface
from NetObjectLoader import NetObjectLoader
import os
import queue
import signal
import time
import argparse
from termcolor import colored
from engineering_notation import EngNumber
import threading
import multiprocessing as mp
import shutil
from sys import platform




# Safe Chirpstack API import
try:
    from ns_chirpstack3_api.sqlCleanup import sqlCleanup,redisCleanup
    import ns_chirpstack3_api.nsConnector as nsConn
except Exception as e:
    print(colored("Warning: ns_chirpstack3_api could not be imported, disabling Chirpstack functions!", "yellow")) # It is disabled in the "if __name__ == "__main__":" block
    print(colored((e), "yellow"))



class Simulation:

    deltas = []

    def __init__(self) -> None:

        if Settings.CHIRPSTACK:
            # Initialize NS connection and preconfigure Chirpstack
            nsConn.MESHOrganizationName = "organization_simulator"
            nsConn.MESHDeviceProfileName = "deviceProfile_simulator"
            nsConn.MESHApplicationName = "application_simulator"
            nsConn.MESHServiceProfileName = "serviceProfile_simulator"
            nsConn.MESHNetworkServerName = "networkServer_simulator"
            nsConn.MESHGatewayProfileName = "gatewayProfile_simulator"
            nsConn.networkServerInitialize("127.0.0.1", "127.0.0.1", "astest")

            # Cleanup NS and nonces in its database
            nsConn.networkServerPurge()
            time.sleep(1) # Program hangs without this
            sqlCleanup()
            redisCleanup()

        # If MeshVis is used do a cleanup
        if Settings.MESHVIS_EN:
            MeshVisAPI.instance.purge_packets()
            MeshVisAPI.instance.purge_devices()

        # Init simulation variables
        self.time = Time()
        self.air = AirInterface(self.time)

        # Load gateways and nodes
        self.staticNodes = NetObjectLoader(self.time, self.air).loadCSV(Settings.CSV_PATH)
        self.air.addNetObjects(self.staticNodes)

        if Settings.CHIRPSTACK:
            nsConn.ns.client.disconnect() # Disconnect from NS


    def __del__(self) -> None:
        self.isRunning = False
        for node in self.staticNodes:
            node.__del__()

    def run(self):
        #if Settings.REALTIME:
        #    import ctypes # Needed for usleep
        #    libc = ctypes.CDLL('libc.so.6')

        initialNanos = None
        lastStepNanos = None

        while self.time.sec < Settings.RUN_TIME:
            # process all static nodes
            all_idle = True
            for node in self.staticNodes:
                all_idle &= node.step()

            # if all nodes are idle process packets and make a time step
            if all_idle:
                self.air.processPackets()
                self.time.increment()

                # First step timestamp
                if lastStepNanos==None:
                    initialNanos = time.perf_counter_ns()
                    lastStepNanos = time.perf_counter_ns()

                if Settings.REALTIME:
                    while lastStepNanos + int(1e6) >= time.perf_counter_ns(): # wait for 1ms to pass
                        #libc.usleep(10)
                        #time.sleep(0)
                        pass

                    lastStepNanos += int(1e6) # increment by 1ms

                    delta = ((time.perf_counter_ns()-initialNanos)*1e-9)-self.time.sec
                    Simulation.deltas.append(delta)
                    delta = EngNumber(delta)
                if self.time.ms%1000==0:
                    print(f"Time: {int(self.time.sec)}s (delta: {delta}s)")



if __name__ == "__main__":
    # Check if we run on Linux
    if not platform in ["linux", "linux2"]:
        print("ERROR: The LoRa Radio Sim can only be run on Linux!") # type: ignore <- prevents undefined warning
        os._exit(0)


    # Making further print() calls multi-thread and multi-process safe
    printQueue = mp.Queue()
    def printWorker():
        while True:
            data = printQueue.get()
            if data==None:
                break
            __builtins__['oldprint'](*data)
    printThread = threading.Thread(target=printWorker)
    printThread.start()

    def dprint(*args):# https://stackoverflow.com/a/44562634
        printQueue.put(args)

    if 'oldprint' not in __builtins__:
        __builtins__['oldprint'] = __builtins__['print']
    __builtins__['print'] = dprint


    # POSIX Signal handling
    #    termination handled by a thread to prevent multiple runs of the procedure
    #    when any handled signal is put to the terminationQueue, the thread returns from the get() function
    terminationQueue = queue.Queue()
    def terminator():
        sig=terminationQueue.get()
        # Termination procedure
        if sig!=0:
            print(colored(f"Simulation terminated due to external signal sig={sig}", "red"))
        
        JSONlogger.close()
        global sim
        try:
            sim.__del__()
        except:
            pass
        printQueue.put(None)
        printThread.join()
        os.killpg(0, signal.SIGTERM)
        os._exit(0)

    terminatorThread = threading.Thread(target=terminator)
    terminatorThread.start()

    def terminate_handler(sig, frame):
        terminationQueue.put(sig)
        terminatorThread.join()


    # Run all subprocesses in a single process group
    os.setpgrp()
    # register terminate signals so it calls terminate_handler
    signal.signal(signal.SIGINT, terminate_handler)
    #signal.signal(signal.SIGTERM, terminate_handler)   # SIGTERM cannot be registered for terminate handler because this would cause recursive loop of terminate_handler
    signal.signal(signal.SIGHUP, terminate_handler)
    signal.signal(signal.SIGQUIT, terminate_handler)


    # Process arguments...
    parser = argparse.ArgumentParser(description='LoRa Radio Simulator')
    parser.add_argument('--csv', required=True, type=str, metavar='path-to-file', help='Path to the CSV file containing device definitions')
    parser.add_argument('--sim-time', type=int, metavar='seconds', help='Simulation run time in seconds')
    parser.add_argument('--realtime', type=bool, action=argparse.BooleanOptionalAction, help='Slow down the simulation to real time (default)')
    parser.add_argument('--chirpstack', type=bool, action=argparse.BooleanOptionalAction, help='Use the Chirpstack service')
    
    parser.add_argument('--wireshark-rx', type=bool, action=argparse.BooleanOptionalAction, help='Report received packets to Wireshark')
    parser.add_argument('--wireshark-tx', type=bool, action=argparse.BooleanOptionalAction, help='Report transmitted packets to Wireshark')
    parser.add_argument('--wireshark-addr', type=str, metavar='IP-or-domain-name', help='IP address or domain name of the Wireshark endpoint, default: '+Settings.WIRESHARK_ADDR)
    parser.add_argument('--wireshark-port', type=int, metavar='port-number', help='UDP port of the Wireshark endpoint, default: '+str(Settings.WIRESHARK_PORT))

    parser.add_argument('--meshvis', type=bool, action=argparse.BooleanOptionalAction, help='Report packets and devices to MeshVis')
    parser.add_argument('--meshvis-addr', type=str, metavar='IP-or-domain-name', help='IP address or domain name of the MeshVis server, default: '+Settings.MESHVIS_ADDR)
    parser.add_argument('--meshvis-port', type=int, metavar='port-number', help='TCP port of the MeshVis server, default: '+str(Settings.MESHVIS_PORT))
    args = parser.parse_args()

    # ...and override the defaults in Settings.py
    Settings.CSV_PATH = args.csv
    Settings.RUN_TIME = args.sim_time if args.sim_time is not None else Settings.RUN_TIME
    Settings.REALTIME = args.realtime if args.realtime is not None else Settings.REALTIME
    
    Settings.WIRESHARK_RX = args.wireshark_rx if args.wireshark_rx is not None else Settings.WIRESHARK_RX
    Settings.WIRESHARK_TX = args.wireshark_tx if args.wireshark_tx is not None else Settings.WIRESHARK_TX
    Settings.WIRESHARK_ADDR = args.wireshark_addr if args.wireshark_addr is not None else Settings.WIRESHARK_ADDR
    Settings.WIRESHARK_PORT = args.wireshark_port if args.wireshark_port is not None else Settings.WIRESHARK_PORT
    
    Settings.MESHVIS_EN = args.meshvis if args.meshvis is not None else Settings.MESHVIS_EN
    Settings.MESHVIS_ADDR = args.meshvis_addr if args.meshvis_addr is not None else Settings.MESHVIS_ADDR
    Settings.MESHVIS_PORT = args.meshvis_port if args.meshvis_port is not None else Settings.MESHVIS_PORT
    
    if args.chirpstack is not None:
        Settings.CHIRPSTACK = args.chirpstack
    if not "nsConn" in locals():
        Settings.CHIRPSTACK = False


    if Settings.MESHVIS_EN:
        try:
            MeshVisAPI(server_address=Settings.MESHVIS_ADDR, server_port=Settings.MESHVIS_PORT)
        except:
            print(colored("MeshVis unreachable! Disabling...", "yellow"))
            Settings.MESHVIS_EN = False
        

    # move run directory if it exists
    if os.path.exists("run"):
        if os.path.exists("run/datetime.txt"):
            nameDate = open("run/datetime.txt", "r").read()
        else:
            nameDate = "n" + time.strftime("%Y-%m-%d_%H%M%S", time.localtime())

        # move run directory to backup directory
        if not os.path.exists(".run.bckup"):
            os.mkdir(".run.bckup")
        os.rename("run", ".run.bckup/run_" + nameDate)

    # Check if the provided CSV file exists
    if not os.path.exists(Settings.CSV_PATH):
        print(colored("\""+Settings.CSV_PATH+"\" does not exist! Aborting..."))
        os._exit(0)

    # create run directory and write current date to datetime.txt
    os.mkdir("run")
    os.mkdir("run/deviceLogs")
    with open("run/datetime.txt", "w") as f:
        f.write(time.strftime("%Y-%m-%d_%H%M%S", time.localtime()))

    # copy the CSV to the run directory
    shutil.copy2(Settings.CSV_PATH, "run/scenario.csv")

    # initialize JSON event logger
    JSONlogger.init(fileName="eventLog", filePath="./run/")

    #
    # run simulation
    #

    # Try to rise the CPU priority of the simulator if running as root / with sudo
    if (os.getuid()==0):
        oldNiceness = os.nice(0)
        newNiceness = os.nice(-20-oldNiceness) # target niceness = -20
        print(f"Successfully set niceness (CPU priority) from {oldNiceness} to {newNiceness}.")
    else:
        print(colored("Not running as root, cannot set higher CPU priority.", "yellow"))
    

    print("Simulation initializing...")
    global sim
    sim = Simulation()

    time.sleep(1)
    print("Simulation starting...")

    #import cProfile
    #cProfile.run("sim.run()", filename="sim-run.profile")
    sim.run()

    # Save timestep delta values ()
    with open(file="./run/deltas.txt", mode="w") as f:
        for d in Simulation.deltas:
            f.write(str(d)+"\r\n")

    print("Simulation ended.")
    time.sleep(1)
    print("Terminating...")
    terminate_handler(0, 0)
