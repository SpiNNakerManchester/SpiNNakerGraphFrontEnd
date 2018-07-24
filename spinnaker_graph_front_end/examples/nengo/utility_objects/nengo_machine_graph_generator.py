from pacman.executor import PACMANAlgorithmExecutor


class NengoMachineGraphGenerator(object):

    def __init__(self):
        pass

    def __call__(
            self, nengo_network, machine_time_step,
            nengo_random_number_generator_seed, decoder_cache,
            utilise_extra_core_for_output_types_probe,
            nengo_nodes_as_function_of_time,
            function_of_time_nodes_time_period, insert_interposers,
            spinnaker_machine_for_partitioning,
            system_pre_allocated_resources_inputs,
            system_pre_allocated_resources_algorithms,
            print_timings, do_timings, xml_paths,
            pacman_executor_provenance_path):

        # create data holders
        inputs = dict()
        algorithms = list()
        outputs = list()
        tokens = list()
        required_tokens = list()
        optional_algorithms = list()

        # update inputs with the system pre allocated inputs
        inputs.update(system_pre_allocated_resources_inputs)

        # update algorithms with system pre allocated algor's
        algorithms.extend(system_pre_allocated_resources_algorithms)

        # add nengo algorithms
        algorithms.append("NengoApplicationGraphBuilder")
        algorithms.append("NengoPartitioner")
        if insert_interposers:
            algorithms.append("NengoUtiliseInterposers")

        # add nengo inputs
        inputs["NengoModel"] = nengo_network
        inputs["MachineTimeStep"] = machine_time_step
        inputs["NengoRandomNumberGeneratorSeed"] = (
            nengo_random_number_generator_seed)
        inputs["NengoDecoderCache"] = decoder_cache
        inputs["NengoUtiliseExtraCoreForProbes"] = (
            utilise_extra_core_for_output_types_probe)
        inputs["NengoNodesAsFunctionOfTime"] = nengo_nodes_as_function_of_time
        inputs["NengoNodesAsFunctionOfTimeTimePeriod"] = (
            function_of_time_nodes_time_period)

        # add partitioning inputs
        inputs["MemoryMachine"] = spinnaker_machine_for_partitioning

        # Execute the algorithms
        executor = PACMANAlgorithmExecutor(
            algorithms=algorithms, optional_algorithms=optional_algorithms,
            inputs=inputs, tokens=tokens,
            required_output_tokens=required_tokens, xml_paths=xml_paths,
            required_outputs=outputs, do_timings=do_timings,
            print_timings=print_timings,
            provenance_name="nengo_graph_to_machine_graph",
            provenance_path=pacman_executor_provenance_path)
        executor.execute_mapping()

        return (executor.get_item("MemoryMachineGraph"),
                executor.get_item("NengoOperatorGraph"),
                executor.get_item("NengoHostNetwork"),
                executor.get_item("NengoGraphToAppGraphMap"),
                executor.get_item("NengoRandomNumberGenerator"),
                executor.get_item("NengoGraphMapper"))
