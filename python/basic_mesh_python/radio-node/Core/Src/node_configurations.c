#include "LoRa.h"
#include "uart_queue.h"

#define APPROX_PACKET_INFO_SIZE_TX 250
#define APPROX_PACKET_INFO_SIZE_RX 200
uint8_t MyBuffer[RING_BUFFER_SIZE];
uint8_t uart_message_out[1000];

uint8_t NODE_command[3];
uint8_t data_ready_counter = 0;
bool CAD_detected_flag = false;
bool CAD_timeout_flag = false;

bool RX_DONE = false;
bool TX_DONE = false;
bool TXRX_TIMEOUT = false;
bool timestamp_flag = false;
uint32_t timestamp = 0;
volatile bool exti_flag = false;
volatile bool uart_received = false;
volatile bool crc_check = true;                         //crc ok?
volatile uint8_t uart_byte;
volatile uint8_t lora_buffer [MAX_LORA_PAYLOAD];        //payload from TX
uart_queue MyUartQueue;
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
uint16_t payload_len = 0;
bool crc_state = 0;
bool iq_state = 0;
uint8_t spreading_factor = 0;
uint16_t bandwidth = 0;
uint8_t coding_rate = 0;
uint8_t LDR = 0;
bool wait_for_interrupt = 0;
uint32_t delay_fire = 0;
bool packet_interrupt = 0;
uint32_t timestamp_delay_fire = 0;
//-----------TX_PARAMETERS-----------------
uint8_t tx_power = 0;
uint8_t ramp_time = 0;
uint8_t tx_timeout = 0;
uint8_t sim_size = 0;
uint8_t tx_payload[1000];
uint8_t hexStrToIntPayload[260];
uint16_t payload_size;
//-----------RX_PARAMETERS-----------------
uint32_t rx_timeout = 0;
uint8_t rx_payload = 0;
uint16_t message_len = 0;
uint8_t intToHexStrPayload[1000];

uint16_t msg_len = 0;
uint8_t timestampHW[40];

extern TIM_HandleTypeDef htim2;
extern SUBGHZ_HandleTypeDef hsubghz;
extern uint32_t RTCwakeUpTimer;
extern PacketStatus_t packetStatus;
uint32_t RTC_get_Timestamp(void);


void radio_init(void){
    Radio.Init(&RadioEvents, radio_frequency, preamble_len, header_type, 
                payload_len, crc_state, iq_state, spreading_factor, bandwidth, coding_rate, LDR, tx_power);  
    RadioEvents.TxDone = OnTxDone;
    RadioEvents.RxDone = OnRxDone;
    RadioEvents.TxTimeout = OnTxTimeout;
    RadioEvents.RxTimeout = OnRxTimeout;
    RadioEvents.RxError = OnRxError;
    RadioEvents.CADDetected = OnCADDetected;
    RadioEvents.CADTimeout = OnCADTimeout;
    RadioEvents.PreambleDetected = OnPreambleDetected;
    RadioEvents.HeaderValid = OnHeaderValid;
    RadioEvents.HeaderError = OnHeaderError;
    Radio.Sleep();
}

uint16_t find_parameter(uint8_t *parameter_name){
    uint8_t j = 0;
    for(uint16_t i=0; i<sizeof(MyBuffer); i++){
        if (*(parameter_name+j)==MyBuffer[i]){
            j++;
            if(MyBuffer[i] == '='){
                MyBuffer[i] = '\0';
                return i+1;
            }
        }else{
            j=0;
        }
    }
    return false;
}

uint32_t find_value(uint8_t *parameter_name){
    uint16_t parameter_position = 0;
    uint32_t value = 0;
    parameter_position = find_parameter(parameter_name);
    sscanf(&MyBuffer[parameter_position], "%ld", &value);
    return value;
}

