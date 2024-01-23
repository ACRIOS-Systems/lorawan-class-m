#include "radio.h"


PacketParams_t packetParams;  // TODO: this is lazy
SleepParams_t sleepParams;
const RadioLoRaBandwidths_t Bandwidths[] = { LORA_BW_125, LORA_BW_250, LORA_BW_500 };
static RadioEvents_t* RadioEvents;
PacketStatus_t packetStatus;
RadioLoRaCadSymbols_t cadSymbols;
RadioCadExitModes_t cadMode;
ModulationParams_t modulationParams;

uint8_t rxBuffer[5000];
uint8_t rxSize;


void RadioInit(RadioEvents_t* events, uint32_t radio_frequency, uint16_t preamble_len, bool header_type, 
                uint8_t payload_len, bool crc_state, bool iq_state, uint8_t spreading_factor, uint8_t bandwidth, uint8_t coding_rate, uint8_t LDR, uint8_t TX_power)
{
  RadioEvents = events;
    // Initialize the hardware (SPI bus, TCXO control, RF switch)
  SUBGRF_Init(RadioOnDioIrq);

  // Use DCDC converter if `DCDC_ENABLE` is defined in radio_conf.h
  // "By default, the SMPS clock detection is disabled and must be enabled before enabling the SMPS." (6.1 in RM0453)
  SUBGRF_WriteRegister(SUBGHZ_SMPSC0R, (SUBGRF_ReadRegister(SUBGHZ_SMPSC0R) | SMPS_CLK_DET_ENABLE));
  SUBGRF_SetRegulatorMode();


  // Use the whole 256-byte buffer for both TX and RX
  SUBGRF_SetBufferBaseAddress(0x00, 0x00);

  SUBGRF_SetRfFrequency(radio_frequency);
  SUBGRF_SetRfTxPower(TX_power);
  SUBGRF_SetStopRxTimerOnPreambleDetect(true);

  SUBGRF_SetPacketType(PACKET_TYPE_LORA);

  //SUBGRF_WriteRegister( REG_LR_SYNCWORD, ( LORA_MAC_PRIVATE_SYNCWORD >> 8 ) & 0xFF );
  //SUBGRF_WriteRegister( REG_LR_SYNCWORD + 1, LORA_MAC_PRIVATE_SYNCWORD & 0xFF );

  SUBGRF_WriteRegister( REG_LR_SYNCWORD, ( LORA_MAC_PUBLIC_SYNCWORD >> 8 ) & 0xFF );
  SUBGRF_WriteRegister( REG_LR_SYNCWORD + 1, LORA_MAC_PUBLIC_SYNCWORD & 0xFF );


  modulationParams.PacketType = PACKET_TYPE_LORA;
  modulationParams.Params.LoRa.Bandwidth = Bandwidths[bandwidth];
  modulationParams.Params.LoRa.CodingRate = (RadioLoRaCodingRates_t)coding_rate;
  modulationParams.Params.LoRa.LowDatarateOptimize = LDR;
  modulationParams.Params.LoRa.SpreadingFactor = (RadioLoRaSpreadingFactors_t)spreading_factor;
  SUBGRF_SetModulationParams(&modulationParams);

  packetParams.PacketType = PACKET_TYPE_LORA;
  packetParams.Params.LoRa.CrcMode = crc_state;
  packetParams.Params.LoRa.HeaderType = header_type;
  packetParams.Params.LoRa.InvertIQ = iq_state;
  packetParams.Params.LoRa.PayloadLength = payload_len;
  packetParams.Params.LoRa.PreambleLength = preamble_len;
  SUBGRF_SetPacketParams(&packetParams);

  //SUBGRF_SetRxDutyCycle(4200, 1);
  //SUBGRF_SetLoRaSymbNumTimeout(LORA_SYMBOL_TIMEOUT);

  // WORKAROUND - Optimizing the Inverted IQ Operation, see DS_SX1261-2_V1.2 datasheet chapter 15.4
  // RegIqPolaritySetup @address 0x0736
  SUBGRF_WriteRegister( 0x0736, SUBGRF_ReadRegister( 0x0736 ) | ( 1 << 2 ) );
}


void RadioSleep(void)
{
  sleepParams.Fields.WakeUpRTC = 1;
  SUBGRF_SetSleep(sleepParams);
}

void RadioStandby(void)
{
  SUBGRF_SetStandby(STDBY_RC);
}

