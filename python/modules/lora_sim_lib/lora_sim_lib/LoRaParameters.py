################################################################################################
class LoRaParameters: # Parameters of LoRa modulation for both packet transmission and reception
    
    def __init__(self, frequency, bandwidth_kHz, spreading_factor, coding_rate, iq_inverted, low_data_rate, implicit_header, crc_en, preamble_length):
        #assert (12 >= spreading_factor >= 7), "SF needs to be between <7, 12>"
        #assert (8 >= coding_rate >= 5), "CR needs to be between (4/5, 4/8) -> <5, 8>"

        self.frequency = frequency
        self.bandwidth_kHz = bandwidth_kHz
        self.spreading_factor = spreading_factor
        self.coding_rate = coding_rate
        self.iq_inverted = iq_inverted
        self.low_data_rate = low_data_rate
        self.implicit_header = implicit_header
        self.crc_en = crc_en
        self.preamble_length = preamble_length

    def __str__(self):
        return 'SF{}; BW{}; FQ{}'.format(int(self.spreading_factor), int(self.bandwidth_kHz), int(self.freq))

    def canHear(self, param) -> bool:
        assert isinstance(param, LoRaParameters)
        return(
            (param.frequency == self.frequency) and
            (param.bandwidth_kHz == self.bandwidth_kHz) and
            (param.spreading_factor == self.spreading_factor) and
            (param.iq_inverted == self.iq_inverted)
        )

####################################################################################################
class PacketParameters(LoRaParameters): # Parameters for packet transmission, extends LoRaParameters

    def __init__(self, frequency, bandwidth_kHz, spreading_factor, coding_rate, iq_inverted, low_data_rate, implicit_header, crc_en, preamble_length, power):
        super().__init__(frequency, bandwidth_kHz, spreading_factor, coding_rate, iq_inverted, low_data_rate, implicit_header, crc_en, preamble_length)
        self.power = power

    def toDict(self) -> dict:
        par = {}
        par["frequency"]        = self.frequency            
        par["bandwidth_kHz"]    = self.bandwidth_kHz        
        par["spreading_factor"] = self.spreading_factor     
        par["coding_rate"]      = self.coding_rate          
        par["iq_inverted"]      = self.iq_inverted          
        par["low_data_rate"]    = self.low_data_rate        
        par["implicit_header"]  = self.implicit_header      
        par["crc_en"]           = self.crc_en               
        par["preamble_length"]  = self.preamble_length      
        par["power"]            = self.power                
        return par
        

#############################################################################################
class RxParameters(LoRaParameters): # Parameters for packet reception, extends LoRaParameters

    def __init__(self, frequency, bandwidth_kHz, spreading_factor, coding_rate, iq_inverted, low_data_rate, implicit_header, crc_en, preamble_length, rx_timeout):
        super().__init__(frequency, bandwidth_kHz, spreading_factor, coding_rate, iq_inverted, low_data_rate, implicit_header, crc_en, preamble_length)
        self.rx_timeout = rx_timeout