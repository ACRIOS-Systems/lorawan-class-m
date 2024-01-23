import subprocess
from lora_sim_lib.Time import Time
from lora_sim_lib.JSONlogger import JSONlogger
from Packet import Packet
import threading
import time
import collections
import re # Regular expression
from termcolor import colored
import Settings

if Settings.MESHVIS_EN:
    from lora_sim_lib.MeshVisAPI import MeshVisAPI


def gatewayStackStdinProcess(id, stdin, queue, self):
    #with open(f"run/deviceLogs/{id}gw.stdin", "a") as f: # resource hungry!
        with open(f"run/deviceLogs/{id}gw.hstdin", "a") as fh:
            while True:
                try:
                    cmd = queue.popleft()
                except IndexError:
                    time.sleep(0)
                    continue
                
                if cmd == None:
                    break # None in queue - thread ended

                try:
                    stdin.write(f":{cmd}\n")
                except BrokenPipeError:
                    self.isRunning = False
                    print(colored(f"{self} has a broken stdin pipe!", "red"))
                    break
                    
                # write command to a file
                #f.write(f":{cmd}\n") # resource hungry!
                #f.flush()

                # write human-readable stdin file
                if cmd != "":
                    fh.write(f":{cmd}\n")
                    fh.flush()


def gatewayStackStdoutProcess(id, stdout, queue):
    with open(f"run/deviceLogs/{id}gw.stdout", "a") as f:
        while True:
            line = stdout.readline()
            if not line:
                break           # end of file - thread ended

            # strip blank characters from the start and end of the line
            line = line.strip()

            # write line to a file
            f.write(line)
            f.write("\n")
            f.flush()

    print(colored(f"GatewayStack[{id}]: stdout Thread Ends", "red"))


def gatewayStackStderrProcess(id, stderr, queue):
    with open(f"run/deviceLogs/{id}gw.stderr", "a") as f:
        with open(f"run/deviceLogs/{id}gw.hstderr", "a") as fh:
            while True:
                line = stderr.readline()
                if not line:
                    break           # end of file - thread ended

                # strip blank characters from the start and end of the line
                line = line.strip()

                if len(line) > 0:
                    if line.startswith(":") or line.startswith("."):
                        queue.appendleft(line)

                # write line to a file
                f.write(line)
                f.write("\n")
                f.flush()

                # write human-readable stderr file
                if line.startswith(":"):
                    fh.write(line)
                    fh.write("\n")
                    fh.flush()

    print(colored(f"GatewayStack[{id}]: stderr Thread Ends", "red"))


