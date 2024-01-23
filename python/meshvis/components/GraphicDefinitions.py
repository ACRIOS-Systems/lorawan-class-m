


class GraphicDefinitions():

    def __init__(self):
        pass

    deviceStatusColor = {
        "Idle": "green",
        "Unknown state": "lightgray",
        "Connecting": "orange",
        "Connected": "lightgreen",
        "Error": "tomato"
    }
    deviceStatusColor.setdefault("Unknown state")
    