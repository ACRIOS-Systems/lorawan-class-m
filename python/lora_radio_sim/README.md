<!-- ABOUT THE PROJECT -->
# LoRa Radio Simulator

*LoRa Radio Simulator* is a Python based tool for simulation and analysis of wireless communication based on Semtech's LoRa radios.
It reads a CSV list of predefined devices to be simulated. Each device then runs as an external sub-process of the simulator.
This allows to run different device applications in one simulation run. From the device's side, the simulator acts as the hardware radio peripheral
which receives and sends commands through *stdio* using a straightforward text-based [protocol](##Device-Simulator-protocol). To support LoRaWAN networks,
the simulator can optionally connect to a locally running [*ChirpStack*](https://www.chirpstack.io/) instance and register simulated gateways in it.
All the wireless packets are reported from the simulation to [*Wireshark*](https://www.wireshark.org/) in real time, enabling further analysis. For graphical visualization of simulations the [*MeshVis*](https://sw.acrios.com/acrios/meshvis) tool can be used, where the network topology and packet timeline are visualized.

![Simplified diagram of the simulator](/doc/diagrams/diagram_python_outer.svg)


## Source files
|            **File**                   | **Description** |
|:--------------------------------------|:----------------|
| Simulation.py                         | The main simulator script which starts the simulation |
| Settings.py                           | Settings of the simulator, the values can be changed or overriden using [Command line arguments](##Command-line-arguments) |
| modules.py                            | Script which loads the required Python modules outside of the simulator directory |
| AirInterface.py                       | Handing packets between devices and collision checking |
| Packet.py                             | Simulated LoRa packet class |
| NetObjectLoader.py                    | Parsing the device definitions from CSV and instantiation of them in the simulation |
| NetObject.py                          | Prototype class of a device |
| Node.py<br>NodeStack.py               | Node type device behavior and interface to external subprocess |
| Gateway.py<br>GatewayStack.py         | Gateway type device behavior and interface to external subprocess |
| GWconfTemplate.json                   | Template JSON configuration for the [lora_pkt_fwd application](https://sw.acrios.com/acrios/packet_forwarder) which is used to simulate gateways |
| nsDriver/*                            | ChirpStack server API interface |
| Scenarios/*.csv                       | Directory containing predefined scenarios (device definitions) for simulation |
| Scenarios/configurator/DeviceSetup.py | A GUI tool for easy generation of CSV scenario files |
| doc/                                  | Directory contatining documentation files |
| .vscode/                              | Project configuration files for the [Visual Studio Code editor](https://code.visualstudio.com/) |

![Diagram of the simulator](/doc/diagrams/diagram_python_inner.svg)




<!-- USAGE EXAMPLES -->
# Usage
A simulation is started using the [command](#command-line-arguments) described below. It needs to be provided a path to CSV file containing definitions of all devices to be simulated using the --csv argument. All the other arguments are optional, the simulator will use [defualt options](/Settings.py) when not specified.

At startup the simulator runs all the device executables as subprocesses of itself and connects to their [stdio pipes](https://en.wikipedia.org/wiki/C_file_input/output) (*stdin*, *stdout*, *stderr*) which are used for the communication between the simulator and the device using the [protocol](#device-simulator-protocol) specified below. All the communication is logged to *run/* directory which is created automatically. If any files from a previous run are present at the simulation startup they are moved to a *.run.bckup/* directory first. Device events are also logged to the JSON formatted *run/eventLog.json* file.


## Command line arguments
> Simulation.py [-h] --csv path-to-file [--sim-time seconds]
                     [--realtime | --no-realtime]
                     [--chirpstack | --no-chirpstack]
                     [--wireshark-rx | --no-wireshark-rx]
                     [--wireshark-tx | --no-wireshark-tx]
                     [--wireshark-addr IP-or-domain-name]
                     [--wireshark-port port-number]
                     [--meshvis | --no-meshvis]
                     [--meshvis-addr IP-or-domain-name]
                     [--meshvis-port port-number]
>
>> --csv path-to-file
>> - Path to the CSV file containing device definitions
>
>> -h, --help
>> - Show help message and exit
>
>> --sim-time seconds
>> - Simulation run time in seconds
>
>> --realtime, --no-realtime
>> - Slow down the simulation to real time (default)
>
>> --chirpstack, --no-chirpstack
>> - Use the Chirpstack service
>
>> --wireshark-rx, --no-wireshark-rx
>> - Report received packets to Wireshark
>
>> --wireshark-tx, --no-wireshark-tx
>> - Report transmitted packets to Wireshark
>                        
>> --wireshark-addr IP-or-domain-name
>> - IP address or domain name of the Wireshark endpoint
>> - default: 127.0.0.1
>
>> --wireshark-port port-number
>> - UDP port of the Wireshark endpoint
>> - default: 5555
>
>> --meshvis, --no-meshvis
>> - Report packets and devices to MeshVis
>
>> --meshvis-addr IP-or-domain-name
>> - IP address or domain name of the MeshVis server,
>> - default: 127.0.0.1
>
>> --meshvis-port port-number
>> - TCP port of the MeshVis server, default: 8050


<!-- Deivce-Simulator protocol -->
# Device-Simulator protocol
Every command starts with a colon character ":" and ends with a new-line character, here denoted as "\n" 

## Simulator -> Node
(stdin pipe)
- Received a packet containing 3 bytes of data
	> :RX_DONE,size=3,data=AA:BB:CC\n
- Received a packet containing 3 bytes of data with optional info
	> :RX_DONE,size=2,data=AA:BB,SNR=3,RSSI=30\n
- Received a corrupted packet
	> :RX_DONE,CRC_ERROR\n
		
- Transmission is done
	> :TX_DONE\n

- Timeout of reception or transmission
    > :TIMEOUT\n
		
- Execute a single time step (1ms), the device must respond with a dot message ".\n", used only when enabled in settings or using CLI argument
	> :\n

- Stop the application, simulation ended
    > :QUIT\n

## Node -> Simulator
(stderr pipe)
- Packet transmission
	>:TX,<br>
    >    ts=0,<br>
    >    frequency=868100000,<br>
    >    preamble_length=8,<br>
    >    implicit_header=0,<br>
    >    payload_length=23,<br>
    >    crc_en=1,<br>
    >    iq_inverted=0,<br>
    >    spreading_factor=10,<br>
    >    bandwidth_kHz=125,<br>
    >    coding_rate=5,<br>
    >    low_data_rate=0,<br>
    >    power=13,<br>
    >    ramp_time=40,<br>
    >    tx_timeout=0,<br>
    >    symbol_timeout=0,<br>
    >    size=23,<br>
    >    data=00:01:00:F0:E0:D0:C0:B0:A0:02:00:FF:EE:DD:CC:BB:AA:01:00:6C:4D:01:2B:\n

	
- Start reception mode
	>:RX,<br>
    >    ts=0,<br>
    >    frequency=0,<br>
    >    preamble_length=0,<br>
    >    implicit_header=0,<br>
    >    payload_length=0,<br>
    >    crc_en=0,<br>
    >    iq_inverted=0,<br>
    >    spreading_factor=0,<br>
    >    bandwidth_kHz=7,<br>
    >    coding_rate=5,<br>
    >    low_data_rate=0,<br>
    >    rx_timeout=0,<br>
    >    symbol_timeout=0\n
		
- Idle (stop RX mode)
	>:IDLE,ts=5513\n

- Response to the single time step command (:\n), sent only if the node is ready to step forward in time
	> .\n


## Simulator -> Gateway
(stdin pipe)
- Received a packet
    >:RX_DONE,<br>
    >   ts=114.0,<br>
    >   frequency=868100000,<br>
    >   preamble_length=8,<br>
    >   header_implicit=0,<br>
    >   crc_status=1,<br>
    >   iq_inverted=0,<br>
    >   spreading_factor=8,<br>
    >   bandwidth_kHz=125,<br>
    >   coding_rate=5,<br>
    >   size=23,<br>
    >   data=00:00:00:f0:e0:d0:c0:b0:a0:05:00:ff:ee:dd:cc:bb:aa:01:00:fa:2c:1e:c2:,<br>
    >   snr=-7,<br>
    >   rssi=-77\n

- Stop the application, simulation ended
    > :QUIT\n


## Gateway -> Simulator
(stderr pipe)
- Set up Rx RF chain (an Rx radio)
    >:CFG_RXRF,<br>
    >    rf_chain=0,<br>
    >    en=1,<br>
    >    freq=867500000,<br>
    >    rssi_offset=-158.000000,<br>
    >    radio_type=2,<br>
    >    tx_enable=1,<br>
    >    tx_notch_freq=0\n

- Set up Rx IF chain (an Rx channel)
    >:CFG_RXIF,<br>
    >    rf_chain=0,<br>
    >    type=lora_multi,<br>
    >    if_chain=0,<br>
    >    en=1,<br>
    >    freq=-400000,<br>
    >    bw=125000,<br>
    >    SF_mask=0x7e<br>

- Packet transmission
    >:TX<br>
    >    modulation=LORA,<br>
    >    frequency=868100000,<br>
    >    power=14,<br>
    >    size=33,<br>
    >    bandwidth_kHz=125<br>
    >    rf_chain=0,<br>
    >    crc_en=1,<br>
    >    preamble_length=8,<br>
    >    spreading_factor=9,<br>
    >    coding_rate=5,<br>
    >    implicit_header=0,<br>
    >    iq_inverted=1,<br>
    >    data=20:F9:8F:F9:97:D4:67:DC:E3:6C:D0:1A:FA:9B:0E:D9:A3:3D:53:02:D2:79:AF:FA:9F:53:FE:2D:0D:18:BA:FD:56:\n
