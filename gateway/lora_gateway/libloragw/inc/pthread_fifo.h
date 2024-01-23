/**
 * source: https://github.com/stenbergd/pthread_fifo
 */
/**
 * @brief	Header file of thread-safe FIFO queue using POSIX pthread and semaphore
 */

#ifndef _PTHREAD_FIFO_H_
#define _PTHREAD_FIFO_H_

/* Includes -------------------------------------------------*/
#include <stdint.h>
#include <pthread.h>
#include <semaphore.h>

/* Exported types -------------------------------------------*/

typedef struct pthread_fifo
{
	pthread_mutex_t mutex; // Internal mutex
	sem_t sem; // Internal semaphore
	uint8_t *buffer; // Internal pointer to allocated queue item data buffer
	unsigned int front; // Index to first inserted item data in buffer
	unsigned int back; // Index to next buffer place to insert new item data
	size_t max_nbr_items; // Maximum number of items in buffer
	size_t item_size; // Size of each item in queue
} pthread_fifo_t;

/* Exported function prototypes -----------------------------*/
int pthread_fifo_create(pthread_fifo_t *queue, size_t max_nbr_items, size_t item_size);
int pthread_fifo_enqueue(pthread_fifo_t *queue, uint8_t *item);
int pthread_fifo_dequeue(pthread_fifo_t *queue, uint8_t *item, const struct timespec *timeout);
int pthread_fifo_destroy(pthread_fifo_t *queue);

#endif // _PTHREAD_FIFO_H_
