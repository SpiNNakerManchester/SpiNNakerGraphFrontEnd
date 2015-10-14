from data_specification import utility_calls as dsg_utility_calls

import struct

def read(transceiver, recording_region, x, y, p):

    # Get the App Data for the core
    app_data_base_address = transceiver.get_cpu_information_from_core(x, y, p).user[0]

    region_base_address_offset = \
        dsg_utility_calls.get_region_base_address_offset(app_data_base_address, recording_region)

    region_base_address_buf = buffer(transceiver.read_memory(x, y, region_base_address_offset, 4))
    hello_world_base_address = struct.unpack_from("<I", region_base_address_buf)[0]
    hello_world_base_address += app_data_base_address

    # Read the hello world data size
    number_of_bytes_written_buf = buffer(transceiver.read_memory(
        x, y, hello_world_base_address, 4))
    number_of_bytes_written = struct.unpack_from(
        "<I", number_of_bytes_written_buf)[0]

    hello_world_data = transceiver.read_memory(
        x, y, hello_world_base_address + 4, number_of_bytes_written)

    return hello_world_data
