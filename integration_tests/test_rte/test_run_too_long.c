#include <debug.h>
#include <spin1_api.h>
#include <data_specification.h>

static uint32_t simulation_ticks;

void timer_callback(uint time, uint unused1) {
    if (time == 1) {
        log_warning("Going to run for %u ticks", simulation_ticks + 1000000);
    }
    if (time >= simulation_ticks + 1000000) {
        spin1_exit(0);
    }
}

void c_main() {

    address_t address = data_specification_get_data_address();

    if (!data_specification_read_header(address)) {
        rt_error(RTE_SWERR);
    }

    address_t data = data_specification_get_region(0, address);
    simulation_ticks = data[0];
    log_info("Running for %u ticks", simulation_ticks);

    spin1_set_timer_tick(1000);
    spin1_callback_on(TIMER_TICK, timer_callback, 0);

    spin1_start(SYNC_WAIT);
}
