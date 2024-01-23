import sqlCleaner
from nsconnector import networkServerInitialize, networkServerRegisterNode, networkServerRegisterGateway
from sqlCleaner import nonceCleanup
from time import sleep
import os

#os.environ["GRPC_TRACE"] = "all"
#os.environ["GRPC_VERBOSITY"] = "debug"
#os.environ["GRPC_DNS_RESOLVER"] = "native"

def RxCallback(ReceivedData, port, timestamp, context, deveui, userdata):
    print("Received data at port %d" % port)
    print(userdata)

def JoinedCallback(timestamp, context, deveui, userdata):
    print(deveui + " successfully joined!")
    print(userdata)
    
def JoinRequestCallback(timestamp, deveui, joinRequestData):
    print(deveui + " wants to join!")


networkServerInitialize("127.0.0.1", "127.0.0.1", "astest")

networkServerRegisterGateway({"identification": "test", "description": "test gateway", "latitude": 49, "longitude": 15, "altitude": 330, "gweui": "DEADBEEFDEADBEEF"})

networkServerRegisterNode({"deveui":"AABBCCDD11223344", "name":"testDevice", "appkey":"11223344556677881122334455667788", "description": "This is my test device"},
    RxCallback, JoinedCallback, JoinRequestCallback, "SomeUserData")


while True:
    print("Clean all nonces!")
    nonceCleanup()
    sleep(10)