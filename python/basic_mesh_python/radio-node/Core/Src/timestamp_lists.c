#include "timestamp_lists.h"

extern uint32_t RTC_get_Timestamp(void);
linked_list_node *head = NULL;
linked_list_node *current = NULL;


void insertNodeStart(uint32_t timestamp)
{
    linked_list_node *ptrToMem = (linked_list_node*) malloc(sizeof(linked_list_node));
    ptrToMem->timestamp = timestamp;
    if (head  == NULL)
    {
        head = ptrToMem;
        ptrToMem->next = NULL;
    }else
    {
        ptrToMem->next = head;
        head = ptrToMem;
    }
}

void insertNodeAfter(linked_list_node *list, uint32_t timestamp)
{
    linked_list_node *ptrToMem = (linked_list_node*) malloc(sizeof(linked_list_node));
    ptrToMem->timestamp = timestamp;
    ptrToMem->next = list->next;
    list->next = ptrToMem;
}

void deleteNodeStart()
{
    linked_list_node *unlinked_head = head;
    head = head->next;
    free(unlinked_head);
}

void enqueueEventTimestamp(uint32_t timeout){
    uint32_t current_timestamp = RTC_get_Timestamp();
    uint32_t event_timestamp = timeout;
    
    if (head == NULL || (int32_t)(event_timestamp) < (int32_t)(head->timestamp)){
        insertNodeStart(event_timestamp);
    }else{
        current = head;
        while(current->next != NULL && (int32_t)(current->next->timestamp) < (int32_t)(event_timestamp)){
            current = current->next;
        }
        insertNodeAfter(current, event_timestamp);
    }
}

bool dequeueEventTimestamp(){
    uint32_t current_timestamp = RTC_get_Timestamp();
    uint32_t event_timestamp = head->timestamp;
    if (head != NULL && (int32_t)(event_timestamp-current_timestamp) <= 0){
        deleteNodeStart();
        return true;
    }else{
        return false;
    }
}