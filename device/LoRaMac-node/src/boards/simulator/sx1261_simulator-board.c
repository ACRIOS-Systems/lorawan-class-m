/*!
 * \file      sx1261mbxbas-board.c
 *
 * \brief     Target board SX1261MBXBAS shield driver implementation
 *
 * \copyright Revised BSD License, see section \ref LICENSE.
 *
 * \code
 *                ______                              _
 *               / _____)             _              | |
 *              ( (____  _____ ____ _| |_ _____  ____| |__
 *               \____ \| ___ |    (_   _) ___ |/ ___)  _ \
 *               _____) ) ____| | | || |_| ____( (___| | | |
 *              (______/|_____)_|_|_| \__)_____)\____)_| |_|
 *              (C)2013-2017 Semtech
 *
 * \endcode
 *
 * \author    Miguel Luis ( Semtech )
 *
 * \author    Gregory Cristian ( Semtech )
 */
#include <stdlib.h>
#include "utilities.h"
#include "board-config.h"
#include "board.h"
#include "delay.h"
#include "radio.h"
#include "sx126x-board.h"
#include "stdio.h"
#include "assert.h"
#include "rtc-board.h"

/*!
 * \brief Holds the internal operating mode of the radio
 */
static RadioOperatingModes_t OperatingMode;

/*!
 * Antenna switch GPIO pins objects
 */
Gpio_t AntPow;
Gpio_t DeviceSel;

void SX126xIoInit( void )
{
}

void SX126xIoIrqInit( DioIrqHandler dioIrq )
{
    GpioSetInterrupt( &SX126x.DIO1, IRQ_RISING_EDGE, IRQ_HIGH_PRIORITY, dioIrq );
}

void SX126xIoDeInit( void )
{
}

void SX126xIoDbgInit( void )
{
}

void SX126xIoTcxoInit( void )
{
    // No TCXO component available on this board design.
}

uint32_t SX126xGetBoardTcxoWakeupTime( void )
{
    return BOARD_TCXO_WAKEUP_TIME;
}

void SX126xIoRfSwitchInit( void )
{
    SX126xSetDio2AsRfSwitchCtrl( true );
}

RadioOperatingModes_t SX126xGetOperatingMode( void )
{
    return OperatingMode;
}


void SX126xSetOperatingMode( RadioOperatingModes_t mode )
{
    OperatingMode = mode;
}

void SX126xReset( void )
{
}

void SX126xWaitOnBusy( void )
{
}

void SX126xWakeup( void )
{
}

void simulatorSetNextRadioIRQin(uint32_t inms);

typedef struct
{
    const char* name;
    int value;
} valueToString_t;

valueToString_t bwToString[] = 
{
    {"500", 6}, {"250", 5}, {"125", 4}, {"62", 3},
    {"41", 10}, {"31", 2},  {"20", 9},  {"15", 1},
    {"10", 8},  {"7", 0},   {NULL, -1}
};

const char* helper_bandwidthNumberTokHz(int value)
{
    for(int i = 0; bwToString[i].name; i++)
    {
        if(bwToString[i].value == value)
        {
            return bwToString[i].name;
        }
    }
    return "-1";
}

valueToString_t crToString[] = 
{
    {"5", LORA_CR_4_5}, {"6", LORA_CR_4_6},
    {"7", LORA_CR_4_7}, {"8", LORA_CR_4_8},
    {NULL, -1}
};

const char* helper_codingRateValueToRate(int value)
{
    for(int i = 0; crToString[i].name; i++)
    {
        if(crToString[i].value == value)
        {
            return crToString[i].name;
        }
    }
    return "-1";
}

valueToString_t rampToString[] = 
{
    {"10", RADIO_RAMP_10_US}, {"20", RADIO_RAMP_20_US},
    {"40", RADIO_RAMP_40_US}, {"80", RADIO_RAMP_80_US},
    {"200", RADIO_RAMP_200_US}, {"800", RADIO_RAMP_800_US},
    {"1700", RADIO_RAMP_1700_US}, {"3400", RADIO_RAMP_3400_US},
    {NULL, -1}
};

const char* helper_rampToString(int value)
{
    for(int i = 0; rampToString[i].name; i++)
    {
        if(rampToString[i].value == value)
        {
            return rampToString[i].name;
        }
    }
    return "-1";
}

const char* helper_dataToHex(uint8_t* data, int size)
{
    static char hex[3*256+1];
    if(size > 255)
    {
        size = 255;
    }

    for(int i = 0; i < size; i++)
    {
        sprintf(&hex[3*i], "%02X:", data[i]);
    }
    hex[3*size] = '\0';
    return hex;
}

