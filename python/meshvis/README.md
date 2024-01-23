<!-- ABOUT THE PROJECT -->
# MeshVis
*MeshVis* is a Python based tool for visualisation and monitoring of LoRaWAN-based networks (including the Class-M). It was developed along with the [*LoRa Radio Simulator*](https://sw.acrios.com/acrios/lora-radio-sim) as a way of visualising the devices and frames of a simulation run. However, thanks to its simple JSON API it is suitable for real-world deployments as well.

![Screenshot of the MeshVis](/doc/meshvis.png)

## Disclaimer
The current implementation of the tool does not incorporate any security measures. Therefore, it should not be made directly accessible from the internet! 



<!-- USAGE EXAMPLES -->
# Usage
MeshVis can be run using [the command](#command-line-arguments) provided below. After starting it behaves as a service which provides an HTTP web-interface and JSON API.

The graphical user interface is accessible at the root URL http://*address*:*port*/. The interface is split to three subwindows and Menu bar on the left. The top left and right windows show the devices and their connections in hierarchy view and on a map. The bottom window shows a timeline of captured frames.

The API uses URLs http://*address*:*port*/api/*command* and expects [one of the commands](#api) described below.



## Command line arguments
> python3 App.py [-p port-number] [-d]
>
>> -p port-number, --port port-number
>> - Specifies TCP listening port number
>> - default: 8050
>
>> -d, --debug
>> - Runs the MeshVis with debug options on
>> - default: false
>



## API

| **Command** | **HTTP Method** | **Description**                                                                    |
|:-----------:|:---------------:|------------------------------------------------------------------------------------|
| device      | POST            | Expects a JSON in the body of the request containing a list of device dictionaries |
| packet      | POST            | Expects a JSON in the body of the request containing a list of packet dictionaries |
| get-devices | GET             | Returns a JSON list of all current devices                                         |
| get-packets | GET             | Returns a JSON list of all current packets                                         |

Examples of JSON format is provided in [the test directory](test) along with Bash scripts for uploading them to a locally running instance of the MeshVis.


