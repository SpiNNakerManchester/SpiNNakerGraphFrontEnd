#ifndef __DLL_H__
#define __DLL_H__

typedef struct list_entry {
    void* data;

    struct list_entry* next;
    struct list_entry* prev;
} list_entry;

typedef struct double_linked_list {
    size_t size;

    list_entry** head;
    list_entry** tail;

} double_linked_list;

void push(double_linked_list* dll, void* data){

    list_entry* new_head = (list_entry*) sark_alloc(1, sizeof(list_entry));

    list_entry* old_head = *dll->head;

    new_head->data = data;
    new_head->prev = NULL;
    new_head->next = old_head;

    if(old_head == NULL){
        *dll->tail = new_head;
    }else{
        old_head->prev = new_head;
    }

    *dll->head = new_head;
    dll->size++;
}

double_linked_list* init_double_linked_list(){
    double_linked_list* dll = (double_linked_list*)
                              sark_alloc(1, sizeof(double_linked_list));

    dll->size  = 0;
    dll->head  = (list_entry**)sark_alloc(1, sizeof(list_entry*));
    *dll->head = NULL;

    dll->tail  = (list_entry**)sark_alloc(1, sizeof(list_entry*));
    *dll->tail = NULL;

    return dll;
}

#endif