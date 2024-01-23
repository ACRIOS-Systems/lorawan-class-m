/*!
 * \file      sx126x.c
 *
 * \brief     SX126x driver implementation
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
#include <string.h>
#include "utilities.h"
#include "timer.h"
#include "radio.h"
#include "delay.h"
#include "sx126x.h"
#include "sx126x-board.h"

/*!
 * \brief Internal frequency of the radio
 */
#define SX126X_XTAL_FREQ                            32000000UL

/*!
 * \brief Scaling factor used to perform fixed-point operations
 */
#define SX126X_PLL_STEP_SHIFT_AMOUNT                ( 14 )

/*!
 * \brief PLL step - scaled with SX126X_PLL_STEP_SHIFT_AMOUNT
 */
#define SX126X_PLL_STEP_SCALED                      ( SX126X_XTAL_FREQ >> ( 25 - SX126X_PLL_STEP_SHIFT_AMOUNT ) )

/*!
 * \brief Maximum value for parameter symbNum in \ref SX126xSetLoRaSymbNumTimeout
 */
#define SX126X_MAX_LORA_SYMB_NUM_TIMEOUT            248

/*!
 * \brief Radio registers definition
 */
typedef struct
{
    uint16_t      Addr;                             //!< The address of the register
    uint8_t       Value;                            //!< The value of the register
}RadioRegisters_t;

/*!
 * \brief Stores the current packet type set in the radio
 */
static RadioPacketTypes_t PacketType;

/*!
 * \brief Stores the current packet header type set in the radio
 */
static volatile RadioLoRaPacketLengthsMode_t LoRaHeaderType;

/*!
 * \brief Stores the last frequency error measured on LoRa received packet
 */
volatile uint32_t FrequencyError = 0;

/*!
 * \brief Hold the status of the Image calibration
 */
static bool ImageCalibrated = false;

/*
 * SX126x DIO IRQ callback functions prototype
 */

/*!
 * \brief DIO 0 IRQ callback
 */
void SX126xOnDioIrq( void );

/*!
 * \brief DIO 0 IRQ callback
 */
void SX126xSetPollingMode( void );

/*!
 * \brief DIO 0 IRQ callback
 */
void SX126xSetInterruptMode( void );

/*
 * \brief Process the IRQ if handled by the driver
 */
void SX126xProcessIrqs( void );

void SX126xInit( DioIrqHandler dioIrq )
{
    SX126xReset( );

    SX126xIoIrqInit( dioIrq );

    SX126xWakeup( );
    SX126xSetStandby( STDBY_RC );

    // Initialize TCXO control
    SX126xIoTcxoInit( );

    // Initialize RF switch control
    SX126xIoRfSwitchInit( );

    // Force image calibration
    ImageCalibrated = false;

    SX126xSetOperatingMode( MODE_STDBY_RC );
}

void SX126xCheckDeviceReady( void )
{
    if( ( SX126xGetOperatingMode( ) == MODE_SLEEP ) || ( SX126xGetOperatingMode( ) == MODE_RX_DC ) )
    {
        SX126xWakeup( );
        // Switch is turned off when device is in sleep mode and turned on is all other modes
        SX126xAntSwOn( );
    }
    SX126xWaitOnBusy( );
}

uint8_t sim_payload[256];
uint8_t sim_size;

void SX126xSetPayload( uint8_t *payload, uint8_t size )
{
    memcpy(sim_payload, payload, size);
    sim_size = size;
    SX126xWriteBuffer( 0x00, payload, size );
}

uint8_t SX126xGetPayload( uint8_t *buffer, uint8_t *size,  uint8_t maxSize )
{
    uint8_t offset = 0;
    SX126xReadBuffer( offset, buffer, *size );
    return 0;
}

void SX126xSendPayload( uint8_t *payload, uint8_t size, uint32_t timeout )
{
    SX126xSetPayload( payload, size );
    SX126xSetTx( timeout );
}

uint8_t SX126xSetSyncWord( uint8_t *syncWord )
{
    SX126xWriteRegisters( REG_LR_SYNCWORDBASEADDRESS, syncWord, 8 );
    return 0;
}

