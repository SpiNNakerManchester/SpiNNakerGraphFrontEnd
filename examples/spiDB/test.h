
#ifndef __TEST_H__
#define __TEST_H__

#include <debug.h>

//TODO should be debug
#define log_assert(message, ...) do {__log(LOG_INFO, "[ASSERT]   ", message, ##__VA_ARGS__);} while (0)

#define assert_t(test,msg,...) do { if (!test) log_assert(msg, ##__VA_ARGS__);} while (0)
#define assert_f(test,msg,...) do { if  (test) log_assert(msg, ##__VA_ARGS__);} while (0)

//TODO make use of this
#define run_test(test) do { char* msg = test(); tests_run++; if (msg) return msg; } while (0)

#endif