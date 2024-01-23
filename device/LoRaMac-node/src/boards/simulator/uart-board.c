/*!
 * \file      uart-board.c
 *
 * \brief     Target board UART driver implementation
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
#include "utilities.h"
#include "board.h"
#include "sysIrqHandlers.h"
#include "uart-board.h"

#include "unistd.h"
#include <stdlib.h>
#include <pthread.h>
#include <stdio.h>
#include "string.h"
#include "sx126x.h"
#include "timer.h"
#include "sx126x-board.h"

/*!
 * Number of times the UartPutBuffer will try to send the buffer before
 * returning ERROR
 */
#define TX_BUFFER_RETRY_COUNT                       10

uint8_t RxData = 0;
uint8_t TxData = 0;
pthread_t stdinThread;
extern pthread_cond_t  mainThreadCond;
void* stdinThreadFunction(void* arg)
{
    int c;
    Uart_t *obj = arg;
    while(1)
    {
        c = getchar();
        CRITICAL_SECTION_BEGIN( );
        if( IsFifoFull( &(obj->FifoRx) ) == false )
        {
            
            FifoPush( &obj->FifoRx, c );
            pthread_cond_signal(&mainThreadCond);
        }
        CRITICAL_SECTION_END( );
    }
}













extern TimerEvent_t TxTimeoutTimer;
extern TimerEvent_t RxTimeoutTimer;
extern RadioEvents_t* RadioEvents;
extern bool RxContinuous;
extern uint32_t TxTimeout;
extern uint32_t RxTimeout;
extern bool RxContinuous;
extern PacketStatus_t RadioPktStatus;
extern uint8_t RadioRxPayload[];


void simulatorReceiveDoneEvent(const char* cmd)
{
    TimerStop( &RxTimeoutTimer );
    if(strstr(cmd, "CRC_ERROR"))
    {
        if( RxContinuous == false )
        {
            //!< Update operating mode state to a value lower than \ref MODE_STDBY_XOSC
            SX126xSetOperatingMode( MODE_STDBY_RC );
        }
        if( ( RadioEvents != NULL ) && ( RadioEvents->RxError ) )
        {
            RadioEvents->RxError( );
        }
    }
    else
    {
        uint8_t size;

        char* parameter = strstr(cmd, "size=");
        if(parameter)
        {
            int tmpi;
            sscanf(parameter, "size=%d", &tmpi);
            size = (uint8_t)tmpi;
        }
        else
        {
            // abort!
            fprintf(stderr, ":!MISSING 'size=%%d'\n");
            return;
        }

        parameter = strstr(cmd, "data=");
        if(parameter)
        {
            char* dataPtr = parameter + 5; // skip data=
            char* dataStart = dataPtr;
            int sepCount = 0;
            int nibbleCount = 0;
            while((*dataPtr != ',')&&(*dataPtr != '\n')&&(*dataPtr != '\0'))
            {
                if(*dataPtr != ':')
                {
                    nibbleCount++;
                }
                dataPtr++;
            }

            if((nibbleCount/2) != size)
            {
                *dataPtr = '\0';
                // abort!
                fprintf(stderr, ":!Bad size= for %s, should be %d\n", dataStart, nibbleCount/2);
                return;
            }

            for(int i = 0; i < size; i++)
            {
                int tmpi = 0;
                sscanf(dataStart, "%02X:", &tmpi);
                RadioRxPayload[i] = tmpi;
                dataStart += 3;
            }
        }
        else
        {
            // abort!
            fprintf(stderr, ":!MISSING 'size=%%d'\n");
            return;
        }

        RadioPktStatus.packetType = PACKET_TYPE_LORA;
        RadioPktStatus.Params.LoRa.FreqError = 0; //unused
        RadioPktStatus.Params.LoRa.RssiPkt = 0;
        RadioPktStatus.Params.LoRa.SignalRssiPkt = 0; //unused
        RadioPktStatus.Params.LoRa.SnrPkt = 0;

        parameter = strstr(cmd, "RSSI=");
        if(parameter)
        {
            int tmpi;
            sscanf(parameter, "RSSI=%d", &tmpi);
            RadioPktStatus.Params.LoRa.RssiPkt = (int8_t)tmpi;
        }

        parameter = strstr(cmd, "SNR=");
        if(parameter)
        {
            int tmpi;
            sscanf(parameter, "SNR=%d", &tmpi);
            RadioPktStatus.Params.LoRa.SnrPkt = (int8_t)tmpi;
        }

        if( RxContinuous == false )
        {
            //!< Update operating mode state to a value lower than \ref MODE_STDBY_XOSC
            SX126xSetOperatingMode( MODE_STDBY_RC );

            // WORKAROUND - Implicit Header Mode Timeout Behavior, see DS_SX1261-2_V1.2 datasheet chapter 15.3
            SX126xWriteRegister( REG_RTC_CTRL, 0x00 );
            SX126xWriteRegister( REG_EVT_CLR, SX126xReadRegister( REG_EVT_CLR ) | ( 1 << 1 ) );
            // WORKAROUND END
        }

        if( ( RadioEvents != NULL ) && ( RadioEvents->RxDone != NULL ) )
        {
            RadioEvents->RxDone( RadioRxPayload, size, RadioPktStatus.Params.LoRa.RssiPkt, RadioPktStatus.Params.LoRa.SnrPkt );
        }
    }
}