void SX126xSetCrcSeed( uint16_t seed )
{
    uint8_t buf[2];

    buf[0] = ( uint8_t )( ( seed >> 8 ) & 0xFF );
    buf[1] = ( uint8_t )( seed & 0xFF );

    switch( SX126xGetPacketType( ) )
    {
        case PACKET_TYPE_GFSK:
            SX126xWriteRegisters( REG_LR_CRCSEEDBASEADDR, buf, 2 );
            break;

        default:
            break;
    }
}

void SX126xSetCrcPolynomial( uint16_t polynomial )
{
    uint8_t buf[2];

    buf[0] = ( uint8_t )( ( polynomial >> 8 ) & 0xFF );
    buf[1] = ( uint8_t )( polynomial & 0xFF );

    switch( SX126xGetPacketType( ) )
    {
        case PACKET_TYPE_GFSK:
            SX126xWriteRegisters( REG_LR_CRCPOLYBASEADDR, buf, 2 );
            break;

        default:
            break;
    }
}

void SX126xSetWhiteningSeed( uint16_t seed )
{
    uint8_t regValue = 0;
    
    switch( SX126xGetPacketType( ) )
    {
        case PACKET_TYPE_GFSK:
            regValue = SX126xReadRegister( REG_LR_WHITSEEDBASEADDR_MSB ) & 0xFE;
            regValue = ( ( seed >> 8 ) & 0x01 ) | regValue;
            SX126xWriteRegister( REG_LR_WHITSEEDBASEADDR_MSB, regValue ); // only 1 bit.
            SX126xWriteRegister( REG_LR_WHITSEEDBASEADDR_LSB, ( uint8_t )seed );
            break;

        default:
            break;
    }
}

uint32_t SX126xGetRandom( void )
{
    uint32_t number = 0;
    uint8_t regAnaLna = 0;
    uint8_t regAnaMixer = 0;

    regAnaLna = SX126xReadRegister( REG_ANA_LNA );
    SX126xWriteRegister( REG_ANA_LNA, regAnaLna & ~( 1 << 0 ) );

    regAnaMixer = SX126xReadRegister( REG_ANA_MIXER );
    SX126xWriteRegister( REG_ANA_MIXER, regAnaMixer & ~( 1 << 7 ) );

    // Set radio in continuous reception
    SX126xSetRx( 0xFFFFFF ); // Rx Continuous

    SX126xReadRegisters( RANDOM_NUMBER_GENERATORBASEADDR, ( uint8_t* )&number, 4 );

    SX126xSetStandby( STDBY_RC );

    SX126xWriteRegister( REG_ANA_LNA, regAnaLna );
    SX126xWriteRegister( REG_ANA_MIXER, regAnaMixer );

    return number;
}

void SX126xSetSleep( SleepParams_t sleepConfig )
{
    SX126xAntSwOff( );

    uint8_t value = ( ( ( uint8_t )sleepConfig.Fields.WarmStart << 2 ) |
                      ( ( uint8_t )sleepConfig.Fields.Reset << 1 ) |
                      ( ( uint8_t )sleepConfig.Fields.WakeUpRTC ) );

    if( sleepConfig.Fields.WarmStart == 0 )
    {
        // Force image calibration
        ImageCalibrated = false;
    }
    SX126xWriteCommand( RADIO_SET_SLEEP, &value, 1 );
    SX126xSetOperatingMode( MODE_SLEEP );
}

void SX126xSetStandby( RadioStandbyModes_t standbyConfig )
{
    SX126xWriteCommand( RADIO_SET_STANDBY, ( uint8_t* )&standbyConfig, 1 );
    if( standbyConfig == STDBY_RC )
    {
        SX126xSetOperatingMode( MODE_STDBY_RC );
    }
    else
    {
        SX126xSetOperatingMode( MODE_STDBY_XOSC );
    }
}

void SX126xSetFs( void )
{
    SX126xWriteCommand( RADIO_SET_FS, 0, 0 );
    SX126xSetOperatingMode( MODE_FS );
}

