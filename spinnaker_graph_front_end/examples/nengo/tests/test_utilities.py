import numpy

from nengo.learning_rules import LearningRuleType
from nengo_spinnaker.builder.node import InputNode, OutputNode

from nengo_spinnaker.builder.ports import OutputPort, InputPort, \
    EnsembleOutputPort, EnsembleInputPort
from nengo_spinnaker.builder.transmission_parameters import \
    PassthroughNodeTransmissionParameters, EnsembleTransmissionParameters, \
    NodeTransmissionParameters
from nengo_spinnaker.operators import Filter, EnsembleLIF, SDPReceiver, \
    SDPTransmitter, ValueSink, ValueSource
from nengo_spinnaker.regions.filters import NoneFilter, LowpassFilter, \
    LinearFilter
from nengo_spinnaker.builder.model import PassthroughNode

from spinnaker_graph_front_end.examples.nengo.connection_parameters\
    .ensemble_transmission_parameters import EnsembleTransmissionParameters \
    as GFEEnsembleTransmissionParameters
from spinnaker_graph_front_end.examples.nengo.connection_parameters\
    .node_transmission_parameters import NodeTransmissionParameters as \
    GFENodeTransmissionParameters
from spinnaker_graph_front_end.examples.nengo.connection_parameters\
    .pass_through_node_transmission_parameters import \
    PassthroughNodeTransmissionParameters as \
        GFEPassthroughNodeTransmissionParameters
from spinnaker_graph_front_end.examples.nengo import constants
from spinnaker_graph_front_end.examples.nengo.application_vertices.\
    interposer_application_vertex import \
    InterposerApplicationVertex
from spinnaker_graph_front_end.examples.nengo.application_vertices.\
    lif_application_vertex import \
    LIFApplicationVertex
from spinnaker_graph_front_end.examples.nengo.application_vertices.\
    pass_through_application_vertex import \
    PassThroughApplicationVertex
from spinnaker_graph_front_end.examples.nengo.application_vertices.\
    sdp_receiver_application_vertex import \
    SDPReceiverApplicationVertex
from spinnaker_graph_front_end.examples.nengo.application_vertices.\
    sdp_transmitter_application_vertex import \
    SDPTransmitterApplicationVertex
from spinnaker_graph_front_end.examples.nengo.application_vertices.\
    value_sink_application_vertex import \
    ValueSinkApplicationVertex
from spinnaker_graph_front_end.examples.nengo.application_vertices.\
    value_source_application_vertex import \
    ValueSourceApplicationVertex
from spinnaker_graph_front_end.examples.nengo.filters.low_pass_filter import \
    LowPassFilter as GFELowPassFilter
from spinnaker_graph_front_end.examples.nengo.filters.linear_filter import \
    LinearFilter as GFELinearFilter
from spinnaker_graph_front_end.examples.nengo.filters.none_filter import \
    NoneFilter as GFENoneFilter
from spinnaker_graph_front_end.examples.nengo.nengo_implicit_interfaces.\
    nengo_input_node import \
    NengoInputNode
from spinnaker_graph_front_end.examples.nengo.nengo_implicit_interfaces.\
    nengo_output_node import \
    NengoOutputNode


def compare_against_the_nengo_spinnaker_and_gfe_impls(
        nengo_operators, nengo_to_app_graph_map, connection_map, app_graph,
        nengo_spinnaker_network_builder):
    verts_safe = _test_graph_vertices(
        nengo_operators, nengo_to_app_graph_map,
        nengo_spinnaker_network_builder)
    if not verts_safe:
        return False
    else:
        return _test_graph_edges(
            connection_map, app_graph, nengo_operators, nengo_to_app_graph_map)


def _compare_none_filters(nengo_version, gfe_version):
    return (nengo_version.width == gfe_version.width and
            nengo_version.latching == gfe_version.latching)


def _compare_low_pass_filters(nengo_version, gfe_version):
    return (_compare_none_filters(nengo_version, gfe_version) and
            nengo_version.time_constant == gfe_version.time_constant)


def _compare_linear_filters(nengo_version, gfe_version):
    return (_compare_none_filters(nengo_version, gfe_version) and
            nengo_version.order == gfe_version.order and
            numpy.all(numpy.in1d(nengo_version.num, gfe_version.num)) and
            numpy.all(numpy.in1d(nengo_version.den, gfe_version.den)))


