/*

#include "LoRa.h"

bool NODE_role = 0;
bool RX_DONE = false;
bool TX_DONE = false;
bool RSSI_flag = false;
volatile bool uart_received = false;
volatile bool crc_check = true;                         //crc ok?
volatile int8_t RSSI = 0;                               //RSSI?
volatile uint8_t uart_buffer [LORA_NUM_OF_CONFIGURATIONS+MAX_LORA_PAYLOAD];    //configurations + payload
volatile uint8_t lora_buffer [MAX_LORA_PAYLOAD];       //payload from TX
uint8_t uart_sprintf[20];
//--------RX_buffer--------------
uint8_t total_received;
uint8_t current_index = 0;
uint8_t prev_index;
uint8_t num_bytes_avail = 0;

static RadioEvents_t RadioEvents;
//-----------COMMON_PARAMETERS-----------------
uint32_t radio_frequency = 0;
uint16_t preamble_len = 0;
bool header_type = 0;       //1 = implicit, 0 = explicit
uint8_t payload_len = 0;
bool crc_state = 0;
bool iq_state = 0;
uint8_t spreading_factor = 0;
uint16_t bandwidth = 0;
uint8_t coding_rate = 0;
uint8_t LDR = 0;
uint8_t sym_timeout = 0;
//-----------TX_PARAMETERS-----------------
uint8_t tx_power = 0;
uint8_t ramp_time = 0;
uint8_t tx_timeout = 0;
uint8_t sim_size = 0;
uint8_t tx_payload[15] = {"012345678901234"};
//-----------RX_PARAMETERS-----------------
uint32_t rx_timeout = 0;
uint8_t rx_payload = 0;

extern TIM_HandleTypeDef htim2;
extern SUBGHZ_HandleTypeDef hsubghz;


void radio_init(void){
    Radio.Init(&RadioEvents, radio_frequency, preamble_len, header_type, 
                payload_len, crc_state, iq_state, spreading_factor, bandwidth, coding_rate, LDR, tx_power);  
    RadioEvents.TxDone = OnTxDone;
    RadioEvents.RxDone = OnRxDone;
    RadioEvents.TxTimeout = OnTxTimeout;
    RadioEvents.RxTimeout = OnRxTimeout;
    RadioEvents.RxError = OnRxError;
    RadioEvents.CADDetected = OnCADDetected;
    Radio.Standby();
}

void radio_configurations(void)
{
        Radio.Standby();
        //initialize the radio with desired configurations
        Radio.Init(&RadioEvents, 868000000, 8, 1, 
                                    15, 0, 0, 12, 
                                    2, 1, 0, 10);

        if(NODE_role == 1){//NODE_role == TX
            HAL_Delay(2000);
            Radio.Send(tx_payload, 15);
            while(TX_DONE!=1){}
            TX_DONE=false;

        }else{        //NODE_role == RX
            Radio.Rx(rx_timeout, 15);
            while(RX_DONE != true){}
            RX_DONE=false;
        }
}

void OnTxDone( void )
{
    TX_DONE = true;

}

void OnRxDone( uint8_t *payload, uint16_t size)
{
    memcpy(lora_buffer, payload, 15);
    Radio.Standby();
    RX_DONE = true;
}

void OnTxTimeout( void )
{
    TX_DONE = true;
}

void OnRxTimeout( void )
{
    Radio.Standby();
    RX_DONE = true;
}

void OnRxError( void )
{
    // CRC error
    crc_check = false;
    RX_DONE = true;
}

void OnCADDetected( void )
{

}

void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin){
    
	if(GPIO_Pin == GPIO_PIN_1)
	{
        //timestamp = (uint32_t)__HAL_TIM_SET_COUNTER(&htim2, 0);
    }
}

uint32_t getTimestamp(void)
{
    return HAL_GetTick();
}


void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    if(huart == &huart2)
	{
        uart_received = true;
        HAL_UART_Receive_IT(&huart2, uart_buffer, LORA_NUM_OF_CONFIGURATIONS+MAX_LORA_PAYLOAD);
    }
}

*/