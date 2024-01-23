



deviceList = []


class GUIDevice():

    deviceParameters = [
        "type",
        "name",
        "latitude",
        "longitude",
        "altitude",
        "regChirpstack",
        "timingCmds",
        "exec",
        "startDelay",
        "eui-64",
        "appeui",
        "appkey",
        "joindr",
        "description",
    ]

    def __init__(self, name, latitude, longitude, marker,
                params = None
            ):   
        self.marker = marker

        self.params = params if not params==None else {}
        for p in self.deviceParameters:
            if not p in self.params:
                self.params[p] = ""
        
        self.params["name"] = name
        self.params["latitude"] = latitude
        self.params["longitude"] = longitude

    @property
    def name(self):
        return self.params["name"]
    @property
    def latitude(self):
        return self.params["latitude"]
    @property
    def longitude(self):
        return self.params["longitude"]


    def updateParam(self, param, value):
        self.params[param] = value


    @staticmethod
    def getDeviceFromMarker(marker):
        devList = deviceList # type: list[GUIDevice]
        for device in devList:
            if device.marker == marker:
                return device
        raise Exception("Something went wrong! There is no device in deviceList for the given marker.") 
        return None

    @staticmethod
    def getDeviceByName(name):
        devList = deviceList # type: list[GUIDevice]
        for device in devList:
            if device.name == name:
                return device
        return None