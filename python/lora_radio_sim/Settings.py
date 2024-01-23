## Global settings file

RUN_TIME = 300 # For how long the simulation should be run in seconds

CSV_PATH = "" # CSV file with device definitions (must be provided by the --csv argument!)

REALTIME = True # Whether to run the simulation in real time (otherwise as fast as possible)

CHIRPSTACK = False # Whether to register devices to the Chirpstack NS

WIRESHARK_TX = True # Whether to report packets transmitted by the devices to the Wireshark
WIRESHARK_RX = True # Whether to report packets received by the devices to the Wireshark
WIRESHARK_ADDR = "127.0.0.1" # IP address or domain name of the Wireshark endpoint
WIRESHARK_PORT = 5555 # UDP port of the Wireshark endpoint

MESHVIS_EN = True # Whether to report packets and devices to the MeshVis
MESHVIS_ADDR = "127.0.0.1" # MeshVis server address
MESHVIS_PORT = 8050 # MeshVis server port