uint32_t sim_tx_timeout = 0;
void SX126xSetTx( uint32_t timeout )
{
    uint8_t buf[3];
    sim_tx_timeout = timeout;

    SX126xSetOperatingMode( MODE_TX );

    buf[0] = ( uint8_t )( ( timeout >> 16 ) & 0xFF );
    buf[1] = ( uint8_t )( ( timeout >> 8 ) & 0xFF );
    buf[2] = ( uint8_t )( timeout & 0xFF );
    SX126xWriteCommand( RADIO_SET_TX, buf, 3 );
}

void SX126xSetRx( uint32_t timeout )
{
    uint8_t buf[3];

    SX126xSetOperatingMode( MODE_RX );

    SX126xWriteRegister( REG_RX_GAIN, 0x94 ); // default gain

    buf[0] = ( uint8_t )( ( timeout >> 16 ) & 0xFF );
    buf[1] = ( uint8_t )( ( timeout >> 8 ) & 0xFF );
    buf[2] = ( uint8_t )( timeout & 0xFF );
    SX126xWriteCommand( RADIO_SET_RX, buf, 3 );
}

void SX126xSetRxBoosted( uint32_t timeout )
{
    uint8_t buf[3];

    SX126xSetOperatingMode( MODE_RX );

    SX126xWriteRegister( REG_RX_GAIN, 0x96 ); // max LNA gain, increase current by ~2mA for around ~3dB in sensitivity

    buf[0] = ( uint8_t )( ( timeout >> 16 ) & 0xFF );
    buf[1] = ( uint8_t )( ( timeout >> 8 ) & 0xFF );
    buf[2] = ( uint8_t )( timeout & 0xFF );
    SX126xWriteCommand( RADIO_SET_RX, buf, 3 );
}

void SX126xSetRxDutyCycle( uint32_t rxTime, uint32_t sleepTime )
{
    uint8_t buf[6];

    buf[0] = ( uint8_t )( ( rxTime >> 16 ) & 0xFF );
    buf[1] = ( uint8_t )( ( rxTime >> 8 ) & 0xFF );
    buf[2] = ( uint8_t )( rxTime & 0xFF );
    buf[3] = ( uint8_t )( ( sleepTime >> 16 ) & 0xFF );
    buf[4] = ( uint8_t )( ( sleepTime >> 8 ) & 0xFF );
    buf[5] = ( uint8_t )( sleepTime & 0xFF );
    SX126xWriteCommand( RADIO_SET_RXDUTYCYCLE, buf, 6 );
    SX126xSetOperatingMode( MODE_RX_DC );
}

void SX126xSetCad( void )
{
    SX126xWriteCommand( RADIO_SET_CAD, 0, 0 );
    SX126xSetOperatingMode( MODE_CAD );
}

void SX126xSetTxContinuousWave( void )
{
    SX126xWriteCommand( RADIO_SET_TXCONTINUOUSWAVE, 0, 0 );
    SX126xSetOperatingMode( MODE_TX );
}

void SX126xSetTxInfinitePreamble( void )
{
    SX126xWriteCommand( RADIO_SET_TXCONTINUOUSPREAMBLE, 0, 0 );
    SX126xSetOperatingMode( MODE_TX );
}

void SX126xSetStopRxTimerOnPreambleDetect( bool enable )
{
    SX126xWriteCommand( RADIO_SET_STOPRXTIMERONPREAMBLE, ( uint8_t* )&enable, 1 );
}

uint8_t sim_symbNum = 0;
void SX126xSetLoRaSymbNumTimeout( uint8_t symbNum )
{
    uint8_t mant = ( ( ( symbNum > SX126X_MAX_LORA_SYMB_NUM_TIMEOUT ) ?
                       SX126X_MAX_LORA_SYMB_NUM_TIMEOUT : 
                       symbNum ) + 1 ) >> 1;
    uint8_t exp  = 0;
    uint8_t reg  = 0;

    while( mant > 31 )
    {
        mant = ( mant + 3 ) >> 2;
        exp++;
    }

    reg = mant << ( 2 * exp + 1 );
    SX126xWriteCommand( RADIO_SET_LORASYMBTIMEOUT, &reg, 1 );

    if( symbNum != 0 )
    {
        reg = exp + ( mant << 3 );
        SX126xWriteRegister( REG_LR_SYNCH_TIMEOUT, reg );
    }

    sim_symbNum = symbNum;
}

