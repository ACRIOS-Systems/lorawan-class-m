#include <stdbool.h>
#include <stdint.h>
#include <stdlib.h>

typedef struct linked_list_node
{
    uint32_t timestamp;
    struct linked_list_node *next;
}linked_list_node;


void insertNodeStart(uint32_t timestamp);
void insertNodeAfter(struct linked_list_node *list, uint32_t timestamp);
void deleteNodeStart(void);

void enqueueEventTimestamp(uint32_t timeout);
bool dequeueEventTimestamp(void);