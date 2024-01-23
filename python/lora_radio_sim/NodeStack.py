from lora_sim_lib.Time import Time
from lora_sim_lib.JSONlogger import JSONlogger
import Settings
import subprocess
import collections
import threading
import time
import re # Regular expression
from termcolor import colored

if Settings.MESHVIS_EN:
    from lora_sim_lib.MeshVisAPI import MeshVisAPI


def nodeStackStdinProcess(id, stdin, queue, self):
    #with open(f"run/deviceLogs/{id}.stdin", "a") as f: # resource hungry!
        with open(f"run/deviceLogs/{id}.hstdin", "a") as fh:
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

                # write line to a file
                #f.write(f":{cmd}\n") # resource hungry!
                #f.flush()

                # write human-readable stdin file
                if cmd != "":
                    fh.write(f":{cmd}\n")
                    fh.flush()

        print(colored(f"NodeStack[{id}]: stdin Thread Ends", "red"))


def nodeStackStdoutProcess(id, stdout, queue):
    with open(f"run/deviceLogs/{id}.stdout", "a") as f:
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

    print(colored(f"NodeStack[{id}]: stdout Thread Ends", "red"))


def nodeStackStderrProcess(id, stderr, queue):
    with open(f"run/deviceLogs/{id}.stderr", "a") as f:
        with open(f"run/deviceLogs/{id}.hstderr", "a") as fh:
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

    print(colored(f"NodeStack[{id}]: stderr Thread Ends", "red"))



