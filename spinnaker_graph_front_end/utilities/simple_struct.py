class SimpleStruct(object):
    def __init__(self, name, members):
        self._members = members
        self._name = name
        self._size = sum(member.type.size for member in members)

    def write_data_spec(self, spec, dictionary):
        for member in self._members:
            value = dictionary[member.name]
            spec.write_value(value, member.type)

    @property
    def size(self):
        return self._size

    @property
    def c_struct(self):
        result = "typedef struct {\n"
        for member in self._members:
            result += "    " + member.type.c_type + " " + member.name + ";"
        result += "} " + self._name + ";\n"
        return result


class Member(object):
    __slots__ = ["name", "type"]

    def __init__(self, type, name):  # @ReservedAssignment
        self.type = type
        self.name = name


# Example of defining structures for conways_cell.c
if False:
    import data_specification.enums.data_type.DataType as Type
    from enum import Enum

    # Create the definitions
    transmissions_t = SimpleStruct("transmissions_t", [
        Member(Type.UINT32, "has_key"),
        Member(Type.UINT32, "my_key")])
    state_t = SimpleStruct("state_t", [
        Member(Type.UINT32, "my_state")])
    neighbour_t = SimpleStruct("neighbour_initial_states_t", [
        Member(Type.UINT32, "alive_states_recieved_this_tick"),
        Member(Type.UINT32, "dead_states_recieved_this_tick")])

    DATA_REGIONS = Enum(
        value="DATA_REGIONS",
        names=[('SYSTEM', 0),
               ('TRANSMISSIONS', 1),
               ('STATE', 2),
               ('NEIGHBOUR_INITIAL_STATES', 3),
               ('RESULTS', 4)])

    # How to create the header file
    with open("conways_cell_types.h", "w") as f:
        f.write(transmissions_t.c_struct)
        f.write(state_t.c_struct)
        f.write(neighbour_t.c_struct)
        # Needs more code to generate the code to 'instantiate' the structures
        # from the DSG regions...

    # How to write the state (assume inside method with spec available)
    def write_structs(spec, key, state, alive, dead):
        variables = {}
        variables["has_key"] = int(key is not None)
        variables["my_key"] = key if key is not None else 0
        variables["my_state"] = int(bool(state))
        variables["alive_states_recieved_this_tick"] = alive
        variables["dead_states_recieved_this_tick"] = dead

        spec.reserve_memory_region(
            region=DATA_REGIONS.TRANSMISSIONS.value,
            size=transmissions_t.size, label="inputs")
        spec.switch_write_focus(DATA_REGIONS.TRANSMISSIONS.value)
        transmissions_t.write_data_spec(spec, variables)

        spec.reserve_memory_region(
            region=DATA_REGIONS.STATE.value,
            size=state_t.size, label="state")
        spec.switch_write_focus(DATA_REGIONS.STATE.value)
        state_t.write_data_spec(spec, variables)

        spec.reserve_memory_region(
            region=DATA_REGIONS.NEIGHBOUR_INITIAL_STATES.value,
            size=neighbour_t.size, label="neighour_states")
        spec.switch_write_focus(DATA_REGIONS.NEIGHBOUR_INITIAL_STATES.value)
        neighbour_t.write_data_spec(spec, variables)