void SX126xSetRegulatorMode( RadioRegulatorMode_t mode )
{
    SX126xWriteCommand( RADIO_SET_REGULATORMODE, ( uint8_t* )&mode, 1 );
}

void SX126xCalibrate( CalibrationParams_t calibParam )
{
    uint8_t value = ( ( ( uint8_t )calibParam.Fields.ImgEnable << 6 ) |
                      ( ( uint8_t )calibParam.Fields.ADCBulkPEnable << 5 ) |
                      ( ( uint8_t )calibParam.Fields.ADCBulkNEnable << 4 ) |
                      ( ( uint8_t )calibParam.Fields.ADCPulseEnable << 3 ) |
                      ( ( uint8_t )calibParam.Fields.PLLEnable << 2 ) |
                      ( ( uint8_t )calibParam.Fields.RC13MEnable << 1 ) |
                      ( ( uint8_t )calibParam.Fields.RC64KEnable ) );

    SX126xWriteCommand( RADIO_CALIBRATE, &value, 1 );
}

void SX126xCalibrateImage( uint32_t freq )
{
    uint8_t calFreq[2];

    if( freq > 900000000 )
    {
        calFreq[0] = 0xE1;
        calFreq[1] = 0xE9;
    }
    else if( freq > 850000000 )
    {
        calFreq[0] = 0xD7;
        calFreq[1] = 0xDB;
    }
    else if( freq > 770000000 )
    {
        calFreq[0] = 0xC1;
        calFreq[1] = 0xC5;
    }
    else if( freq > 460000000 )
    {
        calFreq[0] = 0x75;
        calFreq[1] = 0x81;
    }
    else if( freq > 425000000 )
    {
        calFreq[0] = 0x6B;
        calFreq[1] = 0x6F;
    }
    SX126xWriteCommand( RADIO_CALIBRATEIMAGE, calFreq, 2 );
}

void SX126xSetPaConfig( uint8_t paDutyCycle, uint8_t hpMax, uint8_t deviceSel, uint8_t paLut )
{
    uint8_t buf[4];

    buf[0] = paDutyCycle;
    buf[1] = hpMax;
    buf[2] = deviceSel;
    buf[3] = paLut;
    SX126xWriteCommand( RADIO_SET_PACONFIG, buf, 4 );
}


void SX126xGetPacketStatus( PacketStatus_t *pktStatus )
{
    pktStatus->packetType = SX126xGetPacketType( );
    switch( pktStatus->packetType )
    {
        case PACKET_TYPE_GFSK:
            pktStatus->Params.Gfsk.RxStatus = 0;
            pktStatus->Params.Gfsk.RssiSync = 0;
            pktStatus->Params.Gfsk.RssiAvg = 0;
            pktStatus->Params.Gfsk.FreqError = 0;
            break;

        case PACKET_TYPE_LORA:
            pktStatus->Params.LoRa.RssiPkt = 0;
            // Returns SNR value [dB] rounded to the nearest integer value
            pktStatus->Params.LoRa.SnrPkt = 0;
            pktStatus->Params.LoRa.SignalRssiPkt = 0;
            pktStatus->Params.LoRa.FreqError = FrequencyError;
            break;

        default:
        case PACKET_TYPE_NONE:
            // In that specific case, we set everything in the pktStatus to zeros
            // and reset the packet type accordingly
            memset( pktStatus, 0, sizeof( PacketStatus_t ) );
            pktStatus->packetType = PACKET_TYPE_NONE;
            break;
    }
}

void SX126xSetRxTxFallbackMode( uint8_t fallbackMode )
{
    SX126xWriteCommand( RADIO_SET_TXFALLBACKMODE, &fallbackMode, 1 );
}

