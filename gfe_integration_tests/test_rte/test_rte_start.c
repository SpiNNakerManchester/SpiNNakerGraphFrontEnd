#include <sark.h>
#include <debug.h>

void c_main() {
    log_error("Generating Error");
    rt_error(RTE_SWERR);
}