def _create_map_between_nengo_spinnaker_and_gfe_filters():
    mappable = dict()
    mappable[NoneFilter] = GFENoneFilter
    mappable[LowpassFilter] = GFELowPassFilter
    mappable[LinearFilter] = GFELinearFilter
    return mappable


def _compare_filters(nengo_filter, gfe_filter):
    # mappings = _create_map_between_nengo_spinnaker_and_gfe_filters()
    return nengo_filter == gfe_filter
    # seems these are not the filters i thought they were...... might be
    # worth keeping for future comparision
    """if isinstance(gfe_filter, mappings[type(nengo_filter)]):
        if isinstance(gfe_filter, GFENoneFilter):
            return _compare_none_filters(nengo_filter, gfe_filter)
        elif isinstance(gfe_filter, GFELowPassFilter):
            return _compare_low_pass_filters(nengo_filter, gfe_filter)
        elif isinstance(gfe_filter, GFELinearFilter):
            return _compare_linear_filters(nengo_filter, gfe_filter)
        else:
            raise Exception("should never reach a unknown filter class")
    else:
        raise Exception("the filter types dont match")"""


def _compare_param_transform(nengo_version, gfe_version):

    if (nengo_version.size_in == gfe_version.size_in and
            nengo_version.size_out == gfe_version.size_out and
            numpy.all(numpy.in1d(
                nengo_version.slice_in, gfe_version.slice_in)) and
            numpy.all(
                numpy.in1d(nengo_version.slice_out, gfe_version.slice_out))):
        return True
    else:
        return False


def _compare_pass_through_trans(nengo_version, gfe_version):
    return _compare_param_transform(
        nengo_version._transform, gfe_version.transform)


def _compare_ensemble_trans(nengo_version, gfe_version):
    return (_compare_param_transform(
        nengo_version._transform, gfe_version.transform) and
            numpy.all(numpy.in1d(
                nengo_version.decoders, gfe_version.decoders)) and
        nengo_version.learning_rule == gfe_version.learning_rule)


def _compare_node_trans_params(nengo_version, gfe_version):
    return (_compare_param_transform(
        nengo_version._transform, gfe_version.transform) and
        nengo_version.function == gfe_version.parameter_function and
        nengo_version.pre_slice == gfe_version.pre_slice)


def _compare_transmission_params(nengo_version, gfe_version):
    if isinstance(nengo_version, PassthroughNodeTransmissionParameters):
        return _compare_pass_through_trans(nengo_version, gfe_version)
    elif isinstance(nengo_version, EnsembleTransmissionParameters):
        return _compare_ensemble_trans(nengo_version, gfe_version)
    elif isinstance(nengo_version, NodeTransmissionParameters):
        return _compare_node_trans_params(nengo_version, gfe_version)
    else:
        raise Exception("should never get here")


def _create_map_between_nenego_spinnaker_and_gfe_trans_params():
    mappable = dict()
    mappable[PassthroughNodeTransmissionParameters] = \
        GFEPassthroughNodeTransmissionParameters
    mappable[EnsembleTransmissionParameters] = \
        GFEEnsembleTransmissionParameters
    mappable[NodeTransmissionParameters] = GFENodeTransmissionParameters
    return mappable


def _create_map_between_nengo_spinnaker_and_gfe_verts():
    mappable = dict()
    mappable[Filter] = InterposerApplicationVertex
    mappable[EnsembleLIF] = LIFApplicationVertex
    mappable[SDPReceiver] = SDPReceiverApplicationVertex
    mappable[SDPTransmitter] = SDPTransmitterApplicationVertex
    mappable[ValueSink] = ValueSinkApplicationVertex
    mappable[ValueSource] = ValueSourceApplicationVertex
    mappable[PassthroughNode] = PassThroughApplicationVertex
    mappable[InputNode] = NengoInputNode
    mappable[OutputNode] = NengoOutputNode
    return mappable


def _compare_nengo_spinnaker_and_gfe_enums(nengo_enum, gfe_enum):
    if (isinstance(nengo_enum, OutputPort) and isinstance(
            gfe_enum, constants.OUTPUT_PORT)):
        return nengo_enum.value == gfe_enum.value
    elif (isinstance(nengo_enum, InputPort) and isinstance(
            gfe_enum, constants.INPUT_PORT)):
        return nengo_enum.value == gfe_enum.value
    elif (isinstance(nengo_enum, EnsembleOutputPort) and isinstance(
            gfe_enum, constants.ENSEMBLE_OUTPUT_PORT)):
        return nengo_enum.value == gfe_enum.value
    elif (isinstance(nengo_enum, EnsembleInputPort) and isinstance(
            gfe_enum, constants.ENSEMBLE_INPUT_PORT)):
        return nengo_enum.value == gfe_enum.value
    elif isinstance(nengo_enum, LearningRuleType):
        return (isinstance(gfe_enum, constants.ENSEMBLE_INPUT_PORT) and
                gfe_enum.value ==
                constants.ENSEMBLE_INPUT_PORT.LEARNING_RULE.value)
    else:
        return False


