from collections import defaultdict

import numpy

from nengo.connection import LearningRule
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
    sdp_transmitter_application_vertex import SDPTransmitterApplicationVertex
from spinnaker_graph_front_end.examples.nengo.application_vertices.\
    value_sink_application_vertex import ValueSinkApplicationVertex
from spinnaker_graph_front_end.examples.nengo.application_vertices.\
    value_source_application_vertex import ValueSourceApplicationVertex
from spinnaker_graph_front_end.examples.nengo.nengo_filters.\
    low_pass_filter import LowPassFilter as GFELowPassFilter
from spinnaker_graph_front_end.examples.nengo.nengo_filters.\
    linear_filter import LinearFilter as GFELinearFilter
from spinnaker_graph_front_end.examples.nengo.nengo_filters.\
    none_filter import NoneFilter as GFENoneFilter
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
            connection_map, app_graph, nengo_operators, nengo_to_app_graph_map,
            nengo_spinnaker_network_builder)


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
    # seems these are not the nengo_filters i thought they were...... might be
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
    if isinstance(gfe_version, GFEPassthroughNodeTransmissionParameters):
        return _compare_param_transform(
            nengo_version._transform, gfe_version.transform)
    return False


def _compare_ensemble_trans(nengo_version, gfe_version):
    if isinstance(gfe_version, GFEEnsembleTransmissionParameters):
        return (_compare_param_transform(
            nengo_version._transform, gfe_version.transform) and
               # numpy.all(numpy.in1d(
               #     nengo_version.decoders, gfe_version.decoders)) and
            nengo_version.learning_rule == gfe_version.learning_rule)
    return False


def _compare_node_trans_params(nengo_version, gfe_version):
    if isinstance(gfe_version, GFENodeTransmissionParameters):
        return (_compare_param_transform(
            nengo_version._transform, gfe_version.transform) and
            nengo_version.function == gfe_version.parameter_function and
            nengo_version.pre_slice == gfe_version.pre_slice)
    else:
        return False


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
    elif isinstance(nengo_enum, LearningRule):
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
    return True

    # TODO if we can somehow fix seeds on both, this would be testable
    """return (numpy.all(numpy.in1d(
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
            nengo_spinnaker_vertex.bias == nengo_spinnaker_vertex.bias)"""


def _check_sdp_transmitter_app_vertex(nengo_spinnaker_vertex, gfe_nengo_vertex):
    return (nengo_spinnaker_vertex.size_in == gfe_nengo_vertex.size_in and
            nengo_spinnaker_vertex.output == gfe_nengo_vertex.output)


def _check_value_sink_app_vertex(nengo_spinnaker_vertex, gfe_nengo_vertex):
    return nengo_spinnaker_vertex.size_in == gfe_nengo_vertex.size_in


def _check_value_source_app_vertex(nengo_spinnaker_vertex, gfe_nengo_vertex):
    basic_values = (
        nengo_spinnaker_vertex.size_out == gfe_nengo_vertex.size_out and
        nengo_spinnaker_vertex.period == gfe_nengo_vertex.update_period)
    output_function_valid = False
    if isinstance(nengo_spinnaker_vertex.function, (numpy.ndarray,
                                                    numpy.generic)):
        output_function_valid = numpy.all(numpy.in1d(
            nengo_spinnaker_vertex.function,
            gfe_nengo_vertex.nengo_output_function))
    else:
        if (nengo_spinnaker_vertex.function ==
                gfe_nengo_vertex.nengo_output_function):
            output_function_valid = True
    return basic_values and output_function_valid

def _check_vert(
        nengo_spinnaker_vertex, gfe_nengo_vertex,
        nengo_spinnaker_network_builder, mappings):
    if not isinstance(gfe_nengo_vertex, mappings[type(
            nengo_spinnaker_vertex)]):
        return False
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
        pass
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


def _test_graph_vertices(
        nengo_operators, nengo_to_app_graph_map,
        nengo_spinnaker_network_builder):
    mappings = _create_map_between_nengo_spinnaker_and_gfe_verts()

    for nengo_obj in nengo_operators:
        nengo_spinnaker_vertex = nengo_operators[nengo_obj]
        gfe_nengo_vertex = nengo_to_app_graph_map[nengo_obj]
        valid = _check_vert(nengo_spinnaker_vertex, gfe_nengo_vertex,
                            nengo_spinnaker_network_builder, mappings)
        if not valid:
            return False
    return True


def _check_reception_params(nengo_reception_params, gfe_reception_params):
    for gfe_reception_param in gfe_reception_params:
        if not (nengo_reception_params.width == gfe_reception_param.width and
                nengo_reception_params.learning_rule ==
                gfe_reception_param.learning_rule and
                _compare_filters(nengo_reception_params.filter,
                                 gfe_reception_param.parameter_filter)):
            return False
    return True


