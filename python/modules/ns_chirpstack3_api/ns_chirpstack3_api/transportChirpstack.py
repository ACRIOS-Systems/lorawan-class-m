import json
import requests
import grpc
from chirpstack_api.as_pb.external import api
import chirpstack_api.common
import chirpstack_api.as_pb.as_pb_pb2_grpc
import threading
import paho.mqtt.client as mqtt
import base64
import queue
from time import sleep, time
import traceback

class chirpstackConnector:

    def log(self, txt):
        if not self.silent:
            print(txt)

    def renewToken(self):
        t = time()
        if t - self.lastRenewalTimestamp > self.renewPeriod:
            self.lastRenewalTimestamp = t
            self.jwt = self.getJwt(self.gRPCUser, self.gRPCPassword)
            self.auth_token = [("authorization", "Bearer %s" % self.jwt)]

    def __init__(self, mqttServerURL="127.0.0.1", mqttServerPort=1883, useWebsockets = False, wsLogin="admin:admin", wsPath="/mqtt/", gRPCURL = 'http://127.0.0.1', gRPCUser = "admin", gRPCPassword = "nstest", keepalive=20, silent = False):

        self.silent = silent

        self.filter = []

        # The callback for when the client receives a CONNACK response from the server.
        def on_connect(client, userdata, flags, rc):
            self = userdata
            self.log("Connected with result code "+str(rc))
            client.subscribe("application/+/device/+/event/#")
            client.subscribe("gateway/+/event/up") # needed for join-request detection

        # The callback for when a PUBLISH message is received from the server.
        def on_message(client, userdata, msg):
            try:
                self = userdata
                splitted = msg.topic.split("/")

                if splitted[0] == "gateway": # report directly from gateway - join-request detection
                    phymsg = json.loads(msg.payload)
                    phyPayload = phymsg["phyPayload"]
                    rawPayload = base64.b64decode(phyPayload)
                    if rawPayload[0] == 0: # 0 is JOIN REQUEST
                        deveuiInversed = rawPayload[9:17]
                        deveuiBytes = deveuiInversed[::-1]
                        deveui = ''.join(["%02x" % x for x in deveuiBytes]) # note: lower case x !
                        if deveui in self.devices:
                            ts = time()
                            if "join_req_callback" in self.devices[deveui]:
                                if "join_req_userdata" in self.devices[deveui]:
                                    self.devices[deveui]["join_req_callback"](ts, deveui, self.devices[deveui]["join_req_userdata"])
                                else:
                                    self.devices[deveui]["join_req_callback"](ts, deveui, None)
                    return

                deveui = splitted[3]
                event = splitted[5]
                self.log(f"[{deveui}]: {event}")
                if event == "up":
                    ts = time()
                    context = json.loads(msg.payload)
                    if deveui in self.devices:
                        self.provCheck(deveui)
                        port = context["fPort"]
                        try:
                            data = b""
                            if "data" in context:
                                if context["data"] != None:
                                    data = base64.b64decode(context["data"])
                        except:
                            self.log("Could not parse: " + str(context["data"]))

                        asHex = ''.join(["%02X " % x for x in data])
                        name = self.devices[deveui]["info"].name
                        self.log(f"Received uplink from [{deveui}, {name}] (port {port}): {asHex}")


                        if "callback" in self.devices[deveui]:
                            if "userdata" in self.devices[deveui]:
                                self.devices[deveui]["callback"](data, port, ts, context, deveui, self.devices[deveui]["userdata"])
                            else:
                                self.devices[deveui]["callback"](data, port, ts, context, deveui, None)
                        else:
                            self.devices[deveui]["queue"].put({
                                "timestamp": ts,
                                "data": data,
                                "port": port,
                                "context": context
                            })
                    else:
                        self.log(f"Unknown node {deveui}, dropping message!")

                elif event == "join":
                    ts = time()
                    context = json.loads(msg.payload)
                    if deveui in self.devices:
                        if "join_callback" in self.devices[deveui]:
                            if "join_userdata" in self.devices[deveui]:
                                self.devices[deveui]["join_callback"](ts, context, deveui, self.devices[deveui]["join_userdata"])
                            else:
                                self.devices[deveui]["join_callback"](ts, context, deveui, None)

            except Exception as e:
                self.log(e)
                print(traceback.format_exc())

        if useWebsockets:
            client = mqtt.Client(userdata=self, transport="websockets")
            headers = {"authorization": "Basic "+base64.b64encode(wsLogin.encode("utf-8")).decode()}
            client.ws_set_options(path=wsPath, headers=headers)
            if ("https://" in mqttServerURL) or ("wss://" in mqttServerURL):
                client.tls_set()
                
                # USE THESE TWO LINES FOR SELF SIGNED CERTS, for debug only!
                #client.tls_set(cert_reqs=ssl.CERT_NONE)
                #client.tls_insecure_set(True)
        else:
            client = mqtt.Client(userdata=self)
        self.client = client
        self.mqttServerURL = mqttServerURL
        self.mqttServerPort = mqttServerPort
        client.on_connect = on_connect
        client.on_message = on_message


        self.gRPCURL = gRPCURL
        if gRPCURL.startswith("https://"):
            self.channelSecure = True
            gRPCURL = gRPCURL.split("://")[1]
            self.channel = grpc.secure_channel(gRPCURL, grpc.ssl_channel_credentials())
        else:
            self.channelSecure = False
            if "://" in gRPCURL:
                gRPCURL = gRPCURL.split("://")[1]
            self.channel = grpc.insecure_channel(gRPCURL)

        self.gRPCPassword = gRPCPassword
        self.gRPCUser = gRPCUser
        self.renewPeriod = 3600
        self.lastRenewalTimestamp = time()-self.renewPeriod-1
        self.renewToken()



        # build list of available devices at the network server
        devicesList = self.listDevices(limit=99999)
        self.devices = {}
        for dev in devicesList:
            self.devices[dev.dev_eui] = {}
            self.devices[dev.dev_eui]["info"] = dev
            self.devices[dev.dev_eui]["queue"] = queue.Queue()

        # build list of available device profiles at the network server
        deviceProfilesList = self.listDeviceProfiles(limit=99999)
        self.deviceProfiles = {}
        for profile in deviceProfilesList:
            self.deviceProfiles[profile.id] = profile

        # build list of available applications at the network server
        applicationsList = self.listApplications(limit=99999)
        self.applications = {}
        for application in applicationsList:
            self.applications[application.id] = application

        # build list of available service profiles at the network server
        serviceProfilesList = self.listServiceProfiles(limit=99999)
        self.serviceProfiles = {}
        for profile in serviceProfilesList:
            self.serviceProfiles[profile.id] = profile

        # build list of available organizations at the network server
        organizationsList = self.listOrganizations(limit=99999)
        self.organizations = {}
        for organization in organizationsList:
            self.organizations[organization.id] = organization

        # build list of available network server instances at the server
        networkServersList = self.listNetworkServers(limit=99999)
        self.networkServers = {}
        for ns in networkServersList:
            self.networkServers[ns.id] = ns

        # build list of available gateway profiles at the network server
        gwProfilesList = self.listGatewayProfiles(limit=99999)
        self.gatewayProfiles = {}
        for gwProfile in gwProfilesList:
            self.gatewayProfiles[gwProfile.id] = gwProfile

        # build list of available gateways at the network server
        gwsList = self.listGateways(limit=99999)
        self.gateways = {}
        for gw in gwsList:
            self.gateways[gw.id] = gw


        # start MQTT reception
        def loop():
            client.loop_forever()

        self.chirpstackMqttThread = threading.Thread(target=loop, args=())
        self.chirpstackMqttThread.start()
        client.connect(self.mqttServerURL.split("://")[-1], self.mqttServerPort, keepalive=keepalive)

    def provCheck(self, deveui):
        if len(self.filter) > 0:
            if not (deveui in self.filter):
                raise Exception("Fatal internal error")

    def getJwt(self, user, password):
        req = {}
        req['email'] = user
        req['password'] = password

        headers = {}
        headers['Content-Type'] = 'application/json'
        headers['Accept'] = 'application/json'

        url = self.gRPCURL + '/api/internal/login'
        resp = requests.post(url, data = json.dumps(req), headers = headers, verify = False)
        if b'error' in resp.content:
            #import pdb;pdb.set_trace()
            raise Exception('Error', str(resp) + str(resp.content))

        ans = json.loads(resp.content)
        return ans["jwt"]

    def listDevices(self, limit=1000, applicationID = -1):
        self.renewToken()
        client = api.DeviceServiceStub(self.channel)
        # Construct request.
        req = api.ListDeviceRequest()
        req.limit = limit
        if applicationID != -1:
            req.application_id = applicationID
        resp = client.List(req, metadata=self.auth_token)
        return resp.result

    def getDeviceByDeveui(self, deveui):
        self.renewToken()
        client = api.DeviceServiceStub(self.channel)
        # Construct request.
        req = api.GetDeviceRequest()
        req.dev_eui = deveui
        resp = client.Get(req, metadata=self.auth_token)
        return resp.device

    def getDevaddrByDeveui(self, deveui):
        self.renewToken()
        client = api.DeviceServiceStub(self.channel)

        req = api.GetDeviceActivationRequest()
        req.dev_eui = deveui
        resp = client.GetActivation(req, metadata=self.auth_token)
        return resp.device_activation.dev_addr

    def listDeviceProfiles(self, limit=1000):
        self.renewToken()
        client = api.DeviceProfileServiceStub(self.channel)
        # Construct request.
        req = api.ListDeviceProfileRequest()
        req.limit = limit
        resp = client.List(req, metadata=self.auth_token)
        return resp.result

    def getDeviceProfileByName(self, name):
        deviceProfilesList = self.listDeviceProfiles(limit=99999)
        for profile in deviceProfilesList:
            if profile.name == name:
                return profile
        return None

    def createDeviceProfile(self, name, organization_id, network_server_id):
        self.renewToken()
        client = api.DeviceProfileServiceStub(self.channel)
        # Construct request.
        req = api.CreateDeviceProfileRequest()
        req.device_profile.organization_id = organization_id
        req.device_profile.network_server_id = network_server_id
        req.device_profile.name = name

        # hardcoded settings, could be parametrized using config.py, but 
        # for now ok to hardcode it here...
        req.device_profile.supports_class_b = False
        req.device_profile.supports_class_c = True
        req.device_profile.class_c_timeout = 60
        req.device_profile.mac_version = "1.0.3"
        req.device_profile.reg_params_revision = "A"
        req.device_profile.uplink_interval.seconds = 3600

        req.device_profile.max_eirp = 14
        req.device_profile.max_duty_cycle = 0 # ?
        req.device_profile.supports_join = True # OTAA is True, ABP is False
        req.device_profile.rf_region = "EU868"
        req.device_profile.supports_32bit_f_cnt = False

        # cannot assign... req.device_profile.uplink_interval = "1200s"
        req.device_profile.adr_algorithm_id = "default"

        client.Create(req, metadata = self.auth_token)
        # on error raises exception...

    def listApplications(self, limit=1000):
        self.renewToken()
        client = api.ApplicationServiceStub(self.channel)
        # Construct request.
        req = api.ListApplicationRequest()
        req.limit = limit
        resp = client.List(req, metadata=self.auth_token)
        return resp.result

    def getApplicationByName(self, name):
        applicationsList = self.listApplications(limit=99999)
        for application in applicationsList:
            if application.name == name:
                return application
        return None

    def createApplication(self, name, service_profile_id, organization_id):
        self.renewToken()
        client = api.ApplicationServiceStub(self.channel)
        # Construct request.
        req = api.CreateApplicationRequest()
        req.application.name = name
        req.application.organization_id = organization_id
        req.application.service_profile_id = service_profile_id
        client.Create(req, metadata = self.auth_token)
        # on error raises exception...


    def listServiceProfiles(self, limit=1000):
        self.renewToken()
        client = api.ServiceProfileServiceStub(self.channel)
        # Construct request.
        req = api.ListServiceProfileRequest()
        req.limit = limit
        resp = client.List(req, metadata=self.auth_token)
        return resp.result

    def getServiceProfileByName(self, name):
        serviceProfilesList = self.listServiceProfiles(limit=99999)
        for profile in serviceProfilesList:
            if profile.name == name:
                return profile
        return None

    def createServiceProfile(self, name, organization_id, network_server_id):
        self.renewToken()
        client = api.ServiceProfileServiceStub(self.channel)
        # Construct request.
        req = api.CreateServiceProfileRequest()
        req.service_profile.network_server_id = network_server_id
        req.service_profile.name = name
        req.service_profile.organization_id = organization_id
        req.service_profile.dev_status_req_freq = 2 # ask twice a day for statusRequest
        req.service_profile.report_dev_status_margin = True
        req.service_profile.dr_min = 0
        req.service_profile.dr_max = 5
     
        client.Create(req, metadata = self.auth_token)
        # on error raises exception...


    def listOrganizations(self, limit=1000):
        self.renewToken()
        client = api.OrganizationServiceStub(self.channel)
        # Construct request.
        req = api.ListOrganizationRequest()
        req.limit = limit
        resp = client.List(req, metadata=self.auth_token)
        return resp.result

    def getOrganizationByName(self, name):
        organizationsList = self.listOrganizations(limit=99999)
        for organization in organizationsList:
            if organization.name == name:
                return organization
        return None

    def createOrganization(self, name, can_have_gateways = True):
        self.renewToken()
        client = api.OrganizationServiceStub(self.channel)
        # Construct request.
        req = api.CreateOrganizationRequest()
        req.organization.name = name
        req.organization.display_name = name
        req.organization.can_have_gateways = can_have_gateways 
        client.Create(req, metadata = self.auth_token)
        # on error raises exception...


    def listNetworkServers(self, limit=1000):
        self.renewToken()
        client = api.NetworkServerServiceStub(self.channel)
        # Construct request.
        req = api.ListNetworkServerRequest()
        req.limit = limit
        resp = client.List(req, metadata=self.auth_token)
        return resp.result

    def getNetworkServerByServer(self, server):
        networkServerList = self.listNetworkServers(limit=99999)
        for ns in networkServerList:
            if ns.server == server:
                return ns
        return None

    def createNetworkServer(self, name, server = "chirpstack-network-server:8000"):
        self.renewToken()
        client = api.NetworkServerServiceStub(self.channel)
        # Construct request.
        req = api.CreateNetworkServerRequest()
        req.network_server.name = name
        req.network_server.server = server
        client.Create(req, metadata = self.auth_token)
        # on error raises exception...

    def registerDevice(self, deveui, identification, description, application_id=-1, device_profile_id = ""):
        self.renewToken()
        client = api.DeviceServiceStub(self.channel)
        req = api.CreateDeviceRequest()

        # if not specified, use the same as last
        try:
            default_application_id = self.devices[list(self.devices.keys())[-1]]["info"].application_id
        except:
            default_application_id = 1
        if application_id == -1:
            req.device.application_id = default_application_id
        else:
            req.device.application_id = application_id

        try:
            default_device_profile_id = self.deviceProfiles[list(self.deviceProfiles.keys())[-1]].id
        except:
            default_device_profile_id = ""

        if device_profile_id == '':
            req.device.device_profile_id = default_device_profile_id
        else:
            req.device.device_profile_id = device_profile_id

        req.device.is_disabled = False
        req.device.reference_altitude = 0
        req.device.skip_f_cnt_check = False
        req.device.dev_eui = deveui
        req.device.description = description
        req.device.name = identification
        
        # on error raises exception...
        client.Create(req, metadata=self.auth_token)

    def setDeviceAppKey(self, deveui, appkey):
        self.renewToken()
        client = api.DeviceServiceStub(self.channel)
        req = api.CreateDeviceKeysRequest()
        
        req.device_keys.dev_eui = deveui
        req.device_keys.app_key = appkey
        req.device_keys.gen_app_key = appkey
        req.device_keys.nwk_key = appkey

        # on error raises exception...
        client.CreateKeys(req, metadata=self.auth_token)

    def getDeviceAppKey(self, deveui):
        self.renewToken()
        client = api.DeviceServiceStub(self.channel)
        req = api.GetDeviceKeysRequest()

        req.dev_eui = deveui
        resp = client.GetKeys(req, metadata=self.auth_token)
        return resp.device_keys.app_key

    def unregisterDevice(self, deveui):
        self.renewToken()
        client = api.DeviceServiceStub(self.channel)
        req = api.DeleteDeviceRequest()
        req.dev_eui = deveui
        # on error raises exception...
        client.Delete(req, metadata=self.auth_token)


    def listMulticastGroups(self, limit=1000):
        self.renewToken()
        client = api.MulticastGroupServiceStub(self.channel)
        # Construct request.
        req = api.ListMulticastGroupRequest()
        req.limit = limit
        resp = client.List(req, metadata=self.auth_token)
        return resp.result

    def getMulticastGroupByName(self, name):
        multicastGroupsList = self.listMulticastGroups(limit=99999)
        for mcastGroup in multicastGroupsList:
            if mcastGroup.name == name:
                return mcastGroup
        return None

    def createMulticastGroup(self, name, mc_addr, mc_app_s_key, mc_nwk_s_key, application_id, dr = 0, f_cnt = 0, frequency = 869525000):
        self.renewToken()
        client = api.MulticastGroupServiceStub(self.channel)
        # Construct request.
        req = api.CreateMulticastGroupRequest()
        req.multicast_group.name = name
        req.multicast_group.application_id = application_id
        req.multicast_group.mc_addr = mc_addr
        req.multicast_group.mc_app_s_key = mc_app_s_key
        req.multicast_group.mc_nwk_s_key = mc_nwk_s_key
        req.multicast_group.dr = dr
        req.multicast_group.f_cnt = f_cnt
        req.multicast_group.frequency = frequency
        client.Create(req, metadata = self.auth_token)
        # on error raises exception...

    def deleteMulticastGroup(self, multicast_group_id):
        self.renewToken()
        client = api.MulticastGroupServiceStub(self.channel)
        # Construct request.
        req = api.DeleteMulticastGroupRequest()
        req.id = multicast_group_id
        client.Delete(req, metadata = self.auth_token)
        self.log(f"Delete multicast group {multicast_group_id}")

    def addDeviceToMulticastGroup(self, dev_eui, multicast_group_id):
        self.renewToken()
        client = api.MulticastGroupServiceStub(self.channel)
        # Construct request.
        req = api.AddDeviceToMulticastGroupRequest()
        req.dev_eui = dev_eui
        req.multicast_group_id = multicast_group_id
        client.AddDevice(req, metadata = self.auth_token)
        self.log(f"Add device to multicast group, {dev_eui} to {multicast_group_id}")
        # on error raises exception...


    def removeDeviceFromMulticastGroup(self, dev_eui, multicast_group_id):
        self.renewToken()
        client = api.MulticastGroupServiceStub(self.channel)
        # Construct request.
        req = api.RemoveDeviceFromMulticastGroupRequest()
        req.dev_eui = dev_eui
        req.multicast_group_id = multicast_group_id
        client.RemoveDevice(req, metadata = self.auth_token)
        self.log(f"Remove device from multicast group, {dev_eui} from {multicast_group_id}")
        # on error raises exception...

    def sendMulticast(self, multicast_group_id, data, port = 10):
        self.log(f"Multicast downlink [{multicast_group_id} / port {port}]: {''.join('%02X ' % x for x in data)}")

        self.renewToken()
        
        client = api.MulticastGroupServiceStub(self.channel)
        # Construct request.
        req = api.EnqueueMulticastQueueItemRequest()
        req.multicast_queue_item.data = data
        req.multicast_queue_item.multicast_group_id = multicast_group_id
        req.multicast_queue_item.f_port = port
        resp = client.Enqueue(req, metadata=self.auth_token)
        self.log("... success")
        return resp

    def getGroupFcnt(self, multicast_group_id):
        self.renewToken()
        
        client = api.MulticastGroupServiceStub(self.channel)
        # Construct request.
        req = api.GetMulticastGroupRequest()
        req.id = multicast_group_id
        resp = client.Get(req, metadata=self.auth_token)
        return resp



    def listGatewayProfiles(self, limit=1000):
        self.renewToken()
        client = api.GatewayProfileServiceStub(self.channel)
        # Construct request.
        req = api.ListGatewayProfilesRequest()
        req.limit = limit
        resp = client.List(req, metadata=self.auth_token)
        return resp.result

    def getGatewayProfileByName(self, name):
        gwProfilesList = self.listGatewayProfiles(limit=99999)
        for profile in gwProfilesList:
            if profile.name == name:
                return profile
        return None

    def createGatewayProfile(self, name, network_server_id, channelsList, extraChannelsList, gw_stats_interval = 30):
        self.renewToken()
        client = api.GatewayProfileServiceStub(self.channel)
        # Construct request.
        req = api.CreateGatewayProfileRequest()
        req.gateway_profile.network_server_id = network_server_id
        req.gateway_profile.name = name
        req.gateway_profile.channels.extend(channelsList)
        req.gateway_profile.stats_interval.seconds = gw_stats_interval
        ecs = []
        for ec in extraChannelsList:
            ecObj = api.GatewayProfileExtraChannel()
            
            for k in ec.keys():
                if k == "modulation":
                    if ec[k] in ["lora", "LORA", "Lora", "LoRa"]:
                        setattr(ecObj, k, chirpstack_api.common.LORA)
                    elif ec[k] in ["fsk", "FSK"]:
                        setattr(ecObj, k, chirpstack_api.common.FSK)
                    else:
                        raise Exception(f"Unknown modulation {ec[k]}")
                elif k == "spreading_factors":
                    ecObj.spreading_factors.extend(ec[k])
                else:
                    setattr(ecObj, k, ec[k])
            ecs.append(ecObj)
            
        try:
            req.gateway_profile.extra_channels.extend(ecs)
            client.Create(req, metadata = self.auth_token)
            # on error raises exception...
        except Exception as e:
            print(e)
            print(traceback.format_exc())


    def listGateways(self, limit=1000):
        self.renewToken()
        client = api.GatewayServiceStub(self.channel)
        # Construct request.
        req = api.ListGatewayRequest()
        req.limit = limit
        resp = client.List(req, metadata=self.auth_token)
        return resp.result

    def getGatewayByName(self, name):
        gwList = self.listGateways(limit=99999)
        for gw in gwList:
            if gw.name == name:
                return gw
        return None

    def createGateway(self, name, description, latitude, longitude, altitude, organization_id, network_server_id, service_profile_id, gateway_profile_id, gweui):
        self.renewToken()
        client = api.GatewayServiceStub(self.channel)
        # Construct request.
        req = api.CreateGatewayRequest()
        req.gateway.network_server_id = network_server_id
        req.gateway.name = name
        req.gateway.description = description
        req.gateway.organization_id = organization_id
        req.gateway.network_server_id = network_server_id
        req.gateway.service_profile_id = service_profile_id
        req.gateway.gateway_profile_id = gateway_profile_id
        req.gateway.discovery_enabled = True
        req.gateway.location.altitude = altitude
        req.gateway.location.latitude = latitude
        req.gateway.location.longitude = longitude
        req.gateway.id = gweui
        client.Create(req, metadata = self.auth_token)
        # on error raises exception...

    def updateGateway(self, name, description, latitude, longitude, altitude):
        self.renewToken()
        client = api.GatewayServiceStub(self.channel)

        # re-build list of available gateways at the network server
        gwsList = self.listGateways(limit=99999)
        self.gateways = {}
        for gw in gwsList:
            self.gateways[gw.id] = gw

        id = ""
        for gw in self.gateways:
            if self.gateways[gw].name == name:
                id = gw
                break
        if id == "":
            print(f"Could not update gateway {name}, not found!")
            return
        req = api.GetGatewayRequest()
        req.id = id
        ans = client.Get(req, metadata = self.auth_token)

        # Construct request.
        req = api.UpdateGatewayRequest()
        req.gateway.network_server_id = ans.gateway.network_server_id
        req.gateway.name = name
        req.gateway.description = description
        req.gateway.organization_id = ans.gateway.organization_id
        req.gateway.network_server_id = ans.gateway.network_server_id
        req.gateway.service_profile_id = ans.gateway.service_profile_id
        req.gateway.gateway_profile_id = ans.gateway.gateway_profile_id
        req.gateway.discovery_enabled = True
        req.gateway.location.altitude = altitude
        req.gateway.location.latitude = latitude
        req.gateway.location.longitude = longitude
        req.gateway.id = id
        client.Update(req, metadata = self.auth_token)
        # on error raises exception...


    def deleteGateway(self, name):
        self.renewToken()
        client = api.GatewayServiceStub(self.channel)
        gwToDelete = self.getGatewayByName(name)
        # Construct request.
        req = api.DeleteGatewayRequest()
        req.id = gwToDelete.id
        client.Delete(req, metadata = self.auth_token)

    def send(self, deveui, data, port = 10, confirmed = False):
        self.log(f"Unicast downlink [{deveui} / port {port}]: {''.join('%02X ' % x for x in data)}")
        self.renewToken()
        deveui = deveui.lower()
        self.provCheck(deveui)
        client = api.DeviceQueueServiceStub(self.channel)
        # Construct request.
        req = api.EnqueueDeviceQueueItemRequest()
        req.device_queue_item.confirmed = confirmed
        req.device_queue_item.data = data
        req.device_queue_item.dev_eui = deveui
        req.device_queue_item.f_port = port
        resp = client.Enqueue(req, metadata=self.auth_token)
        self.log("... success")
        return resp

    def receive(self, deveui, timeout=None):
        deveui = deveui.lower()
        if deveui in self.devices:
            return self.devices[deveui]["queue"].get(timeout=timeout)
        else:
            raise Exception(f"Unknown device {deveui}!")

    def clearReceiveQueue(self, deveui):
        deveui = deveui.lower()
        if deveui in self.devices:
            return self.devices[deveui]["queue"].clear()
        else:
            raise Exception(f"Unknown device {deveui}!")

    def registerReceiveCallback(self, deveui, callback = None, userdata = None):
        deveui = deveui.lower()
        self.provCheck(deveui)
        if not (deveui in self.devices):
            newDevice = self.getDeviceByDeveui(deveui)
            extension = {}
            extension[deveui] = {}
            extension[deveui]["info"] = newDevice
            extension[deveui]["queue"] = queue.Queue()
            self.devices.update(extension)

        if deveui in self.devices:
            if callback == None:
                self.devices[deveui].pop('callback', None)
            else:
                self.devices[deveui]["callback"] = callback

            if userdata == None:
                self.devices[deveui].pop('userdata', None)
            else:
                self.devices[deveui]["userdata"] = userdata

        else:
            raise Exception(f"Unknown device {deveui}!")

    def registerJoinCallback(self, deveui, callback = None, userdata = None):
        deveui = deveui.lower()
        self.provCheck(deveui)
        if not (deveui in self.devices):
            newDevice = self.getDeviceByDeveui(deveui)
            extension = {}
            extension[deveui] = {}
            extension[deveui]["info"] = newDevice
            extension[deveui]["queue"] = queue.Queue()
            self.devices.update(extension)

        if deveui in self.devices:
            if callback == None:
                self.devices[deveui].pop('join_callback', None)
            else:
                self.devices[deveui]["join_callback"] = callback

            if userdata == None:
                self.devices[deveui].pop('join_userdata', None)
            else:
                self.devices[deveui]["join_userdata"] = userdata

        else:
            raise Exception(f"Unknown device {deveui}!")

    def registerJoinRequestCallback(self, deveui, callback = None, userdata = None):
        deveui = deveui.lower()
        self.provCheck(deveui)
        if not (deveui in self.devices):
            newDevice = self.getDeviceByDeveui(deveui)
            extension = {}
            extension[deveui] = {}
            extension[deveui]["info"] = newDevice
            extension[deveui]["queue"] = queue.Queue()
            self.devices.update(extension)

        if deveui in self.devices:
            if callback == None:
                self.devices[deveui].pop('join_req_callback', None)
            else:
                self.devices[deveui]["join_req_callback"] = callback

            if userdata == None:
                self.devices[deveui].pop('join_req_userdata', None)
            else:
                self.devices[deveui]["join_req_userdata"] = userdata

        else:
            raise Exception(f"Unknown device {deveui}!")



if __name__ == "__main__":
    cc = chirpstackConnector( mqttServerURL="http://127.0.0.1", mqttServerPort=1883, useWebsockets = True, wsLogin="admin:admin", wsPath="/mqtt/", gRPCURL = 'http://127.0.0.1', gRPCUser = "admin", gRPCPassword = "nstest")

    print(cc.devices)
    while True:
        rxed = cc.receive("2c6a6ffffe102b93")
        print(rxed)