void RadioSend( uint8_t* buffer, uint8_t payload_len )
{  
  //SUBGRF_SetDioIrqParams( IRQ_RADIO_ALL, IRQ_RADIO_ALL, IRQ_RADIO_NONE, IRQ_RADIO_NONE );
  SUBGRF_SetDioIrqParams( IRQ_TX_DONE | IRQ_RX_TX_TIMEOUT,
                          IRQ_TX_DONE | IRQ_RX_TX_TIMEOUT,
                          IRQ_RADIO_NONE,
                          IRQ_RADIO_NONE );
  SUBGRF_SetSwitch(RFO_LP, RFSWITCH_TX);
  SUBGRF_WriteRegister(0x0889, (SUBGRF_ReadRegister(0x0889) | 0x04));
  packetParams.Params.LoRa.PayloadLength = payload_len;
  SUBGRF_SetPacketParams(&packetParams);
  SUBGRF_SendPayload(buffer, payload_len, 0);
}

void RadioRx( uint32_t RX_timeout, uint8_t payload_len)
{
  //SUBGRF_SetDioIrqParams( IRQ_RADIO_ALL, IRQ_RADIO_ALL, IRQ_RADIO_NONE, IRQ_RADIO_NONE );
  SUBGRF_SetDioIrqParams( IRQ_RX_DONE | IRQ_RX_TX_TIMEOUT | IRQ_CRC_ERROR | IRQ_HEADER_ERROR,
                          IRQ_RX_DONE | IRQ_RX_TX_TIMEOUT | IRQ_CRC_ERROR | IRQ_HEADER_ERROR,
                          IRQ_RADIO_NONE,
                          IRQ_RADIO_NONE );
  SUBGRF_SetSwitch(RFO_LP, RFSWITCH_RX);
  packetParams.Params.LoRa.PayloadLength = payload_len;
  SUBGRF_SetPacketParams(&packetParams);
  SUBGRF_SetRx(RX_timeout);
}

void RadioStartCad( uint32_t CADtimeout )
{
  SUBGRF_SetDioIrqParams( IRQ_CAD_DETECTED | IRQ_CAD_CLEAR,
                          IRQ_CAD_DETECTED | IRQ_CAD_CLEAR,
                          IRQ_RADIO_NONE,
                          IRQ_RADIO_NONE );

  SUBGRF_SetCadParams(LORA_CAD_04_SYMBOL, 24, 10, LORA_CAD_ONLY, CADtimeout );
  SUBGRF_SetCad();
}

const struct Radio_s Radio = {
  RadioInit,
  RadioSend,
  RadioRx,
  RadioStandby,
  RadioSleep,
  RadioStartCad
};


void RadioOnDioIrq(RadioIrqMasks_t radioIrq)
{
  switch (radioIrq)
  {
    case IRQ_TX_DONE:
      RadioEvents->TxDone();
      break;
    case IRQ_RX_DONE:

      SUBGRF_WriteRegister(0x0920, 0x00);
      SUBGRF_WriteRegister(0x0944, (SUBGRF_ReadRegister(0x0944) | 0x02));

      SUBGRF_GetPayload(rxBuffer, &rxSize, 0xFF);
      SUBGRF_GetPacketStatus(&packetStatus);
      RadioEvents->RxDone(rxBuffer, rxSize);

      break;
    case IRQ_RX_TX_TIMEOUT:
      if (SUBGRF_GetOperatingMode() == MODE_TX)
      {
        RadioEvents->TxTimeout();
      }
      else if (SUBGRF_GetOperatingMode() == MODE_RX)
      {
        RadioEvents->RxTimeout();
      }
      break;
    case IRQ_CRC_ERROR:
      RadioEvents->RxError();
      break;
    case IRQ_CAD_DETECTED:
      RadioEvents->CADDetected();
      //SUBGRF_SetCad();
      break;

    case IRQ_CAD_CLEAR:
      RadioEvents->CADTimeout();
      //SUBGRF_SetCad();
      break;
    
    case IRQ_PREAMBLE_DETECTED:
      RadioEvents->PreambleDetected();
      break;

        
    case IRQ_HEADER_VALID:
      RadioEvents->HeaderValid();
      break;

        
    case IRQ_HEADER_ERROR:
      RadioEvents->HeaderError();
      break;

    default:
      break;
  }
}
