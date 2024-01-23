/*!
 * \file      board.c
 *
 * \brief     Target board general functions implementation
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
#include "gpio.h"
#include "adc.h"
#include "spi.h"
#include "i2c.h"
#include "uart.h"
#include "timer.h"
#include "sysIrqHandlers.h"
#include "board-config.h"
#include "lpm-board.h"
#include "rtc-board.h"
#include "simulator_radio-board.h"
#include "board.h"

#include "unistd.h"
#include <stdlib.h>
#include <pthread.h>
#include <stdio.h>
#include <time.h>


// function for debug output
#define DEBUG_BOARD_SIMULATOR 1

#if DEBUG_BOARD_SIMULATOR
#define LOG_INF(fmt, ...) \
        do {\
                fprintf(stdout, "INF: "fmt"\n", ##__VA_ARGS__);\
        }while(0)
#else
#define LOG_INF(fmt, ...)
#endif


/*
 * MCU objects
 */
Adc_t Adc;
I2c_t I2c;
Uart_t Uart1;
Uart_t Uart2;

/*!
 * LED GPIO pins objects
 */
Gpio_t Led1;
Gpio_t Led2;
Gpio_t Led3;
Gpio_t Led4;

pthread_t timeoutThread;
pthread_mutex_t radioTimeoutMutex;
pthread_mutex_t timeoutThreadMutex;
pthread_cond_t  timeoutThreadCond;
pthread_cond_t  mainThreadCond;
pthread_mutex_t criticalSectionMutex;
volatile uint32_t timerEventTimestamp;
volatile uint32_t timerEventFlag;
volatile uint32_t radioEventFlag;

/*!
 * Initializes the unused GPIO to a know status
 */
static void BoardUnusedIoInit( void );

/*!
 * Flag to indicate if the MCU is Initialized
 */
static bool McuInitialized = false;

Version_t BoardGetVersion( void )
{
    Version_t boardVersion = { 0 };
   
    return boardVersion;
}

void BoardCriticalSectionBegin( uint32_t *mask )
{
    pthread_mutex_lock( &criticalSectionMutex );   
}

void BoardCriticalSectionEnd( uint32_t *mask )
{
    pthread_mutex_unlock( &criticalSectionMutex );
}

void BoardInitPeriph( void )
{
}

void BoardLockTimer( void )
{
    pthread_mutex_lock( &timeoutThreadMutex );
}

#define USE_CONSOLE_TIME // define to use 'dots'

#ifdef USE_CONSOLE_TIME
int mssleep(long miliseconds)
{
   struct timespec rem;
   struct timespec req= {
       (int)(miliseconds / 1000),     /* secs (Must be Non-Negative) */ 
       (miliseconds % 1000) * 1000000 /* nano (Must be in range of 0 to 999999999) */ 
   };

   return nanosleep(&req , &rem);
}
#endif

void BoardLockTimerFor( uint32_t millis )
{
    #ifndef USE_CONSOLE_TIME
    struct timespec s;
    s.tv_nsec = (millis%1000)*1000000;
    s.tv_sec = millis/1000;

    struct timeval    tp;
    gettimeofday(&tp, NULL);

    /* Convert from timeval to timespec */
    s.tv_sec  += tp.tv_sec;
    s.tv_nsec += tp.tv_usec * 1000;


    pthread_mutex_lock(&timeoutThreadMutex);
    pthread_cond_timedwait(&timeoutThreadCond, &timeoutThreadMutex, &s);
    pthread_mutex_unlock(&timeoutThreadMutex);

    #else
    BoardLockTimer();
    volatile uint32_t startTimestamp = RtcGetTimerValue();
    BoardUnlockTimer();

    while(1)
    {
        BoardLockTimer();
        //printf("sl %u:%u\n", RtcGetTimerValue() - startTimestamp, millis);
        if((RtcGetTimerValue() - startTimestamp) >= millis)
        {
            BoardUnlockTimer();
            break;
        }
        BoardUnlockTimer();
        mssleep(1);
    }
    #endif
}

void BoardUnlockTimer( void )
{
    pthread_mutex_unlock( &timeoutThreadMutex );
}

void simulatorSetNextTimerIRQ(uint32_t eventTimestamp)
{
    if (eventTimestamp != 0)
    {
        LOG_INF("Set next IRQ @T = %u", eventTimestamp);
    }
    timerEventTimestamp = eventTimestamp;
    pthread_cond_signal(&timeoutThreadCond);
}

void BoardProcessIrq(void)
{
    uint32_t val;

    {
        CRITICAL_SECTION_BEGIN( );
        val = timerEventFlag;
        timerEventFlag = 0;
        CRITICAL_SECTION_END( );
    }
    
    if(val)
    {
        LOG_INF("TimerIrqHandler occured at %u", RtcGetTimerValue());
        TimerIrqHandler();
    }
}