uint8_t hexStrToInt(uint8_t *output, uint8_t *values, uint16_t size){
    uint8_t outSize = 0;
    char hex[3];
    for (uint16_t i=0; i<size; i+=2){
        hex[0] = values[i];
        hex[1] = values[i+1];
        output[outSize] = (int)strtol(hex, NULL, 16);
        outSize += 1;
        if (i != size){
            i+=1;
        }
    }
    return outSize;
}

uint16_t intToHexStr(uint8_t *output, uint8_t *values, uint8_t size){
    uint16_t outSize = 0;
    char hex[3];
    for (uint8_t i=0; i<size; i++){
        sprintf((&output[outSize]), "%2x", (values[i]));
        outSize += 2;
        if (i < size-1){
            output[outSize] = ':';
            outSize += 1;
        }
    }
    for(uint16_t k=0; k<outSize; k++){
        if(output[k] == ' '){
            output[k] = '0';
        }
    }
    return outSize; 
}

void unpack(void){
    NODE_command[0] = MyBuffer[1];
    NODE_command[1] = MyBuffer[2];
    NODE_command[2] = '\0';

    if (!strcmp(NODE_command, "TS\0")){
        uint32_t event_timestamp = find_value("event_timestamp=");
        enqueueEventTimestamp(event_timestamp);

    }else if (!strcmp(NODE_command, "TR\0")){
        memset(timestampHW, 0, sizeof(timestampHW));
        msg_len = 0;
        sprintf(timestampHW, ":TS_REQ_DONE,%ld\n", RTC_get_Timestamp());
        for(uint8_t i = 0; i<sizeof(timestampHW); i++){
            if (timestampHW[i]!='\0')msg_len++;
        }
        HAL_UART_Transmit(&huart2, timestampHW, msg_len, 1000);

    }else if ((!strcmp(NODE_command, "TX\0")) || (!strcmp(NODE_command, "RX\0"))){
        radio_frequency = find_value("frequency=");
        preamble_len = find_value("preamble_length=");
        header_type = find_value("implicit_header=");
        payload_len = find_value("payload_length=");
        crc_state = find_value("crc_en=");
        iq_state = find_value("iq_inverted=");
        spreading_factor = find_value("spreading_factor=");
        bandwidth = find_value("bandwidth_kHz=");
        coding_rate = find_value("coding_rate=");
        LDR = find_value("low_data_rate=");

        if(bandwidth == 125){bandwidth = 0;}
        else if(bandwidth == 250){bandwidth = 1;}
        else if(bandwidth == 500){bandwidth = 2;}
        if(coding_rate == 5){coding_rate = 1;}
        else if(coding_rate == 6){coding_rate = 2;}
        else if(coding_rate == 7){coding_rate = 3;}
        else if(coding_rate == 8){coding_rate = 4;}

        if (!strcmp(NODE_command, "TX\0")){
            tx_power = find_value("power=");
            payload_size = find_value("size=");
            uint16_t payload_starting_pos = find_parameter("data=");            //find a starting position of the payload
            memcpy(tx_payload, &MyBuffer[payload_starting_pos], payload_len);   //write the payload to tx_payload
            payload_size = hexStrToInt(hexStrToIntPayload, tx_payload, payload_len);

        }else if (!strcmp(NODE_command, "RX\0")){
            rx_timeout = find_value("rx_timeout=")*65; //rx_timeout received as milliseconds, 65000 = 1second
        }
        memset(tx_payload, 0, sizeof(tx_payload));
    }
    memset(MyBuffer, 0, sizeof(MyBuffer));
    return;
}

