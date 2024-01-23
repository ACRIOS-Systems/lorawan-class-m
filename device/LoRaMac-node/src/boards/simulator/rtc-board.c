/*!
 * \file      rtc-board.c
 *
 * \brief     Target board RTC timer and low power modes management
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
 *              (C)2013-2017 Semtech - STMicroelectronics
 *
 * \endcode
 *
 * \author    Miguel Luis ( Semtech )
 *
 * \author    Gregory Cristian ( Semtech )
 *
 * \author    MCD Application Team (C)( STMicroelectronics International )
 */
#include <math.h>
#include <time.h>
#include "utilities.h"
#include "delay.h"
#include "board.h"
#include "timer.h"
#include "systime.h"
#include "gpio.h"
#include "sysIrqHandlers.h"
#include "lpm-board.h"
#include "rtc-board.h"

#include <sys/time.h>
#include <stdio.h>
#include <unistd.h>

// MCU Wake Up Time
#define MIN_ALARM_DELAY                             3 // in ticks

/*!
 * \brief Days, Hours, Minutes and seconds
 */
#define DAYS_IN_LEAP_YEAR                           ( ( uint32_t )  366U )
#define DAYS_IN_YEAR                                ( ( uint32_t )  365U )
#define SECONDS_IN_1DAY                             ( ( uint32_t )86400U )
#define SECONDS_IN_1HOUR                            ( ( uint32_t ) 3600U )
#define SECONDS_IN_1MINUTE                          ( ( uint32_t )   60U )
#define MINUTES_IN_1HOUR                            ( ( uint32_t )   60U )
#define HOURS_IN_1DAY                               ( ( uint32_t )   24U )

/*!
 * \brief Correction factors
 */
#define  DAYS_IN_MONTH_CORRECTION_NORM              ( ( uint32_t )0x99AAA0 )
#define  DAYS_IN_MONTH_CORRECTION_LEAP              ( ( uint32_t )0x445550 )

/*!
 * \brief Calculates ceiling( X / N )
 */
#define DIVC( X, N )                                ( ( ( X ) + ( N ) -1 ) / ( N ) )

/*!
 * RTC timer context 
 */
typedef struct
{
    uint32_t        Time;         // Reference time
}RtcTimerContext_t;

/*!
 * \brief Indicates if the RTC is already Initialized or not
 */
static bool RtcInitialized = false;

/*!
 * Number of days in each month on a normal year
 */
static const uint8_t DaysInMonth[] = { 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31 };

/*!
 * Number of days in each month on a leap year
 */
static const uint8_t DaysInMonthLeapYear[] = { 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31 };


/*!
 * Keep the value of the RTC timer when the RTC alarm is set
 * Set with the \ref RtcSetTimerContext function
 * Value is kept as a Reference to calculate alarm
 */
static RtcTimerContext_t RtcTimerContext;

void RtcInit( void )
{
    if( RtcInitialized == false )
    {
        RtcSetTimerContext( );
        RtcInitialized = true;
    }
}

#define USE_CONSOLE_TIME // define to use 'dots'

#ifdef USE_CONSOLE_TIME
volatile uint64_t mtime = 0;

void RtcIncrementTick(void)
{
    mtime = mtime + 1;
}
#endif


/*!
 * \brief Sets the RTC timer reference, sets also the RTC_DateStruct and RTC_TimeStruct
 *
 * \param none
 * \retval timerValue In ticks
 */
uint32_t RtcSetTimerContext( void )
{

#ifndef USE_CONSOLE_TIME
    struct timeval ts;

    long mtime;    

    gettimeofday(&ts, NULL);

    mtime = ((ts.tv_sec) * 1000 + ts.tv_usec/1000.0) + 0.5;
#endif

    RtcTimerContext.Time = mtime;
    return ( uint32_t )RtcTimerContext.Time;
}

/*!
 * \brief Gets the RTC timer reference
 *
 * \param none
 * \retval timerValue In ticks
 */
uint32_t RtcGetTimerContext( void )
{
    return RtcTimerContext.Time;
}

/*!
 * \brief returns the wake up time in ticks
 *
 * \retval wake up time in ticks
 */
uint32_t RtcGetMinimumTimeout( void )
{
    return( MIN_ALARM_DELAY );
}

/*!
 * \brief converts time in ms to time in ticks
 *
 * \param[IN] milliseconds Time in milliseconds
 * \retval returns time in timer ticks
 */