def _create_gfe_port(nengo_enum):
    if isinstance(nengo_enum, OutputPort):
        return constants.OUTPUT_PORT.STANDARD
    elif isinstance(nengo_enum, InputPort):
        return constants.INPUT_PORT.STANDARD
    elif isinstance(nengo_enum, EnsembleOutputPort):
        if nengo_enum.value == constants.ENSEMBLE_OUTPUT_PORT.NEURONS.value:
            return constants.ENSEMBLE_OUTPUT_PORT.NEURONS
        elif nengo_enum.value == constants.ENSEMBLE_OUTPUT_PORT.LEARNT.value:
            return constants.ENSEMBLE_OUTPUT_PORT.LEARNT
        else:
            raise Exception("cant convert enum")
    elif isinstance(nengo_enum, EnsembleInputPort):
        if nengo_enum.value == constants.ENSEMBLE_INPUT_PORT.NEURONS.value:
            return constants.ENSEMBLE_INPUT_PORT.NEURONS
        elif (nengo_enum.value ==
                constants.ENSEMBLE_INPUT_PORT.GLOBAL_INHIBITION.value):
            return constants.ENSEMBLE_INPUT_PORT.GLOBAL_INHIBITION
        elif (nengo_enum.value ==
                constants.ENSEMBLE_INPUT_PORT.LEARNT.value):
            return constants.ENSEMBLE_INPUT_PORT.LEARNT
        else:
            raise Exception("cant convert enum")
    elif isinstance(nengo_enum, LearningRule):
        return constants.ENSEMBLE_INPUT_PORT.LEARNING_RULE
    else:
        raise Exception("cant convert enum")


def _check_partition_to_nengo_objects(
        nengo_mapped_objs, outgoing_partition,
        nengo_spinnaker_network_builder, gfe_app_graph):

    mappings = _create_map_between_nengo_spinnaker_and_gfe_verts()

    # check correct amount of data
    for (source_port, weight, latching, transmission_param) in \
            nengo_mapped_objs:
        if (_compare_nengo_spinnaker_and_gfe_enums(
                source_port, outgoing_partition.identifier.source_port) and
                _compare_transmission_params(
                    transmission_param,
                    outgoing_partition.identifier.transmission_parameter) and
                weight == outgoing_partition.identifier.weight and
                latching == outgoing_partition.identifier.latching_required):
            for (sink_object, reception_params, input_port) in \
                    nengo_mapped_objs[(
                        source_port, weight, latching, transmission_param)]:
                for destination in outgoing_partition.edge_destinations:
                    valid = _check_vert(
                        sink_object, destination, None,
                        nengo_spinnaker_network_builder, mappings)
                    if valid:
                        gfe_equiv_input_port = _create_gfe_port(input_port)

                        # locate the edge linking to this outgoing partition
                        # and input port
                        gfe_reception_params = locate_reception_parameters(
                            gfe_app_graph, outgoing_partition,
                            gfe_equiv_input_port, destination)

                        if _check_reception_params(
                                reception_params, gfe_reception_params):
                            nengo_mapped_objs[
                                (source_port, weight, latching,
                                 transmission_param)][
                                    (sink_object, reception_params,
                                     input_port)] = True
    return nengo_mapped_objs


def locate_reception_parameters(gfe_app_graph, outgoing_partition,
                                destination_input_port, destination_vertex):
    reception_params = list()
    for edge in gfe_app_graph.get_edges_ending_at_vertex_with_partition_name(
            destination_vertex, outgoing_partition.identifier):
        if edge.input_port == destination_input_port:
            reception_params.append(edge.reception_parameters)
    return reception_params


def _test_graph_edges(
        connection_map, app_graph, nengo_operators, nengo_to_app_graph_map,
        nengo_spinnaker_network_builder):
    for connection_source_vertex in connection_map._connections:

        # locate the vertex linked to this connection source vertex
        found = None
        for nengo_vertex in nengo_operators:
            if nengo_operators[nengo_vertex] == connection_source_vertex:
                found = nengo_vertex
        app_vertex = nengo_to_app_graph_map[found]

        # get the linked connections
        gfe_partitions = app_graph.\
            get_outgoing_edge_partitions_starting_at_vertex(app_vertex)
        nengo_spinnaker_connections = \
            connection_map._connections[connection_source_vertex]

        # flagger for seeing if we found all mapped objects.
        overall_found = dict()
        for channel_identifier in nengo_spinnaker_connections:
            overall_found[channel_identifier] = False
        for outgoing_partition in gfe_partitions:
            overall_found[outgoing_partition] = False

        # find each one
        for channel_identifier in nengo_spinnaker_connections:

            number_of_partitions_at_correct_channel_identifier = 0
            for partition in gfe_partitions:
                if _compare_nengo_spinnaker_and_gfe_enums(
                        channel_identifier, partition.identifier.source_port):
                    number_of_partitions_at_correct_channel_identifier += 1

            if (len(nengo_spinnaker_connections[channel_identifier]) !=
                    number_of_partitions_at_correct_channel_identifier):
                raise Exception("for vertex {}. there is a mismatch of "
                                "channels.".format(connection_source_vertex))

            nengo_spinnaker_edge_data = \
                nengo_spinnaker_connections[channel_identifier]

            # gather all params, so it can be tested against a
            # outgoing partition
            nengo_mapped_objs = defaultdict(dict)

            for (signal_params, transmission_parameter) in \
                    nengo_spinnaker_edge_data.keys():
                nengo_data = nengo_spinnaker_edge_data[
                    (signal_params, transmission_parameter)]
                for (sink_object, input_port, reception_params) in \
                        nengo_data:
                    nengo_mapped_objs[(channel_identifier,
                          signal_params.weight,
                          signal_params.latching,
                          transmission_parameter)][
                        (sink_object, reception_params,
                         input_port)] = False

                for outgoing_partition in gfe_partitions:
                    if _compare_nengo_spinnaker_and_gfe_enums(
                            channel_identifier,
                            outgoing_partition.identifier.source_port):

                        # check against outgoing partition
                        nengo_mapped_objs = _check_partition_to_nengo_objects(
                            nengo_mapped_objs, outgoing_partition,
                            nengo_spinnaker_network_builder, app_graph)

        # check we've found everything
        for first_key in nengo_mapped_objs:
            for second_key in nengo_mapped_objs[first_key]:
                if not nengo_mapped_objs[first_key][second_key]:
                    return False
    return True