class NodeStack:

    def __str__(self) -> str:
        return self.node.__str__()


    def __init__(self, node, exec) -> None:

        # # TODO: remove watchdog when LoRaMac-node is fixed
        #self.watchdog = 0

        self.id = node.id
        self.node = node
        self.time = node.time
        self.lastTick = Time(-1.0)

        # idle indicates whether the node stack is ready to advance in time
        self._idle = 0

        # Prepare queues for the stdio processing threads
        self.queueStdout = collections.deque()
        self.queueStderr = collections.deque()
        self.queueStdin = collections.deque()

        self.exec = exec.split()
        self.isRunning = False


    def startSubprocess(self):
        print(colored(f"Starting subprocess of {self.node} at {self.time}", "green"))
        JSONlogger.event("nodeStart", int(self.time.ms), EUI=self.node.eui)

        # Format EUIs and key for the node binary (adding colons)
        dEUI = ':'.join([self.node.devEUI[i:i+2] for i,j in enumerate(self.node.devEUI) if not (i%2)])
        aEUI = ':'.join([self.node.appEUI[i:i+2] for i,j in enumerate(self.node.appEUI) if not (i%2)])
        aKey = ':'.join([self.node.appKey[i:i+2] for i,j in enumerate(self.node.appKey) if not (i%2)])

        # stdbuf is required to set no buffering!
        self.proc = subprocess.Popen(
            ["stdbuf", "--input=0", "--output=0", "--error=0", *(self.exec),
                "-a", aEUI, "-d", dEUI,
                "-k", aKey, "-j", self.node.joinDR],
            stdin = subprocess.PIPE, 
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE,
            bufsize = 1,
            universal_newlines=True,
            encoding="utf-8")
        
        # start threads processing stdio
        self.threadStdout = threading.Thread(target = nodeStackStdoutProcess, args = (self.id, self.proc.stdout, self.queueStdout,))
        self.threadStderr = threading.Thread(target = nodeStackStderrProcess, args = (self.id, self.proc.stderr, self.queueStderr,))
        self.threadStdin = threading.Thread(target = nodeStackStdinProcess,  args = (self.id, self.proc.stdin, self.queueStdin, self))
        
        # The thread start() procedure is too slow because of it being foolproof
        # Since new threads are being started only from the main thread any race conditions cannot happen
        #self.threadStdout.start()
        #self.threadStderr.start()
        #self.threadStdin.start()
        threading._limbo[self.threadStdout] = self.threadStdout
        threading._limbo[self.threadStderr] = self.threadStderr
        threading._limbo[self.threadStdin] = self.threadStdin
        threading._start_new_thread(self.threadStdout._bootstrap, ())
        threading._start_new_thread(self.threadStderr._bootstrap, ())
        threading._start_new_thread(self.threadStdin._bootstrap, ())

        # Report node to MeshVis
        if Settings.MESHVIS_EN:
            MeshVisAPI.instance.report_device(MeshVisAPI.Device(
                latitude=self.node.gps[0],
                longitude=self.node.gps[1],
                altitude=self.node.gps[2],
                eui=self.node.devEUI,
                name=self.node.name,
                state="Connecting", # This will result in nodes being orange in MeshVis
                type="Node"
                )
            )

        self.isRunning = True


    def __del__(self):
        if self.isRunning:
            self.isRunning = False
            self.queueStdin.put(None)
            self.cmd("QUIT")
            print(f"Kill: nodestack id {self.id}")
            self.proc.terminate()
            self.proc.join()

            if self.proc.is_alive():
                print(f"Force Kill: nodestack id {self.id}")
                self.proc.kill()
                self.proc.join()


    @property
    def idle(self) -> bool:
        return (self._idle >= 1)


    @staticmethod
    def extractValue(id: str, str: str):

        if id == "data":
            m = re.search(f"{id}=([a-fA-F0-9:]+)", str)
            if m:
                value = m.group(1)
                value = value.replace(":","")
                return bytes.fromhex(value)

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


    def rxDone(self, data : bytes, snr : int, rssi : int) -> None:
        dataStr = data.hex()
        dataStr = ':'.join(dataStr[i:i+2] for i in range(0, len(dataStr)+1, 2))
        self.cmd("RX_DONE,size={},data={},SNR={},RSSI={}".format(len(data), dataStr, snr, rssi))


    def rxCRCerror(self) -> None:
        self.cmd("RX_DONE,CRC_ERROR")


    def preambleDetected(self) -> None:
        self.cmd("PREAMBLE_DETECTED")
    

    def headerDetected(self, snr : int, rssi : int) -> None:
        self.cmd("HEADER_VALID,SNR={},RSSI={}".format(snr, rssi))


    def headerCRCerror(self) -> None:
        self.cmd("HEADER_ERROR")

    
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
            elif line.startswith(":"):
                if line == ':TX_DONE DONE' or \
                    line == ':RX_DONE DONE' or \
                    line == ':TIMEOUT DONE':
                    pass    # ignore these responses to commands
                elif line.startswith(":RX,"):
                    params = ["frequency", "preamble_length", "implicit_header", "crc_en", "iq_inverted",
                        "spreading_factor", "bandwidth_kHz", "coding_rate", "low_data_rate", "rx_timeout"] #, "symbol_timeout"]

                    ts = Time(ms = NodeStack.extractValue("ts", line)+self.time.ms)
                    print(colored(f"{self} goes to RX mode at {self.time.ms} ms", "light_cyan"))
                    par = {}
                    for key in params:
                        # extract all numeric parameters
                        par[key] = NodeStack.extractValue(key, line)

                    # give the parameters to my node object which handles receiving
                    self.node.receive(ts, par)

                elif line.startswith(":TX,"):
                    params = ["frequency", "preamble_length", "implicit_header", "crc_en", "iq_inverted",
                        "spreading_factor", "bandwidth_kHz", "coding_rate", "low_data_rate", "power", "ramp_time", "tx_timeout", "size"] #, "symbol_timeout"]

                    ts = Time(ms = NodeStack.extractValue("ts", line)+self.time.ms)
                    data = NodeStack.extractValue("data", line)
                    
                    par = {}
                    for key in params:
                        # extract all numeric parameters
                        par[key] = NodeStack.extractValue(key, line)

                    # Tx power calculation
                    #   https://stackforce.github.io/LoRaMac-doc/LoRaMac-doc-v4.4.5/group___r_e_g_i_o_n.html#gab33618449f2a573142c463ab071ef8ed
                    #   https://www.thethingsnetwork.org/docs/lorawan/regional-parameters/#eu863-870-summary
                    
                    # Does the node give dBm or "TX_POWER_x" in command?
                    #   Assuming dBm without these:
                    #MAX_ERP = 14 # dBm
                    #par["power"] = MAX_ERP - 2*(par["power"])


                    # give the parameters to my node object which handles transmitting
                    self.node.transmit(ts, par, data)

                elif line.startswith(":IDLE,"):
                    ts = Time(ms = NodeStack.extractValue("ts", line)+self.time.ms)
                    print(colored(f"{self} goes IDLE at {ts}", "grey"))

                    # de-activate receiver or transmitter
                    self.node.idle()
                else:
                    print("WARNING: Unsupported node command received:")
                    print(line)

    
    def step(self) -> bool:
        # Check if the subprocess is running, if not, start it when it is the time to
        if not self.isRunning:
            if self.time == self.node.startDelayMs:
                self.startSubprocess()
            return True

        self.processQueue()

        #if self.watchdog > 1000:
            #self.cmd("")
            #self.watchdog = 0

        if Settings.REALTIME:
            if self.lastTick != self.time:
                if self.node.timingCmds:
                    self.cmd("")            # empty command is tick command
                self.lastTick.us = self.time.us
                self._idle = 0
                #self.watchdog = 0
            #else:
                #self.watchdog += 1
            
            return True # In realtime mode, the device can't block
        
        else:
            if self.lastTick != self.time:
                self.cmd("")            # empty command is tick command
                self.lastTick.us = self.time.us
                self._idle = 0

            return self.idle
        