void radio_configurations(void)
{
    if(dequeueEventTimestamp()){
        HAL_UART_Transmit(&huart2, ":TS_DONE\n", 9, 1000);
    }
    if(data_ready_counter>0){
        readUartQueue(&MyUartQueue, MyBuffer, checkUartQueueSize(&MyUartQueue));
        unpack();
        data_ready_counter -= 1;
        if ((!strcmp(NODE_command, "TX\0")) || (!strcmp(NODE_command, "RX\0"))){
            Radio.Init(&RadioEvents, radio_frequency, preamble_len, header_type,    //initialize the radio with desired configurations
                        payload_size, crc_state, iq_state, spreading_factor, 
                        bandwidth, coding_rate, LDR, tx_power);

            if (!strcmp(NODE_command, "TX\0")){                 //NODE == TX
                Radio.Send(hexStrToIntPayload, payload_size);
                while(TX_DONE != true){}
                TX_DONE = false;
            }else if (!strcmp(NODE_command, "RX\0")){           //NODE == RX
                Radio.Rx(rx_timeout, 0);
            }
        }
    }
    if (RX_DONE == true){
        RX_DONE = false;
        if(crc_check == true){
            message_len = intToHexStr(intToHexStrPayload, lora_buffer, message_len);
            sprintf(uart_message_out, ":RX_DONE,size=%d,data=%s,SNR=%d,RSSI=%d\n", message_len, intToHexStrPayload, packetStatus.Params.LoRa.SnrPkt ,packetStatus.Params.LoRa.RssiPkt);   //CRC+RSSI+PAYLOAD
            message_len = 0;
            for(uint16_t i = 0; i<sizeof(uart_message_out); i++){
                if (uart_message_out[i]!='\0')message_len++;
            }
            HAL_UART_Transmit(&huart2, uart_message_out, message_len, 1000);
            memset(uart_message_out, 0, sizeof(uart_message_out));
            memset(lora_buffer, 0, sizeof(lora_buffer));   
        }else{
            HAL_UART_Transmit(&huart2, ":RX_DONE,CRC_ERROR\n", 19, 1000);
            crc_check = true;
            message_len = 0;
            memset(uart_message_out, 0, sizeof(uart_message_out));
            memset(lora_buffer, 0, sizeof(lora_buffer));   
        }
    }else if(TXRX_TIMEOUT == true){
        HAL_UART_Transmit(&huart2, ":IRQ_RX_TX_TIMEOUT\n", 19, 1000);
        TXRX_TIMEOUT = false;
    }
}

void OnTxDone( void )
{
    TX_DONE = true;
    HAL_UART_Transmit(&huart2, ":TX_DONE\n", 9, 1000);
}

void OnRxDone(uint8_t *payload, uint16_t size)
{
    memcpy(lora_buffer, payload, size);
    message_len = size;
    RX_DONE = true;
}

void OnTxTimeout( void )
{
    TXRX_TIMEOUT = true;
}

void OnRxTimeout( void )
{
    TXRX_TIMEOUT = true;
}

void OnRxError( void )
{
    crc_check = false;
    RX_DONE = true;
}

void OnPreambleDetected(void)
{
    //HAL_UART_Transmit(&huart2, ":PREAMBLE_DETECTED\n", 19, 1000);
}

void OnHeaderValid(void)
{
    //HAL_UART_Transmit(&huart2, ":IRQ_HEADER_VALID\n", 18, 100); 
}

void OnHeaderError(void)
{
    //HAL_UART_Transmit(&huart2, "IRQ_HEADER_ERROR", 16, 100); 
}

void OnCADDetected( void )
{
    //CAD_detected_flag = true;
}

void OnCADTimeout( void )
{
    //CAD_timeout_flag = true;
}

void HAL_GPIO_EXTI_Callback(uint16_t GPIO_Pin){
    
	if(GPIO_Pin == GPIO_PIN_4)
	{
        exti_flag = 1;
    }
}

uint32_t getTimestamp(void)
{
    return HAL_GetTick();
}

uint32_t RTC_get_Timestamp(void)
{
  return RTCwakeUpTimer;
}

void HAL_UART_RxCpltCallback(UART_HandleTypeDef *huart)
{
    if(huart == &huart2)
	{
        uart_received = true;
        writeUartQueue(&MyUartQueue, &uart_byte);
        if(uart_byte =='\n'){
            data_ready_counter += 1;
        }
        HAL_UART_Receive_IT(&huart2, &uart_byte, 1);
    }
}