void SX126xWriteCommand( RadioCommands_t command, uint8_t *buffer, uint16_t size )
{
    extern uint32_t sim_frequency;
    extern PacketParams_t sim_packetParams;
    extern ModulationParams_t sim_modulationParams;
    extern int8_t sim_power;
    extern RadioRampTimes_t sim_rampTime;
    extern uint32_t sim_tx_timeout;    
    extern uint8_t sim_payload[];
    extern uint8_t sim_size;
    extern uint8_t sim_symbNum;
    extern uint32_t sim_rx_timeout;
    extern volatile uint64_t mtime;

    if(command == RADIO_SET_TX)
    {
        fprintf(stderr, ":TX,ts=%lu,frequency=%d,preamble_length=%d,implicit_header=%d,payload_length=%d,crc_en=%d,"\
        "iq_inverted=%d,spreading_factor=%d,bandwidth_kHz=%s,coding_rate=%s,low_data_rate=%d,"\
        "power=%d,ramp_time=%s,tx_timeout=%d,symbol_timeout=%d,size=%d,data=%s\n", mtime,
        sim_frequency, sim_packetParams.Params.LoRa.PreambleLength, sim_packetParams.Params.LoRa.HeaderType == LORA_PACKET_IMPLICIT,
        sim_packetParams.Params.LoRa.PayloadLength, sim_packetParams.Params.LoRa.CrcMode == LORA_CRC_ON,
        sim_packetParams.Params.LoRa.InvertIQ == LORA_IQ_INVERTED, sim_modulationParams.Params.LoRa.SpreadingFactor,
        helper_bandwidthNumberTokHz(sim_modulationParams.Params.LoRa.Bandwidth),
        helper_codingRateValueToRate(sim_modulationParams.Params.LoRa.CodingRate),
        sim_modulationParams.Params.LoRa.LowDatarateOptimize, sim_power, 
        helper_rampToString(sim_rampTime), sim_tx_timeout, sim_symbNum, sim_size,
        helper_dataToHex(sim_payload, sim_size));
    }
    else if(command == RADIO_SET_RX)
    {
        fprintf(stderr, ":RX,ts=%lu,frequency=%d,preamble_length=%d,implicit_header=%d,payload_length=%d,crc_en=%d,"\
        "iq_inverted=%d,spreading_factor=%d,bandwidth_kHz=%s,coding_rate=%s,low_data_rate=%d,"\
        "rx_timeout=%d,symbol_timeout=%d\n", mtime,
        sim_frequency, sim_packetParams.Params.LoRa.PreambleLength, sim_packetParams.Params.LoRa.HeaderType == LORA_PACKET_IMPLICIT,
        sim_packetParams.Params.LoRa.PayloadLength, sim_packetParams.Params.LoRa.CrcMode == LORA_CRC_ON,
        sim_packetParams.Params.LoRa.InvertIQ == LORA_IQ_INVERTED, sim_modulationParams.Params.LoRa.SpreadingFactor,
        helper_bandwidthNumberTokHz(sim_modulationParams.Params.LoRa.Bandwidth),
        helper_codingRateValueToRate(sim_modulationParams.Params.LoRa.CodingRate),
        sim_modulationParams.Params.LoRa.LowDatarateOptimize, sim_rx_timeout, sim_symbNum);
    }
    else if((command == RADIO_SET_STANDBY)||(command == RADIO_SET_SLEEP))
    {
        fprintf(stderr, ":IDLE,ts=%lu,%s\n", mtime, (command == RADIO_SET_SLEEP)?"SLEEP":"STANDBY");
    }
}

uint8_t SX126xReadCommand( RadioCommands_t command, uint8_t *buffer, uint16_t size )
{
    return 0;
}

void SX126xWriteRegisters( uint16_t address, uint8_t *buffer, uint16_t size )
{
}

void SX126xWriteRegister( uint16_t address, uint8_t value )
{
    SX126xWriteRegisters( address, &value, 1 );
}

void SX126xReadRegisters( uint16_t address, uint8_t *buffer, uint16_t size )
{
}

uint8_t SX126xReadRegister( uint16_t address )
{
    uint8_t data;
    SX126xReadRegisters( address, &data, 1 );
    return data;
}

void SX126xWriteBuffer( uint8_t offset, uint8_t *buffer, uint8_t size )
{
}

void SX126xReadBuffer( uint8_t offset, uint8_t *buffer, uint8_t size )
{
}

void SX126xSetRfTxPower( int8_t power )
{
    SX126xSetTxParams( power, RADIO_RAMP_40_US );
}

uint8_t SX126xGetDeviceId( void )
{
    return SX1261;
}

void SX126xAntSwOn( void )
{
}

void SX126xAntSwOff( void )
{
}

bool SX126xCheckRfFrequency( uint32_t frequency )
{
    // Implement check. Currently all frequencies are supported
    return true;
}

uint32_t SX126xGetDio1PinState( void )
{
    return 1;
}