void simulatorTransmitDoneEvent(const char* cmd)
{
    TimerStop( &TxTimeoutTimer );
    //!< Update operating mode state to a value lower than \ref MODE_STDBY_XOSC
    SX126xSetOperatingMode( MODE_STDBY_RC );
    if( ( RadioEvents != NULL ) && ( RadioEvents->TxDone != NULL ) )
    {
        RadioEvents->TxDone( );
    }
}

void simulatorTimeoutEvent(const char* cmd)
{
    if( SX126xGetOperatingMode( ) == MODE_TX )
    {
        TimerStop( &TxTimeoutTimer );
        //!< Update operating mode state to a value lower than \ref MODE_STDBY_XOSC
        SX126xSetOperatingMode( MODE_STDBY_RC );
        if( ( RadioEvents != NULL ) && ( RadioEvents->TxTimeout != NULL ) )
        {
            RadioEvents->TxTimeout( );
        }
    }
    else if( SX126xGetOperatingMode( ) == MODE_RX )
    {
        TimerStop( &RxTimeoutTimer );
        //!< Update operating mode state to a value lower than \ref MODE_STDBY_XOSC
        SX126xSetOperatingMode( MODE_STDBY_RC );
        if( ( RadioEvents != NULL ) && ( RadioEvents->RxTimeout != NULL ) )
        {
            RadioEvents->RxTimeout( );
        }
    }
}

void simulatorTickEvent(const char* cmd)
{
    extern void RtcIncrementTick(void);// increment system time here
    char* parameter = strstr(cmd, "steps=");
    if(parameter)
    {
        unsigned int tmpi;
        sscanf(parameter, "steps=%u", &tmpi);
        for(unsigned int i = 0; i < tmpi; i++)
        {
            RtcIncrementTick();
        }
    }
    else
    {
        RtcIncrementTick();
    }
}

void simualatorQuitEvent(const char* cmd)
{
    // quit the simulator
    printf("quit");
    exit(0);
}

typedef struct
{
    const char* name;
    void (*func)(const char* cmd);
} simulatorCommand_t;

simulatorCommand_t simulatorCommands[] = 
{
    {"RX_DONE", simulatorReceiveDoneEvent},
    {"TX_DONE", simulatorTransmitDoneEvent},
    {"TIMEOUT", simulatorTimeoutEvent},
    {"TICK", simulatorTickEvent},
    {"QUIT", simualatorQuitEvent},
    {NULL, NULL}
};

typedef enum 
{
    SIM_RX_IDLE,
    SIM_RX_OTHER,
    SIM_RX_RUNNING,
} simulatorCommandReceptionState_t;
#define SIM_CMD_MAX_LEN (1024)