def _check_interposer_app_vertex(nengo_spinnaker_vertex, gfe_nengo_vertex):
    return (nengo_spinnaker_vertex.size_in == gfe_nengo_vertex.size_in and
            nengo_spinnaker_vertex.groups == gfe_nengo_vertex.groups)


def _check_lif_app_vertex(nengo_spinnaker_vertex, gfe_nengo_vertex,
                          nengo_spinnaker_network_builder):
    return (numpy.all(numpy.in1d(
            nengo_spinnaker_network_builder.params[
                nengo_spinnaker_vertex.ensemble].eval_points,
                gfe_nengo_vertex.eval_points)) and
            nengo_spinnaker_network_builder.params[
                nengo_spinnaker_vertex.ensemble].encoders ==
            gfe_nengo_vertex.encoders and
            nengo_spinnaker_vertex.scaled_encoders ==
            gfe_nengo_vertex.scaled_encoders and
            nengo_spinnaker_vertex.max_rates == gfe_nengo_vertex.max_rates and
            nengo_spinnaker_vertex.intercepts ==
            gfe_nengo_vertex.intercepts and
            nengo_spinnaker_vertex.gain == gfe_nengo_vertex.gain and
            nengo_spinnaker_vertex.bias == nengo_spinnaker_vertex.bias)


def _check_pass_though_app_vertex(nengo_spinnaker_vertex, gfe_nengo_vertex):
    return True


def _check_sdp_receiver_app_vertex(nengo_spinnaker_vertex, gfe_nengo_vertex):
    return True


def _check_sdp_transmitter_app_vertex(nengo_spinnaker_vertex, gfe_nengo_vertex):
    return (nengo_spinnaker_vertex.size_in == gfe_nengo_vertex.size_in and
            nengo_spinnaker_vertex.output == gfe_nengo_vertex.output)


def _check_value_sink_app_vertex(nengo_spinnaker_vertex, gfe_nengo_vertex):
    return nengo_spinnaker_vertex.size_in == gfe_nengo_vertex.size_in


def _check_value_source_app_vertex(nengo_spinnaker_vertex, gfe_nengo_vertex):
    return (nengo_spinnaker_vertex.size_out == gfe_nengo_vertex.size_out and
            nengo_spinnaker_vertex.update_period ==
            gfe_nengo_vertex.update_period and
            nengo_spinnaker_vertex.output ==
            gfe_nengo_vertex.nengo_output_function)


def _test_graph_vertices(
        nengo_operators, nengo_to_app_graph_map,
        nengo_spinnaker_network_builder):
    mappings = _create_map_between_nengo_spinnaker_and_gfe_verts()

    for nengo_obj in nengo_operators:
        nengo_spinnaker_vertex = nengo_operators[nengo_obj]
        gfe_nengo_vertex = nengo_to_app_graph_map[nengo_obj]
        if not isinstance(gfe_nengo_vertex, mappings[type(
                nengo_spinnaker_vertex)]):
            raise Exception(
                "nengo_obj {} is not matching nengo_spinnaker vertex {} "
                "with gfe vertex {}".format(
                    nengo_obj, nengo_spinnaker_vertex, gfe_nengo_vertex))
        if isinstance(gfe_nengo_vertex, InterposerApplicationVertex):
            valid = _check_interposer_app_vertex(
                nengo_spinnaker_vertex, gfe_nengo_vertex)
            if not valid:
                return False
        if isinstance(gfe_nengo_vertex, LIFApplicationVertex):
            valid = _check_lif_app_vertex(
                nengo_spinnaker_vertex, gfe_nengo_vertex,
                nengo_spinnaker_network_builder)
            if not valid:
                return False
        if isinstance(gfe_nengo_vertex, PassThroughApplicationVertex):
            pass
        if isinstance(gfe_nengo_vertex, SDPReceiverApplicationVertex):
            valid = _check_sdp_receiver_app_vertex(
                nengo_spinnaker_vertex, gfe_nengo_vertex)
            if not valid:
                return False
        if isinstance(
                gfe_nengo_vertex, SDPTransmitterApplicationVertex):
            valid = _check_sdp_transmitter_app_vertex(
                nengo_spinnaker_vertex, gfe_nengo_vertex)
            if not valid:
                return False
        if isinstance(gfe_nengo_vertex, ValueSinkApplicationVertex):
            valid = _check_value_sink_app_vertex(
                nengo_spinnaker_vertex, gfe_nengo_vertex)
            if not valid:
                return False
        if isinstance(gfe_nengo_vertex, ValueSourceApplicationVertex):
            valid = _check_value_source_app_vertex(
                nengo_spinnaker_vertex, gfe_nengo_vertex)
            if not valid:
                return False
    return True