class GatewayStack:

    def __str__(self) -> str:
        return self.gateway.__str__()


    def __init__(self, gateway, exec) -> None:
        self.id = gateway.id
        self.gateway = gateway
        self.time = gateway.time
        self.lastTick = Time(-1.0)

        # idle indicates whether the node stack is ready to advance in time
        self._idle = 0

        # Prepare queues for the stdout and stderr processing threads
        self.queueStdout = collections.deque()
        self.queueStderr = collections.deque()
        self.queueStdin = collections.deque()

        self.exec = exec.split()
        self.isRunning = False


    def startSubprocess(self):
        print(colored(f"Starting subprocess of {self.gateway} at {self.time}", "green"))
        JSONlogger.event("gatewayStart", int(self.time.ms), EUI=self.gateway.eui)

        # stdbuf is required to set no buffering!
        self.proc = subprocess.Popen(
            # Command: ../apps/LoRaGateway/lora_pkt_fwd -d hal -c ./run/GWconfs/C0EE40FFFF29DF10.json
            ["stdbuf", "--input=0", "--output=0", "--error=0", *(self.exec),
                "-d", "hal", "-c", "./run/GWconfs/"+self.gateway.gweui+".json"],
            stdin = subprocess.PIPE, 
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE,
            bufsize = 1,
            universal_newlines=True,
            encoding="utf-8")
        
        # start thread processing stdio
        self.threadStdout = threading.Thread(target = gatewayStackStdoutProcess, args = (self.id, self.proc.stdout, self.queueStdout,))
        self.threadStdout.start()
        self.threadStderr = threading.Thread(target = gatewayStackStderrProcess, args = (self.id, self.proc.stderr, self.queueStderr,))
        self.threadStderr.start()
        self.threadStdin = threading.Thread(target = gatewayStackStdinProcess, args = (self.id, self.proc.stdin, self.queueStdin, self))
        self.threadStdin.start()

        # Report gateway to MeshVis
        if Settings.MESHVIS_EN:
            MeshVisAPI.instance.report_device(MeshVisAPI.Device(
                latitude=self.gateway.gps[0],
                longitude=self.gateway.gps[1],
                altitude=self.gateway.gps[2],
                eui=self.gateway.gweui,
                name=self.gateway.name,
                state="Idle", # This will result in gateways being green in MeshVis
                type="Gateway"
                )
            )

        self.isRunning = True


    def __del__(self):
        if self.isRunning:
            self.isRunning = False
            self.cmd("QUIT")
            print(f"Kill: gatewaystack id {self.id}")
            self.proc.terminate()
            self.proc.join()

            if self.proc.is_alive():
                print(f"Force Kill: gatewaystack id {self.id}")
                self.proc.kill()
                self.proc.join()


    @property
    def idle(self) -> bool:
        return (self._idle >= 1)


    @staticmethod
    def extractValue(id: str, str: str):
        if id=="data":
            m = re.search(f"{id}=([a-fA-F0-9:]+)", str)
            if m:
                value = m.group(1)
                value = value.replace(":","")
                return bytes.fromhex(value)

        elif id=="SF_mask":
            LORA_SF_MASK = {
                7:  int("0x02", 16),
                8:  int("0x04", 16),
                9:  int("0x08", 16),
                10: int("0x10", 16),
                11: int("0x20", 16),
                12: int("0x40", 16),
            }
            m = re.search(f"{id}=0x([a-fA-F0-9:]+)", str)
            value = m.group(1)
                
            ret = [sf for sf, mask in LORA_SF_MASK.items() if mask&int(value,16)]
            return ret

        elif id=="type":
            m = re.search(f"{id}=([a-zA-Z0-9_]+)", str)
            value = m.group(1)
            return value

        else: # ts, frequency, preamble_length, ..... all other numeric values
            m = re.search(f"{id}=(-?[0-9]*)", str)
            if m:
                value = m.group(1)
                return int(value)


    def cmd(self, cmd: str) -> None:
        if self.isRunning:
            self.queueStdin.append(cmd)


    def timeout(self) -> None:
        self.cmd("TIMEOUT")


    def rxDone(self, p : Packet, crcStatus: int, snr: int, rssi: int) -> None:
        # UNUSED params: low_data_rate=, crc=
        #self.cmd("RX_DONE,size={}},data={}}".format(len(data), data.hex()))
        dataString = p.data.hex()
        dataString = ':'.join(dataString[i:i+2] for i in range(0, len(dataString), 2))+':'

        self.cmd(( f"RX_DONE, ts={self.time.ms},"
                   f"frequency={p.packetParam.frequency},"
                   f"preamble_length={p.preambleLength},"
                   f"header_implicit={p.packetParam.implicit_header},"
                   f"crc_status={crcStatus}," # 0=NO_CRC, 1=CRC_OK, 2=CRC_BAD
                   f"iq_inverted={p.packetParam.iq_inverted},"
                   f"spreading_factor={p.packetParam.spreading_factor},"
                   f"bandwidth_kHz={p.packetParam.bandwidth_kHz},"
                   f"coding_rate={p.packetParam.coding_rate},"
                   f"size={p.payloadLength},"
                   f"data={dataString},"
                   f"snr={snr},"
                   f"rssi={rssi},"

                ))


    def txDone(self) -> None:
        self.cmd("TX_DONE")


    def processQueue(self):
        # process all lines in the queue
        while True:
            # get line from the queue
            try:
                line = self.queueStderr.pop()
            except IndexError:
                break

            # process the line
            if line == '.':
                self._idle += 1
            elif line == ':TX_DONE DONE' or \
                line == ':RX_DONE DONE' or \
                line == ':TIMEOUT DONE':
                pass    # ignore these responses to commands
            elif line.startswith(":RX,"):
                params = ["frequency", "preamble_length", "implicit_header", "crc_en", "iq_inverted",
                    "spreading_factor", "bandwidth_kHz", "coding_rate", "low_data_rate", "rx_timeout"] #, "symbol_timeout"]

                #ts = Time(ms = GatewayStack.extractValue("ts", line)+self.time.ms) # GW runs realtime, hence doesn't send the timestamp
                ts = self.time.copy()

                par = {}
                for key in params:
                    # extract all numeric parameters
                    par[key] = GatewayStack.extractValue(key, line)

                # give the parameters to my node object which handles receiving
                self.gateway.receive(ts, par)

            elif line.startswith(":TX"):
                params = ["frequency", "preamble_length", "implicit_header", "crc_en", "iq_inverted",
                    "spreading_factor", "bandwidth_kHz", "coding_rate", "low_data_rate", "power", "size"]

                #ts = Time(ms = GatewayStack.extractValue("ts", line)) # GW runs realtime, hence doesn't send the timestamp
                ts = self.time.copy()
                
                data = GatewayStack.extractValue("data", line)

                par = {}
                for key in params:
                    # extract all numeric parameters
                    par[key] = GatewayStack.extractValue(key, line)

                # GW does not send low data rate parameter
                par["low_data_rate"] = 0

                # give the parameters to my node object which handles transmitting
                self.gateway.transmit(ts, par, data)

            elif line.startswith(":IDLE,"):
                #ts = Time(ms = GatewayStack.extractValue("ts", line)) # GW runs realtime, hence doesn't send the timestamp
                ts = self.time.copy()
                print(f"{self} goes IDLE at {ts}")

                # de-activate receiver or transmitter
                self.gateway.idle(ts)

            elif line.startswith(":CFG_RXRF"):
                params = ["rf_chain", "en", "freq"]

                par = {}
                for key in params:
                    # extract all parameters specified above
                    par[key] = GatewayStack.extractValue(key, line)

                self.gateway.newRxRadio(par)

            elif line.startswith(":CFG_RXIF"):
                params = ["rf_chain", "type", "if_chain", "en", "freq", "bw", "SF_mask"]

                par = {}
                for key in params:
                    # extract all parameters specified above
                    par[key] = GatewayStack.extractValue(key, line)

                self.gateway.newRxChannel(par)

            else:
                print("[{}]WARNING: Unsupported gateway command received:".format(self.gateway.name))
                print(line)

    
    def step(self) -> bool:
        # Check if the subprocess is running, if not, start it when it is the time to
        if not self.isRunning:
            if self.time == self.gateway.startDelayMs:
                self.startSubprocess()
            return True

        self.processQueue()

        if self.lastTick != self.time:
            #self.cmd("")            # empty command is tick command
            self.lastTick.us = self.time.us
            self._idle = 0

        return True # GW runs in realtime -> never idle
        
