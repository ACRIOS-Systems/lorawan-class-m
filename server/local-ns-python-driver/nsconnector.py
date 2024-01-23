from transportChirpstack import chirpstackConnector
from config import *
import datetime

ns = None
MESHNetworkServer = None
MESHOrganization = None
MESHApplication = None
MESHDeviceProfile = None
MESHServiceProfile = None
MESHGatewayProfile = None

def networkServerInitialize(AS_IP_ADDR, MQTT_IP_ADDR, AS_PASSWORD, NS_IP_ADDR="172.31.255.252"):
    global ns
    global MESHDeviceProfile
    global MESHServiceProfile
    global MESHApplication
    global MESHOrganization
    global MESHNetworkServer
    global MESHGatewayProfile
    #AS_PASSWORD = os.getenv("AS_PASSWORD")
    #AS_IP_ADDR = os.getenv("AS_IP_ADDR")
    #NS_IP_ADDR = os.getenv("NS_IP_ADDR")
    #MQTT_IP_ADDR = os.getenv("MQTT_IP_ADDR")

    MESHNetworkServerAddress = NS_IP_ADDR+":8000"

    ns = chirpstackConnector( mqttServerURL=MQTT_IP_ADDR, mqttServerPort=1883, useWebsockets = False, gRPCURL = 'http://'+AS_IP_ADDR+':8080', gRPCUser = "admin", gRPCPassword = AS_PASSWORD)

    foundMESHNetworkServer = False
    for networkServer in ns.networkServers:
        if ns.networkServers[networkServer].server == MESHNetworkServerAddress:
            foundMESHNetworkServer = True
            break
    if not foundMESHNetworkServer:
        ns.createNetworkServer(MESHNetworkServerName, MESHNetworkServerAddress)
    MESHNetworkServer = ns.getNetworkServerByServer(MESHNetworkServerAddress)

    foundMESHOrganization = False
    for organization in ns.organizations:
        if ns.organizations[organization].name == MESHOrganizationName:
            foundMESHOrganization = True
            break
    if not foundMESHOrganization:
        ns.createOrganization(MESHOrganizationName)
    MESHOrganization = ns.getOrganizationByName(MESHOrganizationName)

    foundMESHServiceProfile = False
    for profile in ns.serviceProfiles:
        if ns.serviceProfiles[profile].name == MESHServiceProfileName:
            foundMESHServiceProfile = True
            break
    if not foundMESHServiceProfile:
        ns.createServiceProfile(MESHServiceProfileName, MESHOrganization.id, MESHNetworkServer.id)
    MESHServiceProfile = ns.getServiceProfileByName(MESHServiceProfileName)

    foundMESHDeviceProfile = False
    for profile in ns.deviceProfiles:
        if ns.deviceProfiles[profile].name == MESHDeviceProfileName:
            foundMESHDeviceProfile = True
            break
    if not foundMESHDeviceProfile:
        ns.createDeviceProfile(MESHDeviceProfileName, MESHOrganization.id, MESHNetworkServer.id)
    MESHDeviceProfile = ns.getDeviceProfileByName(MESHDeviceProfileName)

    foundMESHApplication = False
    for application in ns.applications:
        if ns.applications[application].name == MESHApplicationName:
            foundMESHApplication = True
            break
    if not foundMESHApplication:
        ns.createApplication(MESHApplicationName, MESHServiceProfile.id, MESHOrganization.id)
    MESHApplication = ns.getApplicationByName(MESHApplicationName)

    foundMESHGatewayProfile = False
    for profile in ns.gatewayProfiles:
        if ns.gatewayProfiles[profile].name == MESHGatewayProfileName:
            foundMESHGatewayProfile = True
            break
    if not foundMESHGatewayProfile:
        ns.createGatewayProfile(MESHGatewayProfileName, MESHNetworkServer.id, MESHBasicChannels, MESHExtraChannels)
    MESHGatewayProfile = ns.getGatewayProfileByName(MESHGatewayProfileName)


def networkServerCheckDeveuiExists(deveui):
    try:
        ns.getDeviceByDeveui(deveui)
        return True
    except Exception as e:
        return False

def networkServerRegisterGateway(newGateway):
    ns.createGateway(newGateway["identification"], newGateway["description"], newGateway["latitude"], newGateway["longitude"], newGateway["altitude"],  MESHOrganization.id, MESHNetworkServer.id, MESHServiceProfile.id, MESHGatewayProfile.id, newGateway["gweui"])

def networkServerUnregisterGateway(gateway_identification):
    ns.deleteGateway(gateway_identification)

def networkServerGetGatewayStatus(gatewayName):
    gw = ns.getGatewayByName(gatewayName)
    if gw == None:
        return {"lastSeen": "1970-01-01T00:00:00.000Z"}
    return {"lastSeen": datetime.datetime.fromtimestamp(gw.last_seen_at.seconds).isoformat()+".000Z"}

def networkServerRegisterNode(newNode, RxCallback, JoinedCallback, JoinRequestCallback, userdata):
    ns.registerDevice(newNode["deveui"], newNode["name"], newNode["description"], application_id=MESHApplication.id, device_profile_id=MESHDeviceProfile.id)
    ns.setDeviceAppKey(newNode["deveui"], newNode["appkey"])
    ns.registerReceiveCallback(newNode["deveui"], callback=RxCallback, userdata=userdata)
    ns.registerJoinCallback(newNode["deveui"], callback=JoinedCallback, userdata=userdata)
    ns.registerJoinRequestCallback(newNode["deveui"], callback=JoinRequestCallback, userdata=userdata)

def networkServerRegisterCallback(deveui, RxCallback, JoinedCallback, JoinRequestCallback, userdata):
    ns.registerReceiveCallback(deveui, callback=RxCallback, userdata=userdata)
    ns.registerJoinCallback(deveui, callback=JoinedCallback, userdata=userdata)
    ns.registerJoinRequestCallback(deveui, callback=JoinRequestCallback, userdata=userdata)

def networkServerUnregisterNode(node_deveui):
    ns.unregisterDevice(node_deveui)

def networkServerGetNodeDevaddr(deveui):
    return ns.getDevaddrByDeveui(deveui)