void simulatorCheckNextTimerIRQ(void)
{
    uint32_t tets;
    BoardLockTimer();
    tets = timerEventTimestamp - RtcGetTimerValue();
    BoardUnlockTimer();
    
    // check if tets (ms to next timer event) is in the future (not in the past)
    // ATTENTION: like this it does not allow timerEventTimestamp > RtcGetTimerValue() + 24 days
    if (tets > 0 && tets < 0x7FFFFFFF)
    {
        LOG_INF("BoardLockTimerFor %u ms", tets);
        BoardLockTimerFor(tets);
    }

    BoardLockTimer();
    if(timerEventTimestamp)
    {
        LOG_INF("timerEventTimestamp = %u, RtcGetTimerValue() = %u", timerEventTimestamp, RtcGetTimerValue());
        if(timerEventTimestamp <= RtcGetTimerValue())
        {
            timerEventTimestamp = 0;
            BoardUnlockTimer();

            CRITICAL_SECTION_BEGIN( );
            timerEventFlag = 1;
            pthread_cond_signal(&mainThreadCond);
            CRITICAL_SECTION_END( );
            return 0;
        }
        else
        {
            BoardUnlockTimer();
        }
    }
    else
    {
        BoardUnlockTimer();
    }
    return;
}

void* timeoutThreadFunction(void* arg)
{
    while(1)
    {
        simulatorCheckNextTimerIRQ();
    }
}

#define UART2_FIFO_RX_SIZE (32768)
uint8_t Uart2RxBuffer[UART2_FIFO_RX_SIZE];

void BoardInitMcu( void )
{
    if( McuInitialized == false )
    {
        timerEventTimestamp = 0;
        timerEventFlag = 0;
        radioEventFlag = 0;
        if (pthread_mutex_init(&timeoutThreadMutex, NULL) != 0)
        {
            printf("\n timeoutThreadMutex init failed\n");
            exit(-1);
        }

        //initialize mutex/cond_timedwait
        if (pthread_cond_init(&timeoutThreadCond, NULL) != 0)
        {
            printf("\n timeoutThreadCond init failed\n");
            exit(-1);
        }

        if (pthread_mutex_init(&criticalSectionMutex, NULL) != 0)
        {
            printf("\n criticalSectionMutex init failed\n");
            exit(-1);
        }

        if (pthread_cond_init(&mainThreadCond, NULL) != 0)
        {
            printf("\n mainThreadCond init failed\n");
            exit(-1);
        }
        

        FifoInit( &Uart2.FifoRx, Uart2RxBuffer, UART2_FIFO_RX_SIZE );
        // Configure your terminal for 8 Bits data (7 data bit + 1 parity bit), no parity and no flow ctrl
        UartInit( &Uart2, UART_2, NC, NC );
        UartConfig( &Uart2, RX_TX, 921600, UART_8_BIT, UART_1_STOP_BIT, NO_PARITY, NO_FLOW_CTRL );


        RtcInit();

        int iret1 = pthread_create( &timeoutThread, NULL, timeoutThreadFunction, NULL);

        McuInitialized = true;
    }
    else
    {
    }
}

void BoardResetMcu( void )
{
}

void BoardDeInitMcu( void )
{
}

uint32_t BoardGetRandomSeed( void )
{
    return 42;
}

void BoardGetUniqueId( uint8_t *id )
{
    id[7] = 7;
    id[6] = 6;
    id[5] = 5;
    id[4] = 4;
    id[3] = 3;
    id[2] = 2;
    id[1] = 1;
    id[0] = 0;
}

uint16_t BoardBatteryMeasureVoltage( void )
{
    return 0;
}

uint32_t BoardGetBatteryVoltage( void )
{
    return 0;
}

uint8_t BoardGetBatteryLevel( void )
{
    return 0;
}


void SysTick_Handler( void )
{
}

uint8_t GetBoardPowerSource( void )
{
    return BATTERY_POWER;
 
}

/**
  * \brief Enters Low Power Stop Mode
  *
  * \note ARM exists the function when waking up
  */
void LpmEnterStopMode( void)
{
}

/*!
 * \brief Exists Low Power Stop Mode
 */
void LpmExitStopMode( void )
{
}

/*!
 * \brief Enters Low Power Sleep Mode
 *
 * \note ARM exits the function when waking up
 */
void LpmEnterSleepMode( void)
{
}

extern Uart_t *uartObj;
void BoardLowPowerHandler( void )
{
    static uint32_t lastTick = 0;
    uint32_t tick = RtcGetTimerValue();
    if(lastTick != tick)
    {
        lastTick = tick;
        fprintf(stderr, ".\n");
    }
   

    if( IsFifoEmpty( &(uartObj->FifoRx) ))
    {
        pthread_cond_wait(&mainThreadCond, &criticalSectionMutex);
    }
}

