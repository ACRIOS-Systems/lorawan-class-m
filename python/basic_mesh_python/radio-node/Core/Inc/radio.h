#ifndef INC_RADIO_H_
#define INC_RADIO_H_
#include "stm32wlxx_hal.h"

extern UART_HandleTypeDef huart2;

#include <string.h>
#include <stdio.h>
#include "radio_driver.h"
#include "stm32wlxx_nucleo.h"


typedef enum
{
  STATE_NULL,
  STATE_MASTER,
  STATE_SLAVE
} state_t;

typedef enum
{
  SSTATE_NULL,
  SSTATE_RX,
  SSTATE_TX
} substate_t;


#define RF_FREQUENCY                                868000000 /* Hz */
#define TX_OUTPUT_POWER                             14        /* dBm */    //14
#define LORA_BANDWIDTH                              0         /* Hz */
#define LORA_SPREADING_FACTOR                       12                   //7
#define LORA_CODINGRATE                             1
#define LORA_PREAMBLE_LENGTH                        8         /* Same for Tx and Rx */    //65000
#define LORA_SYMBOL_TIMEOUT                         5         /* Symbols */


typedef struct
{
    void    ( *TxDone )( void );
    void    ( *RxDone )( uint8_t *payload, uint16_t size);
    void    ( *TxTimeout )( void );
    void    ( *RxTimeout )( void );
    void    ( *RxError )( void );
    void    ( *CADDetected) (void);
    void    ( *CADTimeout) (void);
    void    ( *PreambleDetected) (void);
    void    ( *HeaderValid) (void);
    void    ( *HeaderError) (void);
}RadioEvents_t;


struct Radio_s {
  void (*Init)(RadioEvents_t* events, uint32_t radio_frequency, uint16_t preamble_len, bool header_type, 
                uint8_t payload_len, bool crc_state, bool iq_state, uint8_t spreading_factor, uint8_t bandwidth, uint8_t coding_rate, uint8_t TX_power, uint8_t LDR);
  void (*Send)(uint8_t* buffer, uint8_t payload_len);
  void (*Rx)( uint32_t RX_timeout, uint8_t payload_len);
  void (*Standby)(void);
  void (*Sleep)(void);
  void (*StartCad)(uint32_t CADtimeout);
};

extern const struct Radio_s Radio;

void RadioInit(RadioEvents_t* events, uint32_t radio_frequency, uint16_t preamble_len, bool header_type, 
                uint8_t payload_len, bool crc_state, bool iq_state, uint8_t spreading_factor, uint8_t bandwidth, uint8_t coding_rate, uint8_t TX_power, uint8_t LDR);
void RadioSend(uint8_t* buffer, uint8_t payload_len);
void RadioRx( uint32_t RX_timeout, uint8_t payload_len );
void RadioStandby(void);
void RadioSleep(void);
void RadioStartCad(uint32_t CADtimeout);
void RadioOnDioIrq(RadioIrqMasks_t radioIrq);

#endif /* INC_RADIO_H_ */
