#ifndef INC_PING_PONG_H_
#define INC_PING_PONG_H_

#include "stm32wlxx_hal.h"
#include "radio.h"
#include <stddef.h>
#include <string.h>

uint32_t getTimestamp(void);
void uart_timestamp(uint32_t timr, uint32_t timestmp);
void radio_init(void);
void lora_poll(void);
void sendPING(void);

void OnTxDone( void );
void OnRxDone( uint8_t *payload, uint16_t size);
void OnTxTimeout( void );
void OnRxTimeout( void );
void OnRxError( void );
void OnCADDetected( void );
void OnCADTimeout( void );
void OnPreambleDetected( void );
void OnHeaderValid( void );
void OnHeaderError( void );

void radio_configurations(void);
void unpack (void);

#define RX_TIMEOUT_VALUE   65000    //65k = 1sec 

#define MAX_LORA_PAYLOAD 255
#define LORA_NUM_OF_CONFIGURATIONS 22
#define SX126X_REG_RX_ADDR_POINTER 0x0803

typedef enum
{   
    INIT = 1,
    PROCESS,
    RX,
    RX_TIMEOUT,
    RX_ERROR,
    RX_WINDOW,
    TX_TIMEOUT,
}States_t;

#endif
