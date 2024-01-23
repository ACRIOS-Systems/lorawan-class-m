import requests
import json
import threading
from queue import Queue



class MeshVisAPI:

    instance = None

    class JsonEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, MeshVisAPI.Packet) | isinstance(obj, MeshVisAPI.Device):
                return obj.to_dict()
            return super().default(obj)

    class Request:
        def __init__(self, url:str, method:str="GET", data:str="", headers:dict={}, timeout:int=None):
            self.url = url
            self.method = method
            self.data = data
            self.headers = headers
            self.timeout = timeout

    class Packet:
        def __init__(self, reporterEUI, direction, startTime, endTime, data=""):
            self.reporterEUI=reporterEUI
            self.direction=direction
            self.startTime=startTime # seconds
            self.endTime=endTime # seconds
            self.data = data

        def to_dict(self):
            return self.__dict__

    class Device:
        def __init__(self,
                eui,
                latitude = None,
                longitude = None,
                altitude = None,
                name = None,
                type = None,
                state = None,
                description = None,
                parent = None,
                children = None
            ):
            self.latitude = latitude
            self.longitude = longitude
            self.altitude = altitude
            self.name = name
            self.type = type
            self.eui = eui
            self.state = state
            self.description = description
            self.parent = parent
            self.children = children

        def to_dict(self):
            return self.__dict__



    def __del__(self):
        self.close()


    def __init__(self, server_address:str="127.0.0.1", server_port:int=8050):
        self.base_url = "http://"+server_address+":"+str(server_port)
        
        # Try if the MeshVis is running
        try:
            response = requests.get(self.base_url+"/api", timeout=5)
        except:
            raise Exception("MeshVis unreachable!")
        if not response.content==b"MeshVisOK":
            raise Exception("MeshVis unreachable! (Wrong response)")

        self.queue = Queue()
        self.worker_thread = threading.Thread(target=self._worker)
        self.worker_thread.start()
        MeshVisAPI.instance = self


    def _worker(self):
        while True:
            # Block and wait for data in the queue
            data = self.queue.get()
            if data is None:
                break  # Exit the thread when a None is encountered

            self._send_request(data)


    def _send_request(self, request:Request) -> requests.Response:
        try:
            if request.method.upper()=="POST":
                response = requests.post(self.base_url+request.url, data=request.data, headers=request.headers, timeout=request.timeout)

            elif request.method.upper()=="GET":
                response = requests.get(self.base_url+request.url, data=request.data, headers=request.headers, timeout=request.timeout)

            return response

        except Exception as e:
            print(f"[MeshVisAPI] {e.__doc__}")
            return None



    def _put_request_to_queue(self, request:Request):
        self.queue.put(request)


    def close(self):
        try:
            # Signal the worker thread to exit
            self.queue.put(None)
            # Wait for the worker thread to finish
            self.worker_thread.join()
        except:
            pass


    def report_packet(self, packet:Packet):
        self.report_packets([packet])


    def report_device(self, device:Device):
        self.report_devices([device])


    def report_packets(self, packets:list[Packet]):
        # Convert the prepared list to a JSON string
        json_data = json.dumps(packets, cls=self.JsonEncoder)
        request = self.Request(url="/api/packet", method="POST", data=json_data, headers={'Content-Type': 'application/json'}, timeout=30)
        self._put_request_to_queue(request)


    def report_devices(self, devices:list[Device]):
        # Remove all None values
        data = []
        for dev in devices:
            data.append({k: v for k, v in dev.to_dict().items() if v is not None})

        # Convert the prepared list to a JSON string
        json_data = json.dumps(data, cls=self.JsonEncoder)
        request = self.Request(url="/api/device", method="POST", data=json_data, headers={'Content-Type': 'application/json'}, timeout=30)
        self._put_request_to_queue(request)


    def get_all_packets(self, timeout:int=10) -> list:
        try:
            request = self.Request(url="/api/get-packets", timeout=timeout)
            response = self._send_request(request)
            return json.loads(response.content)
        except Exception as e:
            print(e)
            return None


    def get_all_devices(self, timeout:int=10) -> list:
        try:
            request = self.Request(url="/api/get-devices", timeout=timeout)
            response = self._send_request(request)
            return json.loads(response.content)
        except Exception as e:
            print(e)
            return None


    def purge_packets(self, timeout:int=10):
        try:
            request = self.Request(url="/api/purge-packets", method="POST", timeout=timeout)
            self._put_request_to_queue(request)
            #response = self._send_request(request)
            #return json.loads(response.content)
        except Exception as e:
            print(e)
            return None


    def purge_devices(self, timeout:int=10):
        try:
            request = self.Request(url="/api/purge-devices", method="POST", timeout=timeout)
            self._put_request_to_queue(request)
            #response = self._send_request(request)
            #return json.loads(response.content)
        except Exception as e:
            print(e)
            return None



# Example usage:
if __name__ == "__main__":
    import time

    api = MeshVisAPI(server_address="127.0.0.1", server_port=8050)

    device1 = api.Device(name="Dev1", eui="EUI1", description="Device 1", state="Idle",  type="Gateway", latitude=0, longitude=1, altitude=0, children=["EUI2"])
    device2 = api.Device(name="Dev2", eui="EUI2", description="Device 2", state="Error", type="Node",    latitude=1, longitude=1, altitude=0, parent="EUI1")
    api.report_devices([device1, device2])

    packet1 = api.Packet(direction="Tx", reporterEUI="EUI1", startTime=1, endTime=2, data="Data1")
    packet2 = api.Packet(direction="Rx", reporterEUI="EUI2", startTime=1, endTime=2, data="Data1")
    api.report_packet(packet1)
    api.report_packet(packet2)

    time.sleep(1)

    print("Devices:")
    print(api.get_all_devices())
    print("Packets:")
    print(api.get_all_packets())

    time.sleep(5)

    print("Purging packets...")
    print(api.purge_packets())

    time.sleep(1)

    print("Purging devices...")
    print(api.purge_devices())

    time.sleep(1)

    print("Devices:")
    print(api.get_all_devices())
    print("Packets:")
    print(api.get_all_packets())

    # Close the API when done to ensure the worker thread exits gracefully
    api.close()