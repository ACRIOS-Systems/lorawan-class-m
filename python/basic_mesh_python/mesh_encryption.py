from lorawan_parser.lorawan_cipher import lorawan_aes128_cmac, lorawan_get_keys, lorawan_aes128_encrypt, lorawan_decrypt
from lorawan_parser.lorawan_parser import parse_join_accept

def calculateKeys(AppKey, DevNonce, JoinNonce, NetID):
    """
    calculateKeys(): calculate NwkSkey and AppSkey from AppKey, DevNonce, JoinNonce and NetID
    """
    appkey = bytearray.fromhex(AppKey)
    devnonce = bytearray.fromhex(DevNonce)
    joinnonce = bytearray.fromhex(JoinNonce)
    netid = bytearray.fromhex(NetID)

    #devnonce = bytearray(DevNonce.to_bytes(2, byteorder='big'))
    #joinnonce = bytearray(JoinNonce.to_bytes(3, byteorder='big'))
    #netid = bytearray(NetID.to_bytes(3, byteorder='big'))
    keys = lorawan_get_keys(appkey, devnonce, joinnonce, netid)
    return keys

def getNwkSkey(AppKey:str, DevNonce:str, JoinNonce:str, NetID:str):
    """
    getNwkSkey(): calculate NwkSkey from AppKey, DevNonce, JoinNonce and NetID
    """
    keys = calculateKeys(AppKey, DevNonce, JoinNonce, NetID)
    NwkSkey = {keys["nwkskey"].hex()}
    return NwkSkey

def getAppSkey(AppKey:str, DevNonce:str, JoinNonce:str, NetID:str):
    """
    getAppSkey(): calculate AppSkey from AppKey, DevNonce, JoinNonce and NetID
    """
    keys = calculateKeys(AppKey, DevNonce, JoinNonce, NetID)
    AppSkey = {keys["appskey"].hex()}
    return AppSkey

def calculateMICRegReq(appkey : str, JoinEUI: int, DevEUI : int, DevNonce: int):
    """
    calculateMIC(): calculate MIC from MHDR, JoinEUI, DevEUI and DevNonce
    """
    key = bytearray.fromhex(appkey)
    MHDR = "000000"

    deviceEUI = DevEUI.to_bytes(8, 'big')
    deviceEUI = deviceEUI.hex()
    joinEUI = JoinEUI.to_bytes(8, 'big')
    joinEUI = joinEUI.hex()
    devnonce = DevNonce.to_bytes(2, 'big')
    devnonce = devnonce.hex()
 
    data = bytearray.fromhex(MHDR + joinEUI + deviceEUI + devnonce)
    cmac = lorawan_aes128_cmac(key, data)
    MIC = cmac['mic'].hex()
    return MIC

def calculateMICRegAck(appkey:str, AppNonce:int, NetID:int, DevAddr:int):
    """
    calculateMIC(): calculate MIC for a RegAck
    """
    key = bytearray.fromhex(appkey)
    MHDR = "000000"
    padding = "000000"

    appNonce = AppNonce.to_bytes(3, 'big')
    appNonce = appNonce.hex()
    netid = NetID.to_bytes(3, 'big')
    netid = netid.hex()
    devaddr = DevAddr.to_bytes(4, 'big')
    devaddr = devaddr.hex()

    data = bytearray.fromhex(MHDR + appNonce + netid + devaddr + padding)
    cmac = lorawan_aes128_cmac(key, data)
    MIC = cmac['mic'].hex()
    return MIC

def calculateMsgMIC (key:str, msg: str):
    """
    calculateMsgMIC(): calculate MIC to append to a message
    """
    #key = bytearray.fromhex(key)
    # create a bytearray from hex message
    #data = bytearray.fromhex(msg)
    # calculate the CMAC
    cmac = lorawan_aes128_cmac(bytearray.fromhex(key), bytearray.fromhex(msg))
    # print cmac in hex format
    MIC = cmac['mic'].hex()
    return MIC

def LoRaEncrypt(key:str, msg:bytes):
    """
    LoRaEncrypt(): Encrypt a message with a key
    """
    key = bytearray.fromhex(key)
    return lorawan_aes128_encrypt(key, msg)

def LoRaDecrypt(key:str, msg:bytes):
    """
    LoRaDecrypt(): Decrypt a message with a key
    """
    key = bytearray.fromhex(key)
    return lorawan_decrypt(key, msg)
