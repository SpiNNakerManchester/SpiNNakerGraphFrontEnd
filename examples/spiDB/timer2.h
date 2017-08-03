#ifndef __TIMER_2__
#define __TIMER_2__

    // Use "timer2" to measure elapsed time.
    // Times up to around 10 sec should be OK.

    // Enable timer - free running, 32-bit
    #define ENABLE_TIMER() tc[T2_CONTROL] = 0x82

    // To measure, set timer to 0
    #define START_TIMER() tc[T2_LOAD] = 0

    // Read timer and compute time (microseconds)
    #define READ_TIMER() ((0 - tc[T2_COUNT]) / sark.cpu_clk)

#endif