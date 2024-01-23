/**
 * source: https://github.com/stenbergd/pthread_fifo
 */
/**
 * @brief	Source code file of thread-safe FIFO queue using POSIX pthread and semaphore
 * 			implemented as a memory ring buffer
 */

/* Includes -------------------------------------------------*/
#define _POSIX_C_SOURCE 200112L

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <errno.h>
#include <pthread.h>
#include <semaphore.h>
#include <sys/time.h>

#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <semaphore.h>
#include <time.h>
#include <assert.h>
#include <errno.h>
#include <signal.h>

#include "pthread_fifo.h"

/**
 * @brief	Creates a new FIFO queue, dynamically allocating necessary memory and resources
 * @param queue : Pointer to FIFO queue to be created
 * @param queue_len : Sets maximum number of FIFO queue items
 * @param item_size : Size of each FIFO queue item
 * @retval	0 if OK, else error
 */
int pthread_fifo_create(struct pthread_fifo *queue, size_t max_nbr_items, size_t item_size)
{
	int status = 1;

	if (NULL == queue || 0 >= max_nbr_items || 0 >= item_size) {
		status = EINVAL;
		goto out;
	}

	memset(queue, 0, sizeof(struct pthread_fifo));

	status = sem_init(&queue->sem, 0, 0);
	if (0 != status) {
		goto out;
	}

	status = pthread_mutex_init(&queue->mutex, NULL);
	if (0 != status) {
		goto out;
	}

	queue->buffer = malloc(item_size * max_nbr_items);
	if (0 != status) {
		goto out;
	}

	queue->front = 0;
	queue->back = 0;

	queue->max_nbr_items = max_nbr_items;
	queue->item_size = item_size;

	status = 0;

out:
	return status;
}

/**
 * @brief	Sends a new FIFO queue item by copying the data of it to the FIFO queue ring buffer
 * @param queue : Pointer to FIFO queue definition
 * @param item : Pointer to data buffer to be copied to FIFO queue
 * @retval	0 if OK, else error
 */
int pthread_fifo_enqueue(struct pthread_fifo *queue, uint8_t *item)
{
	int status = 0;

	if (NULL == queue || NULL == item) {
		status = EINVAL;
		goto out;
	}

	if(queue->max_nbr_items == 0 || queue->item_size == 0) {
		status = -101;
		goto out;
	}

	pthread_mutex_lock(&queue->mutex);
	if (0 != status) {
		goto out;
	}

	if (((queue->back + 1) % queue->max_nbr_items) == queue->front) {
		status = ENOMEM;
		goto out;
	}

	memcpy(&queue->buffer[queue->item_size*queue->back], item, queue->item_size);

	queue->back = (queue->back + 1) % queue->max_nbr_items;

	status = sem_post(&queue->sem);

out:
	pthread_mutex_unlock(&queue->mutex);

	return status;
}

/**
 * @brief	Fetches the next FIFO queue item. Function call is blocking with an optional timeout.
 * @param queue : Pointer to FIFO queue definition
 * @param item : Pointer to item data buffer to which data will be copied to from the FIFO queue buffer
 * @param timeout : Timespec struct defining max blocking time. If set to NULL call will block until new queue item becomes available.
 * @retval	0 if OK, else error
 */
int pthread_fifo_dequeue(struct pthread_fifo *queue, uint8_t *item, const struct timespec *timeout)
{
	int status = 0;
	struct timespec abstimeout;

	if (NULL == queue || NULL == item) {
		status = EINVAL;
		goto out;
	}

	if (NULL != timeout) {
		status = clock_gettime(CLOCK_REALTIME, &abstimeout);
		if (0 != status) {
			goto out;
		}

		abstimeout.tv_sec += timeout->tv_sec;
		abstimeout.tv_nsec += timeout->tv_nsec;

		if (abstimeout.tv_nsec >= 1000000000) {
			abstimeout.tv_sec++;
			abstimeout.tv_nsec -= 1000000000;
		}

		status = sem_timedwait(&queue->sem, &abstimeout); // Might not work on all systems
		if (0 != status && ETIMEDOUT != status) {
			goto out;
		}
	} else {
		status = sem_wait(&queue->sem);
		if (0 != status) {
			goto out;
		}
	}

	if (0 != status) {
		status = errno;
		goto out;
	}

	status = pthread_mutex_lock(&queue->mutex);
	if (0 != status) {
		goto out;
	}

	memcpy(item, &queue->buffer[queue->item_size*queue->front], queue->item_size);

	queue->front = (queue->front + 1) % queue->max_nbr_items;

out:
	pthread_mutex_unlock(&queue->mutex);

	return status;
}

/**
 * @brief	Frees up FIFO queue allocated memory and destroys associated mutex and semaphore
 * @param queue : Pointer to FIFO queue definition
 * @retval	0 if OK, else error
 */
int pthread_fifo_destroy(struct pthread_fifo *queue)
{
	int status = 0;

	if (NULL == queue) {
		status = EINVAL;
		goto out;
	}

	pthread_mutex_lock(&queue->mutex);

	if (NULL != queue->buffer) {
		free(queue->buffer);
	}

	pthread_mutex_unlock(&queue->mutex);

	pthread_mutex_destroy(&queue->mutex);

	sem_destroy(&queue->sem);

out:
	return status;
}
