#include <debug.h>
#include <spin1_api.h>
#include <data_specification.h>
#include <simulation.h>

uint32_t simulation_ticks;
uint32_t infinite_run;
uint32_t time;

void timer_callback(uint time, uint unused1) {
    if ((!infinite_run && ((time * 2) == simulation_ticks))
            || (infinite_run && (time == 2000))) {
        log_error("Generating Error at time %u", time);
        rt_error(RTE_SWERR);
    }
}

void c_main() {

    uint32_t timer_period;

    address_t address = data_specification_get_data_address();

    if (!data_specification_read_header(address)) {
        rt_error(RTE_SWERR);
    }

    if (!simulation_initialise(
            data_specification_get_region(0, address), APPLICATION_NAME_HASH,
            &timer_period, &simulation_ticks,
            &infinite_run, &time, 1, 1)) {
        rt_error(RTE_SWERR);
    }

    spin1_set_timer_tick(timer_period);
    spin1_callback_on(TIMER_TICK, timer_callback, 0);

    simulation_run();
}
