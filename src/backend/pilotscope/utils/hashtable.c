/*-------------------------------------------------------------------------
 *
 * hashtable.c
 *	  Routines to provide a base hash table ability for pilotscope
 *
 * Note that we use the linkedlist to deal with hash conficts.
 * 
 * We use hash_bytes in the source code of pg as our hash function for convinience.
 *  
 * Copyright (c) 2023, Damo Academy of Alibaba Group
 * -------------------------------------------------------------------------
 */

#include "pilotscope/hashtable.h"
#include "common/hashfn.h"
#include "utils/memutils.h"

Hashtable* table;          // store the foreign subquery (its hash of prefix is the key) and the corresponding cardinality (value)
Hashtable* count_table;    // store the generated subquery (its hash of prefix is the key) and the corresponding count (value)

static Entry* create_entry(const char* key, const char* value);

// get hash
unsigned int hash(const char* key, int key_len, int table_capacity) 
{
    unsigned int hash_val=hash_bytes((const unsigned char*)key, key_len);
    return hash_val % table_capacity;
}

// create entry
Entry* create_entry(const char* key, const char* value) 
{
    MemoryContext oldcxt = NULL;
    if (strcmp(CurrentMemoryContext->name, "MessageContext") != 0)
    {
        oldcxt = MemoryContextSwitchTo(CurrentMemoryContext->parent);
    }
    Entry* entry = (Entry*)palloc(sizeof(Entry));
    entry->key   = (char*)palloc(strlen(key) + 1);
    entry->value = (char*)palloc(strlen(value) + 1);
    entry->next  = NULL;
    strcpy(entry->key, key);
    strcpy(entry->value, value);
    if (oldcxt != NULL)
    {
        MemoryContextSwitchTo(oldcxt);
    }
    return entry;
}

// create hash table
Hashtable* create_hashtable(int table_capacity) 
{
    Hashtable* table = (Hashtable*)palloc(sizeof(Hashtable));
    table->capacity      = table_capacity;
    table->entries   = (Entry**)palloc0(table_capacity*sizeof(Entry*));
    return table;
}

// put item into hashtable
void put(Hashtable* table, const char* key, const int key_len, const char* value) 
{
    unsigned int index = hash(key, key_len, table->capacity);
    if (table->entries[index] == NULL) 
    {
        table->entries[index] = create_entry(key, value);
    } 
    else 
    {
        Entry* current = table->entries[index];
        while (current != NULL) 
        {
            if (strcmp(current->key, key) == 0) 
            {
                strcpy(current->value, value);
                return;
            }
            current = current->next;
        }
        Entry* entry = create_entry(key, value);
        entry->next  = table->entries[index];
        table->entries[index] = entry;
    }
}

// get value from hashtable according to the key
char* get(Hashtable* table, const char* key, const int key_len) 
{
    unsigned int index = hash(key, key_len, table->capacity);
    Entry* current = table->entries[index];
    while (current != NULL) 
    {
        if (strncmp(current->key, key, key_len) == 0) 
        {
            return current->value;
        }
        current = current->next;
    }
    return NULL;
}