int processSimulatorCommand(uint8_t b)
{
    static simulatorCommandReceptionState_t st = SIM_RX_IDLE; 
    static uint8_t cmdBuffer[SIM_CMD_MAX_LEN];
    static int cmdBufferIdx = 0;

    switch (st)
    {
    default:
    case SIM_RX_IDLE:
        if(b == ':')
        {
            // switch to command reception
            st = SIM_RX_RUNNING;
            cmdBufferIdx = 0;
            return 1;
        }
        else if(!((b == '\r')||(b == '\n')||(b == '\0')))
        {
            // line starts with something else than ':'
            st = SIM_RX_OTHER;
        }

        return 0;

    case SIM_RX_OTHER:
        // line started with something else than ':'
        // wait until end of line
        if((b == '\r')||(b == '\n')||(b == '\0'))
        {       
            // switch to idle state
            st = SIM_RX_IDLE;
        }
        return 0;
    
    case SIM_RX_RUNNING:
        if((b == '\r')||(b == '\n')||(b == '\0'))
        {
            st = SIM_RX_IDLE;
            cmdBuffer[cmdBufferIdx] = '\0';

            if(cmdBufferIdx == 0) // zero length command means - increment tick!
            {
                extern void RtcIncrementTick(void);// increment system time here
                RtcIncrementTick();
            }
            else
            {
                printf("Received command: <%s>\n", cmdBuffer);
                
                for(int i = 0; simulatorCommands[i].name; i++)
                {
                    int cmdLen = strlen(simulatorCommands[i].name);
                    if(!strncmp(simulatorCommands[i].name, cmdBuffer, cmdLen))
                    {
                        printf("Execute command %s \n", simulatorCommands[i].name);
                        simulatorCommands[i].func(&cmdBuffer[cmdLen]);
                        fprintf(stderr, ":%s DONE\n", simulatorCommands[i].name);
                        break;
                    }
                }
                
            }
        }
        else
        {
            cmdBuffer[cmdBufferIdx++] = b;
        }
        return 1; // consumed
    }
}


void UartMcuInit( Uart_t *obj, UartId_t uartId, PinNames tx, PinNames rx )
{
    obj->UartId = uartId;

    // start thread to listen to stdin

    int iret1 = pthread_create( &stdinThread, NULL, stdinThreadFunction, obj);
}

void UartMcuConfig( Uart_t *obj, UartMode_t mode, uint32_t baudrate, WordLength_t wordLength, StopBits_t stopBits, Parity_t parity, FlowCtrl_t flowCtrl )
{
}

void UartMcuDeInit( Uart_t *obj )
{
}

uint8_t UartMcuPutChar( Uart_t *obj, uint8_t data )
{
    TxData = data;

    if( IsFifoFull( &obj->FifoTx ) == false )
    {
        CRITICAL_SECTION_BEGIN( );
        FifoPush( &obj->FifoTx, TxData );
        CRITICAL_SECTION_END( );
        return 0; // OK
    }
    return 1; // Busy
}

Uart_t *uartObj = NULL;

uint8_t UartMcuGetChar( Uart_t *obj, uint8_t *data )
{
    if(uartObj == NULL)
    {
        uartObj = obj;
    }
    uint8_t b;
    bool isEmpty;
    CRITICAL_SECTION_BEGIN( );
    isEmpty = IsFifoEmpty( &obj->FifoRx );
    if (!isEmpty)
    {
        b = FifoPop( &obj->FifoRx );
    }
    CRITICAL_SECTION_END( );

    if(!isEmpty)
    {

        // handle all simulator-specific commands here, 
        // let the generic things pass through
        if(processSimulatorCommand(b))
        {
            return 1;
        }
        else
        {
            *data = b;
            return 0;
        }
    }

    return 1;
}

uint8_t UartMcuPutBuffer( Uart_t *obj, uint8_t *buffer, uint16_t size )
{
    uint8_t retryCount;
    uint16_t i;

    for( i = 0; i < size; i++ )
    {
        retryCount = 0;
        while( UartPutChar( obj, buffer[i] ) != 0 )
        {
            retryCount++;

            // Exit if something goes terribly wrong
            if( retryCount > TX_BUFFER_RETRY_COUNT )
            {
                return 1; // Error
            }
        }
    }
    return 0; // OK
}

uint8_t UartMcuGetBuffer( Uart_t *obj, uint8_t *buffer, uint16_t size, uint16_t *nbReadBytes )
{
    uint16_t localSize = 0;

    while( localSize < size )
    {
        if( UartGetChar( obj, buffer + localSize ) == 0 )
        {
            localSize++;
        }
        else
        {
            break;
        }
    }

    *nbReadBytes = localSize;

    if( localSize == 0 )
    {
        return 1; // Empty
    }
    return 0; // OK
}
