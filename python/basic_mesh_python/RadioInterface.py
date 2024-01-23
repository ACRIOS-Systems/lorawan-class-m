import multiprocessing as mp
import sys
import io
from serial import Serial
from WiresharkStreamerHW import *

from time import sleep
import time

class RadioInterface():

    def __processRx(self, q: mp.Queue, inp:io.TextIOWrapper) -> None:
        if inp.name == "<stdin>": # if the stdin is being used
            inp = open(0)
        else: # if a serial is being used
            inp.set_low_latency_mode(True)
            
        while not self.stopProcesses.is_set():
            try:
                cmd = inp.readline() #readline() is a blocking function!
                if type(cmd) is bytes: # When using serial, bytes are used instead of str
                    cmd = cmd.decode("ascii")

                #print("[RX] "+cmd.strip())
                q.put(cmd.strip())
            except:
                print("[RadioInterface] Exception while readline() in __processRx()!")
                continue
            sleep(0.000001)

        print("Exitting __processRx().")

    def __processTx(self, q: mp.Queue, out:io.TextIOWrapper) -> None:
        while not self.stopProcesses.is_set():
            try:
                cmd = q.get_nowait()
            except:
                sleep(0.000001)
                continue
            cmd = cmd+"\n"

            #print("[TX] "+cmd.strip())
            if out.name == "<stderr>":
                out.write(cmd)
            else:
                out.write(cmd.encode("ascii")) # When using serial, bytes are used instead of str
            out.flush()

        out.close()
        print("Exitting __processTx().")

    
    ## Constructor
    # port: string containing serial port name, if "None" then stdio is used for simulator
    def __init__(self, port: str) -> None:
        
        # Use the stdio
        if port is None:
            self.queueRx = mp.Queue()
            self.queueTx = mp.Queue()
            self.stopProcesses = mp.Event()
            self.procRx = mp.Process(target = self.__processRx, args = (self.queueRx, sys.stdin))
            self.procTx = mp.Process(target = self.__processTx, args = (self.queueTx, sys.stderr))
            self.procRx.daemon = True
            self.procTx.daemon = True
            self.procRx.start()
            self.procTx.start()

        # Use specified serial port
        else:
            self.serial = Serial(port, 921600)
            self.queueRx = mp.Queue()
            self.queueTx = mp.Queue()
            self.stopProcesses = mp.Event()
            self.procRx = mp.Process(target = self.__processRx, args = (self.queueRx, self.serial))
            self.procTx = mp.Process(target = self.__processTx, args = (self.queueTx, self.serial))
            self.procRx.daemon = True
            self.procTx.daemon = True
            self.procRx.start()
            self.procTx.start()


    ## Destructor
    def __del__(self):
        self.stopProcesses.set()


    ## Sends a command to the radio
    def sendCommand(self, cmd: str) -> bool:
        try:
            self.queueTx.put_nowait(cmd)
        except:
            return False
        return True


    ## Tries to read a command from radio,
    #  if no command was received then None object is returned
    def readCommand(self) -> str:
        try:
            cmd = self.queueRx.get_nowait()
            return cmd
        except:
            return None

"""
### TEST #######################################################################
if __name__ == '__main__':

    from datetime import datetime, timedelta

    lastTime = datetime.now()
    interface = RadioInterface(None) # Virtual radio in simulator
    #interface = RadioInterface("/dev/ttyUSB0") # Physical radio over serial

    # Example for the simulator
    while True:
        if interface.readCommand() == ":":
            interface.sendCommand(".")
        	
        if datetime.now() >= lastTime+timedelta(seconds=3):     
            lastTime = datetime.now()
            interface.sendCommand(":TX,ts=0,frequency=868100000,preamble_length=8,implicit_header=0,payload_length=23,crc_en=1,iq_inverted=0,spreading_factor=10,bandwidth_kHz=125,coding_rate=5,low_data_rate=0,power=13,ramp_time=40,tx_timeout=0,symbol_timeout=0,size=23,data=00:00:00:F0:E0:D0:C0:B0:A0:02:00:FF:EE:DD:CC:BB:AA:01:00:AB:35:FE:D1:")
            
"""