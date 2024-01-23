import threading
import queue
from flask import request, jsonify
from .MeshDevice import MeshDevice as md
from .MeshPacket import MeshPacket as mp

from .TimelineComponent import TimelineComponent
from .MapComponent import MapComponent


class DataInterface():

    @staticmethod
    def parsePackets(data):
        # Init. packets
            for d in data:
                if d.get("reporterEUI") == None:
                    continue
                else:
                    dev = md.getDeviceByEUI(d["reporterEUI"])
                    if dev == None:
                        continue
                    
                    p = dev.getPacketByTimestamp(d.get("startTime"))
                    if p == None:
                        p = mp(reporterEUI=d.get("reporterEUI"),
                                startTime=d.get("startTime"),
                                endTime=d.get("endTime"),
                                direction=d.get("direction"),
                                data=d.get("data"))
                        dev.appendPacket(p)
                    else:
                        # Update attributes
                        for attr, val in d.items():
                            # Forbidden attributes to update
                            if (attr in ["reporterEUI","startTime","packetList","wordList"]): continue
                            with p.lock:
                                setattr(p, attr, val)


    @staticmethod
    def parseDevices(data):
        # Init. or update devices
        for d in data:
            if d.get("eui") == None:
                continue
            else:
                dev = md.getDeviceByEUI(d["eui"])
                if dev==None:
                    # Initialize new device
                    lat = d.get("latitude")
                    lon = d.get("longitude")
                    if (lat != None) & (lon != None):
                        dev = md(eui=d["eui"], latitude=lat, longitude=lon)
                        del d["latitude"]
                        del d["longitude"]
                # Update attributes
                for attr, val in d.items():
                    # Forbidden attributes to update (children and parents are updated below)
                    if (attr in ["eui","children","parent","deviceList","unknownID"]): continue
                    with dev.lock:
                        setattr(dev, attr, val)

        # Update parents and children
        for d in data:
            dev = md.getDeviceByEUI(d.get("eui"))
            if not dev is None:
                if type(d.get("parent")) == str:
                    with dev.lock:
                        dev.parent = md.getDeviceByEUI(d.get("parent"))
                if type(d.get("children")) == list:
                    with dev.lock:
                        dev.children = md.getDeviceByEUI(d.get("children"))

    @staticmethod
    def parserWorker(packetQueue:queue.Queue, deviceQueue:queue.Queue):
        while True:
            changedData = False
            # --- DEVICES ---
            while not deviceQueue.empty():
                data = deviceQueue.get_nowait()
                if data is None:
                    break  # Exit the thread when a None is encountered
                DataInterface.parseDevices(data)
                changedData = True

            # --- PACKETS ---
            while not packetQueue.empty():
                data = packetQueue.get_nowait()
                if data is None:
                    break  # Exit the thread when a None is encountered

                DataInterface.parsePackets(data)
                changedData = True
            
            # Update figures after parsing is done

            TimelineComponent.updateFigure()
            MapComponent.updateFigure()


    def __init__(self, server):
        # JSON processing thread
        self.packetQueue = queue.Queue()
        self.deviceQueue = queue.Queue()
        self.parserThread = threading.Thread(target=DataInterface.parserWorker, args=(self.packetQueue, self.deviceQueue))
        self.parserThread.start()

        # Define the top API endpoint
        @server.route('/meshvis/api', methods=['GET'])
        @server.route('/meshvis/api/', methods=['GET'])
        def apiTop():
            return "MeshVisOK", 200  # Return a response with a 200 status code

        
        # Define an endpoint to delete all packets
        @server.route('/meshvis/api/purge-packets', methods=['POST'])
        def purgePackets():
            try:
                with mp.packetListLock:
                    mp.packetList = []
                    return jsonify("OK"), 200  # Return a JSON response with a 200 status code
            
            except Exception as e:
                return jsonify(e.__str__()), 400  # Return an error response with a 400 status code

        
        # Define an endpoint to delete all devices
        @server.route('/meshvis/api/purge-devices', methods=['POST'])
        def purgeDevices():
            try:
                with md.devListLock:
                    md.deviceList = []
                    return jsonify("OK"), 200  # Return a JSON response with a 200 status code
            
            except Exception as e:
                return jsonify(e.__str__()), 400  # Return an error response with a 400 status code

        
        # Define an endpoint to return all devices
        @server.route('/meshvis/api/get-devices', methods=['GET'])
        def sendDevicesAsJSON():
            try:
                return jsonify(md.getAllDevicesAsDicts()), 200  # Return a JSON response with a 200 status code
            
            except Exception as e:
                return jsonify(e.__str__()), 400  # Return an error response with a 400 status code


        # Define an endpoint to return all packets
        @server.route('/meshvis/api/get-packets', methods=['GET'])
        def sendPacketsAsJSON():
            try:
                return jsonify(mp.getAllPacketsAsDicts()), 200  # Return a JSON response with a 200 status code
            
            except Exception as e:
                return jsonify(e.__str__()), 400  # Return an error response with a 400 status code



        # Define an endpoint to receive device JSON data via POST request
        @server.route('/meshvis/api/device', methods=['POST'])
        def receiveDeviceData():
            try:
                data = request.get_json()  # Parse JSON data from the request and check top-level format
                if not((type(data)==list) & all([type(obj)==dict for obj in data])):
                    raise Exception("Unexpected JSON format!")

                self.deviceQueue.put(data)

                response = {"message": "Data received."}
                return jsonify(response), 200  # Return a JSON response with a 200 status code
            except Exception as e:
                error_message = str(e)
                return jsonify(error_message), 400  # Return an error response with a 400 status code


        # Define an endpoint to receive packet JSON data via POST request
        @server.route('/meshvis/api/packet', methods=['POST'])
        def receivePacketData():
            try:
                data = request.get_json()  # Parse JSON data from the request and check top-level format
                if not((type(data)==list) & all([type(obj)==dict for obj in data])):
                    raise Exception("Unexpected JSON format!")

                self.packetQueue.put(data)

                response = {"message": "Data received successfully."}
                return jsonify(response), 200  # Return a JSON response with a 200 status code
            except Exception as e:
                error_message = str(e)
                return jsonify(error_message), 400  # Return an error response with a 400 status code
