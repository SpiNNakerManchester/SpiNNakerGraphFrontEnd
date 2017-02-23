#include <debug.h>
#include <spin1_api.h>
#include <data_specification.h>
#include <simulation.h>

static uint32_t simulation_ticks;

void timer_callback(uint time, uint unused1) {
    if (time == 1) {
        log_warning(
            "Going to run for %u timesteps", simulation_ticks + 1000000);
    } else if (time > simulation_ticks + 1000000) {
        simulation_exit();
    }
}

void c_main() {

    uint32_t timer_period;
    uint32_t infinite_run;

    address_t address = data_specification_get_data_address();

    if (!data_specification_read_header(address)) {
        rt_error(RTE_SWERR);
    }

    if (!simulation_initialise(
            data_specification_get_region(0, address), APPLICATION_NAME_HASH,
            &timer_period, &simulation_ticks,
            &infinite_run, 1, NULL, NULL)) {
        rt_error(RTE_SWERR);
    }

    spin1_set_timer_tick(timer_period);
    spin1_callback_on(TIMER_TICK, timer_callback, 0);

    simulation_run();
}