void SX126xSetDioIrqParams( uint16_t irqMask, uint16_t dio1Mask, uint16_t dio2Mask, uint16_t dio3Mask )
{
    uint8_t buf[8];

    buf[0] = ( uint8_t )( ( irqMask >> 8 ) & 0x00FF );
    buf[1] = ( uint8_t )( irqMask & 0x00FF );
    buf[2] = ( uint8_t )( ( dio1Mask >> 8 ) & 0x00FF );
    buf[3] = ( uint8_t )( dio1Mask & 0x00FF );
    buf[4] = ( uint8_t )( ( dio2Mask >> 8 ) & 0x00FF );
    buf[5] = ( uint8_t )( dio2Mask & 0x00FF );
    buf[6] = ( uint8_t )( ( dio3Mask >> 8 ) & 0x00FF );
    buf[7] = ( uint8_t )( dio3Mask & 0x00FF );
    SX126xWriteCommand( RADIO_CFG_DIOIRQ, buf, 8 );
}

uint16_t SX126xGetIrqStatus( void )
{
    uint8_t irqStatus[2];

    SX126xReadCommand( RADIO_GET_IRQSTATUS, irqStatus, 2 );
    return ( irqStatus[0] << 8 ) | irqStatus[1];
}

void SX126xSetDio2AsRfSwitchCtrl( uint8_t enable )
{
    SX126xWriteCommand( RADIO_SET_RFSWITCHMODE, &enable, 1 );
}

void SX126xSetDio3AsTcxoCtrl( RadioTcxoCtrlVoltage_t tcxoVoltage, uint32_t timeout )
{
    uint8_t buf[4];

    buf[0] = tcxoVoltage & 0x07;
    buf[1] = ( uint8_t )( ( timeout >> 16 ) & 0xFF );
    buf[2] = ( uint8_t )( ( timeout >> 8 ) & 0xFF );
    buf[3] = ( uint8_t )( timeout & 0xFF );

    SX126xWriteCommand( RADIO_SET_TCXOMODE, buf, 4 );
}

uint32_t sim_frequency = 0;
void SX126xSetRfFrequency( uint32_t frequency )
{
    sim_frequency = frequency;
}

void SX126xSetPacketType( RadioPacketTypes_t packetType )
{
    // Save packet type internally to avoid questioning the radio
    PacketType = packetType;
}

RadioPacketTypes_t SX126xGetPacketType( void )
{
    return PacketType;
}

int8_t sim_power = 0;
RadioRampTimes_t sim_rampTime = 0;
void SX126xSetTxParams( int8_t power, RadioRampTimes_t rampTime )
{
    sim_power = power;
    sim_rampTime = rampTime;
}

ModulationParams_t sim_modulationParams;

void SX126xSetModulationParams( ModulationParams_t *modulationParams )
{
    memcpy(&sim_modulationParams, modulationParams, sizeof(ModulationParams_t));
}

PacketParams_t sim_packetParams;

void SX126xSetPacketParams( PacketParams_t *packetParams )
{
    memcpy(&sim_packetParams, packetParams, sizeof(PacketParams_t));
}

RadioLoRaCadSymbols_t sim_cadSymbolNum;
uint8_t sim_cadDetPeak;
uint8_t sim_cadDetMin;
RadioCadExitModes_t sim_cadExitMode;
uint32_t sim_cadTimeout;

void SX126xSetCadParams( RadioLoRaCadSymbols_t cadSymbolNum, uint8_t cadDetPeak, uint8_t cadDetMin, RadioCadExitModes_t cadExitMode, uint32_t cadTimeout )
{
    sim_cadSymbolNum = cadSymbolNum;
    sim_cadDetPeak = cadDetPeak;
    sim_cadDetMin = cadDetMin;
    sim_cadExitMode = cadExitMode;
    sim_cadTimeout = cadTimeout;
}

uint8_t sim_txBaseAddress;
uint8_t sim_rxBaseAddress;
void SX126xSetBufferBaseAddress( uint8_t txBaseAddress, uint8_t rxBaseAddress )
{
    sim_txBaseAddress = txBaseAddress;
    sim_rxBaseAddress = rxBaseAddress;
}

int8_t SX126xGetRssiInst( void )
{
    int8_t rssi = -42;
    return rssi;
}

void SX126xClearIrqStatus( uint16_t irq )
{
}
