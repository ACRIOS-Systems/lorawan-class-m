from lora_sim_lib.Time import Time
import Settings
import csv
from Gateway import Gateway
from Node import Node
from AirInterface import AirInterface
import time
import os
import json

try:
    import ns_chirpstack3_api.nsConnector as nsConn
except:
    pass


class NetObjectLoader():

    def __init__(self, time: Time, air: AirInterface) -> None:
        self.time = time
        self.air = air
    
    def loadCSV(self, file: str) -> list:
        devices = []
        f = open(file, 'r')
        reader = csv.reader(f)
        header = self.__stripSpaces(next(reader, None))

        # Columns:  "type"          (gateway/node)
        #           "regChirpstack" (Whether to register the device in Chirpstack)
        #           "timingCmds"    (Whether to use the timing commands)
        #           "name"          (Device name for server, for GW must be a number!)
        #           "latitude"      (GPS coordinate)
        #           "longitude"     (GPS coordinate)
        #           "altitude"      (GPS coordinate)
        #           "startDelay"    (Start delay of the device in ms)
        #           "deveui"        (DevEUI-64)
        #           "appeui"        (AppEUI-64)
        #           "appkey"        (AppKey-128)
        #           "joindr"        (Join data rate)
        #           "description"   (Description for server)
        while (line := next(reader, None)):
            line = self.__stripSpaces(line)
            cfg = self.__parseLine(header, line)

            if cfg["type"].lower() == "gateway":
                devices.append(self.__loadGateway(cfg))
                pass
            elif cfg["type"].lower() == "node":
                devices.append(self.__loadNode(cfg))
            else:
                #raise Warning("Unexpected NetObject type \"{}\" in file {} on line {}.".format(line[0], file, reader.line_num))
                print("Unexpected NetObject type \"{}\" in file {} on line {}.".format(line[0], file, reader.line_num))

        f.close()
        return devices


    def __loadNode(self, cfg) -> Node:
        cfg["latitude"] = float(cfg["latitude"])
        cfg["longitude"] = float(cfg["longitude"])
        cfg["altitude"] = float(cfg["altitude"])
        cfg["gps"] = (cfg["latitude"], cfg["longitude"], cfg["altitude"])
        cfg["deveui"] = cfg.pop("eui-64")

        if Settings.CHIRPSTACK:
            if cfg["regChirpstack"].lower() in ("true", "t", "yes", "1"):
                nsConn.networkServerRegisterNode(cfg, None, None, None, None)
                # Let the Chirpstack process
                time.sleep(0.25)

        time.sleep(1) # Program hangs without this
        return Node(self.time, self.air, cfg["exec"], cfg["gps"], cfg["deveui"], cfg["appeui"], cfg["appkey"], cfg["joindr"], cfg["name"], cfg["timingCmds"].lower() in ("true", "t", "yes", "1"), Time(ms=int(cfg["startDelay"])))



    def __loadGateway(self, cfg) -> Gateway:
        cfg["latitude"] = float(cfg["latitude"])
        cfg["longitude"] = float(cfg["longitude"])
        cfg["altitude"] = float(cfg["altitude"])
        cfg["gps"] = (cfg["latitude"], cfg["longitude"], cfg["altitude"])
        cfg["gweui"] = cfg.pop("eui-64")
        cfg["identification"] = cfg.pop("name")

        # Copy the template config file to customized instance
        if not os.path.isdir("./run/GWconfs"):
            os.makedirs("./run/GWconfs")

        file = open('./GWconfTemplate.json',mode='r')
        s = file.read()
        file.close()

        jsonCfg = json.loads(s)
        jsonCfg["gateway_conf"]["gateway_ID"]    = cfg["gweui"]
        jsonCfg["gateway_conf"]["ref_latitude"]  = cfg["latitude"]
        jsonCfg["gateway_conf"]["ref_altitude"]  = cfg["altitude"]
        jsonCfg["gateway_conf"]["ref_longitude"] = cfg["longitude"]

        file = open("./run/GWconfs/"+cfg["gweui"]+".json", "w")
        file.write(json.dumps(jsonCfg, indent=4))
        file.close()

        if Settings.CHIRPSTACK:
            if cfg["regChirpstack"].lower() in ("true", "t", "yes", "1"):
                # Register the GW to the NS
                nsConn.networkServerRegisterGateway(cfg)
                # Let the Chirpstack process
                time.sleep(1) # Program hangs without this
        else:
            print("Error: Simulating gateway without Chirpstack - limited function!")

        return Gateway(self.time, self.air, cfg["exec"], cfg["gps"], cfg["gweui"], cfg["identification"], Time(ms=int(cfg["startDelay"])))

    @staticmethod
    def __parseLine(head, line) -> dict:
        if len(line) == 0:
            return None

        ret = dict()
        for i in range(len(head)):
            ret[head[i]] = line[i]
        else:
            return ret

    @staticmethod
    def __stripSpaces(line):
        for i in range(len(line)):
            line[i] = line[i].strip()
        return line
