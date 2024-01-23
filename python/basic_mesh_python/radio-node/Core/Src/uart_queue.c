#include "uart_queue.h"

bool writeUartQueue(uart_queue* queue, uint8_t *data){
    if ((queue->tail-queue->head)==1){
        return false;                       //queue too full to write data right now
    }
    queue->data[queue->head] = *data;
    queue->head = (queue->head+1)%sizeof(queue->data);
    return true;
}

bool readUartQueue(uart_queue* queue, uint8_t* destination, uint16_t len){
    if (queue->tail == queue->head){
        return false;                       //queue empty
    }
    for (int i=0; i<len; i++){
        *(destination+i) = queue->data[queue->tail];
        queue->tail = (queue->tail+1)%sizeof(queue->data);
    }
    return true;
}

uint16_t checkUartQueueSize(uart_queue* queue){
    if (queue->head>=queue->tail){
        return (queue->head-queue->tail);
    }else{
        return (sizeof(queue->data)-(queue->tail-queue->head));
    }
}


