"""
NSQueue: This queue is accessed by the hardcoded parent and packetForwarder. Hardcoded parent inserts a dictionaries with the request and its parameters,
            packetForwarder uses it to reconstruct a lorawan packet.
"""

###### MAKE THIS THREAD SAFE!!!! #####
class NS_Queue():
    def __init__(self):
        self.NS_input = []      #incoming DATA from the network
        self.NS_output = []     #DATA to be sent to the network

    def NS_input_add(self, Data):
        self.NS_input.append(Data)

    def NS_input_take(self):
        Data = self.NS_input[0]
        self.NS_input.pop(0)
        return Data

    def NS_input_size(self):
        return len(self.NS_input)
    

    def NS_output_add(self, Data):
        self.NS_output.append(Data)

    def NS_output_take(self):
        Data = self.NS_output[0]
        self.NS_output.pop(0)
        return Data

    def NS_output_size(self):
        return len(self.NS_output)