def _check_rest_of_edge_params(
        nengo_reception_params, nengo_latching_required, nengo_weight,
        nengo_destination_port, gfe_reception_params, gfe_latching_required,
        gfe_weight, gfe_destination_input_port, found_set,
        nengo_transmission_param, gfe_transmission_param):
    if (nengo_latching_required == gfe_latching_required and
            nengo_weight == gfe_weight and
            _compare_nengo_spinnaker_and_gfe_enums(
                nengo_destination_port, gfe_destination_input_port) and
            nengo_reception_params.width == gfe_reception_params.width and
            nengo_reception_params.learning_rule ==
                gfe_reception_params.learning_rule and
            _compare_filters(nengo_reception_params.filter,
                             gfe_reception_params.parameter_filter)):
        found_set[(nengo_transmission_param, nengo_reception_params,
                   nengo_latching_required, nengo_weight,
                   nengo_destination_port)] = True
        found_set[(gfe_transmission_param,  gfe_reception_params,
                   gfe_latching_required, gfe_weight,
                   gfe_destination_input_port)] = True


def _check_partition_destinations(sinks, edge_destinations):
    found = dict()
    for edge_destination in edge_destinations:
        found[edge_destination] = False
    mappings = _create_map_between_nengo_spinnaker_and_gfe_verts()

    for sink in sinks:
        for edge_destination in edge_destinations:
            if isinstance(edge_destination, mappings[type(sink)]):
                valid = False
                if isinstance(edge_destination, InterposerApplicationVertex):
                    valid = _check_interposer_app_vertex(sink, edge_destination)
                elif isinstance(edge_destination, LIFApplicationVertex):
                    valid = _check_lif_app_vertex(sink, edge_destination)
                elif isinstance(edge_destination, PassThroughApplicationVertex):
                    valid = True
                elif isinstance(edge_destination, SDPReceiverApplicationVertex):
                    valid = _check_sdp_receiver_app_vertex(
                        sink, edge_destination)
                elif isinstance(
                        edge_destination, SDPTransmitterApplicationVertex):
                    valid = _check_sdp_transmitter_app_vertex(
                        sink, edge_destination)
                elif isinstance(edge_destination, ValueSinkApplicationVertex):
                    valid = _check_value_sink_app_vertex(
                        sink, edge_destination)
                elif isinstance(edge_destination, ValueSourceApplicationVertex):
                    valid = _check_value_source_app_vertex(
                        sink, edge_destination)
                if valid:
                    found[edge_destination] = True

    for edge_destination in found:
        if not edge_destination:
            return False
    return True


