from spinn_front_end_common.utilities.constants import SIMULATION_N_BYTES
from spinn_front_end_common.interface.simulation import simulation_utilities


def generate_system_data_region(
        spec, region_id, machine_vertex, machine_time_step, time_scale_factor):
    # reserve memory regions
    spec.reserve_memory_region(
        region=region_id, size=SIMULATION_N_BYTES, label='systemInfo')

    # simulation .c requirements
    spec.switch_write_focus(region_id)
    spec.write_array(simulation_utilities.get_simulation_header_array(
        machine_vertex.get_binary_file_name(), machine_time_step,
        time_scale_factor))
