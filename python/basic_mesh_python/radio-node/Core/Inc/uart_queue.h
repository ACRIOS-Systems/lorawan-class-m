#include "timestamp_lists.h"

#define RING_BUFFER_SIZE 2000


typedef struct uart_queue{
    uint16_t head;
    uint16_t tail;
    uint8_t data[RING_BUFFER_SIZE];
}uart_queue;

bool writeUartQueue(uart_queue* queue, uint8_t *data);
bool readUartQueue(uart_queue* queue, uint8_t* destination, uint16_t len);
uint16_t checkUartQueueSize(uart_queue* queue);