def _check_partition_to_nengo_objects(
        nengo_transmission_parameters, nengo_reception_parameters,
        nengo_latching_requireds, nengo_weights,
        nengo_destination_input_ports, sinks, outgoing_partition):

    # check correct amount of data
    if (len(nengo_transmission_parameters) !=
            len(outgoing_partition.transmission_params)):
        return False

    # check correct number of destinations
    _check_partition_destinations(sinks, outgoing_partition.edge_destinations)

    transmission_parameter_map = \
        _create_map_between_nenego_spinnaker_and_gfe_trans_params()

    # set up param trackers
    found_set = dict()
    for nengo_parameter_tuple in zip(
            nengo_transmission_parameters, nengo_reception_parameters,
            nengo_latching_requireds, nengo_weights,
            nengo_destination_input_ports):
        found_set[nengo_parameter_tuple] = False
    for gfe_parameter_tuple in zip(
            outgoing_partition.transmission_params,
            outgoing_partition.reception_params,
            outgoing_partition.latching_required,
            outgoing_partition.weight,
            outgoing_partition.destination_input_port):
        found_set[gfe_parameter_tuple] = False

    # start search
    for (nengo_transmission_parameter, nengo_reception_parameter,
         nengo_latching_required, nengo_weight, nengo_destination_input_port) \
            in zip(
                nengo_transmission_parameters, nengo_reception_parameters,
                nengo_latching_requireds, nengo_weights,
                nengo_destination_input_ports):
        for gfe_transmission_param in \
                outgoing_partition.transmission_params:
            if isinstance(
                    gfe_transmission_param,
                    transmission_parameter_map[
                        type(nengo_transmission_parameter)]):
                match = _compare_transmission_params(
                    nengo_transmission_parameter, gfe_transmission_param)
                if match:
                    index_of_params = \
                        outgoing_partition.transmission_params.index(
                            gfe_transmission_param)
                    _check_rest_of_edge_params(
                        nengo_reception_params=nengo_reception_parameter,
                        nengo_latching_required=nengo_latching_required,
                        nengo_weight=nengo_weight,
                        nengo_destination_port=nengo_destination_input_port,
                        gfe_reception_params=outgoing_partition.
                        reception_params[index_of_params],
                        gfe_latching_required=outgoing_partition.
                        latching_required[index_of_params],
                        gfe_weight=outgoing_partition.weight[
                            index_of_params],
                        gfe_destination_input_port=outgoing_partition.
                        destination_input_port[index_of_params],
                        found_set=found_set,
                        gfe_transmission_param=gfe_transmission_param,
                        nengo_transmission_param=nengo_transmission_parameter)
    for found_value in found_set:
        if not found_value:
            return False
    return True


def _test_graph_edges(
        connection_map, app_graph, nengo_operators, nengo_to_app_graph_map):
    for connection_source_vertex in connection_map._connections:
        found = None
        for nengo_vertex in nengo_operators:
            if nengo_operators[nengo_vertex] == connection_source_vertex:
                found = nengo_vertex
        app_vertex = nengo_to_app_graph_map[found]
        gfe_partitions = app_graph.\
            get_outgoing_edge_partitions_starting_at_vertex(app_vertex)
        nengo_spinnaker_connections = \
            connection_map._connections[connection_source_vertex]
        if len(nengo_spinnaker_connections) != len(gfe_partitions):
            raise Exception("for vertex {}. there is a mismatch of "
                            "channels.".format(connection_source_vertex))

        # flagger for seeing if we found all mapped objects.
        overall_found = dict()
        for channel_identifier in nengo_spinnaker_connections:
            overall_found[channel_identifier] = False
        for outgoing_partition in gfe_partitions:
            overall_found[outgoing_partition] = False

        # find each one
        for channel_identifier in nengo_spinnaker_connections:
            nengo_spinnaker_edge_data = \
                nengo_spinnaker_connections[channel_identifier]
            for outgoing_partition in gfe_partitions:
                if _compare_nengo_spinnaker_and_gfe_enums(
                        channel_identifier, outgoing_partition.identifier):

                    # gather all params, so it can be tested against a
                    # outgoing partition
                    transmission_parameters = list()
                    reception_parameters = list()
                    latching_required = list()
                    weight = list()
                    destination_input_port = list()
                    sinks = list()

                    for (signal_params, transmission_params) in \
                            nengo_spinnaker_edge_data.keys():
                        nengo_data = nengo_spinnaker_edge_data[
                            (signal_params, transmission_params)]
                        for (sink_object, input_port, reception_params) in \
                                nengo_data:
                            transmission_parameters.append(transmission_params)
                            reception_parameters.append(reception_params)
                            latching_required.append(signal_params.latching)
                            weight.append(signal_params.weight)
                            destination_input_port.append(input_port)
                            sinks.append(sink_object)

                    # check against outgoing partition
                    found = _check_partition_to_nengo_objects(
                        transmission_parameters, reception_parameters,
                        latching_required, weight, destination_input_port,
                        sinks, outgoing_partition)

                    # if found, update
                    if found:
                        if not overall_found[channel_identifier]:
                            overall_found[channel_identifier] = True
                        else:
                            raise Exception("this channel already been found!")
                        if not overall_found[outgoing_partition]:
                            overall_found[outgoing_partition] = True
                        else:
                            raise Exception(
                                "this outgoing partition already been found!")

        # check we've found everything
        for thing in overall_found:
            if not overall_found[thing]:
                return False
        return True