uint32_t RtcMs2Tick( uint32_t milliseconds )
{
    return milliseconds;
}

/*!
 * \brief converts time in ticks to time in ms
 *
 * \param[IN] time in timer ticks
 * \retval returns time in milliseconds
 */
uint32_t RtcTick2Ms( uint32_t tick )
{
    return tick;
}

/*!
 * \brief a delay of delay ms by polling RTC
 *
 * \param[IN] delay in ms
 */
void RtcDelayMs( uint32_t delay )
{
    uint64_t delayTicks = 0;
    uint64_t refTicks = RtcGetTimerValue( );

    delayTicks = RtcMs2Tick( delay );

    // Wait delay ms
    while( ( ( RtcGetTimerValue( ) - refTicks ) ) < delayTicks )
    {
        usleep(100);
    }
}

/*!
 * \brief Sets the alarm
 *
 * \note The alarm is set at now (read in this function) + timeout
 *
 * \param timeout Duration of the Timer ticks
 */
void RtcSetAlarm( uint32_t timeout )
{
    // We don't go in Low Power mode for timeout below MIN_ALARM_DELAY
    if( ( int64_t )MIN_ALARM_DELAY < ( int64_t )( timeout - RtcGetTimerElapsedTime( ) ) )
    {
        LpmSetStopMode( LPM_RTC_ID, LPM_ENABLE );
    }
    else
    {
        LpmSetStopMode( LPM_RTC_ID, LPM_DISABLE );
    }

    RtcStartAlarm( timeout );
}

void simulatorSetNextTimerIRQ(uint32_t eventTimestamp);
void BoardLockTimer( void );
void BoardUnlockTimer( void );


void RtcStopAlarm( void )
{
    BoardLockTimer();
    simulatorSetNextTimerIRQ(0);
    BoardUnlockTimer();
}

void RtcStartAlarm( uint32_t timeout )
{
    RtcStopAlarm( );

    BoardLockTimer();
    printf("Next alarm in %u + %u ms\n", RtcGetTimerValue(), timeout);
    simulatorSetNextTimerIRQ(RtcGetTimerValue()+timeout);
    BoardUnlockTimer();
}

uint32_t RtcGetTimerValue( void )
{
#ifndef USE_CONSOLE_TIME
    struct timeval ts;

    uint32_t mtime;    

    gettimeofday(&ts, NULL);

    mtime = ((ts.tv_sec) * 1000 + ts.tv_usec/1000.0) + 0.5;

    return( mtime );

#else
    return( mtime );
#endif
}

uint32_t RtcGetTimerElapsedTime( void )
{
  uint32_t calendarValue = RtcGetTimerValue();

  return( ( uint32_t )( calendarValue - RtcTimerContext.Time ) );
}

uint32_t RtcGetCalendarTime( uint16_t *milliseconds )
{
    uint32_t ticks;

    uint64_t calendarValue = RtcGetTimerValue();


    *milliseconds = RtcTick2Ms( calendarValue );

    return calendarValue/1000;
}

uint32_t fakedata0, fakedata1;

void RtcBkupWrite( uint32_t data0, uint32_t data1 )
{
    fakedata0 = data0;
    fakedata1 = data1;
}

void RtcBkupRead( uint32_t *data0, uint32_t *data1 )
{
  *data0 = fakedata0;
  *data1 = fakedata1;
}

void RtcProcess( void )
{
    // Not used on this platform.
}

TimerTime_t RtcTempCompensation( TimerTime_t period, float temperature )
{
    float k = RTC_TEMP_COEFFICIENT;
    float kDev = RTC_TEMP_DEV_COEFFICIENT;
    float t = RTC_TEMP_TURNOVER;
    float tDev = RTC_TEMP_DEV_TURNOVER;
    float interim = 0.0f;
    float ppm = 0.0f;

    if( k < 0.0f )
    {
        ppm = ( k - kDev );
    }
    else
    {
        ppm = ( k + kDev );
    }
    interim = ( temperature - ( t - tDev ) );
    ppm *=  interim * interim;

    // Calculate the drift in time
    interim = ( ( float ) period * ppm ) / 1000000.0f;
    // Calculate the resulting time period
    interim += period;
    interim = floor( interim );

    if( interim < 0.0f )
    {
        interim = ( float )period;
    }

    // Calculate the resulting period
    return ( TimerTime_t ) interim;
}
