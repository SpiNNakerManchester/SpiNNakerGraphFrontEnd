from data_specification.enums import DataType
import numpy
from nengo.builder import connection as nengo_connection_builder
from nengo.exceptions import BuildError
from spinnaker_graph_front_end.examples.nengo.utility_objects.\
    model_wrapper import ModelWrapper


def convert_numpy_array_to_s16_15(values):
    """Convert the given NumPy array of values into fixed point format."""
    # Scale and cast to appropriate int types
    vals = values * DataType.S1615.scale

    # Saturate the values
    vals = numpy.clip(vals, DataType.S1615.min, DataType.S1615.max)

    # **NOTE** for some reason just casting resulted in shape
    # being zeroed on some indeterminate selection of OSes,
    # architectures, Python and Numpy versions"
    return numpy.array(vals, copy=True, dtype=numpy.int32)


def build_decoders_for_nengo_connection(
        nengo_connection, random_number_generator, nengo_to_app_graph_map,
        decoder_cache):
    """
    
    :param nengo_connection: 
    :param random_number_generator: 
    :param nengo_to_app_graph_map: 
    :param decoder_cache: 
    :return: 
    """

    # fudge to support the built in enngo demanding a god object with params
    model = ModelWrapper(nengo_to_app_graph_map, decoder_cache)

    # gets encoders, gains, anf bias's from the application vertex
    encoders = nengo_to_app_graph_map[nengo_connection.pre_obj].encoders
    gain = nengo_to_app_graph_map[nengo_connection.pre_obj].gain
    bias = nengo_to_app_graph_map[nengo_connection.pre_obj].bias

    eval_points = nengo_connection_builder.get_eval_points(
        model, nengo_connection, random_number_generator)

    # TODO Figure out which version this is meant to support and use only that
    # TODO one
    try:
        targets = nengo_connection_builder.get_targets(
            model, nengo_connection, eval_points)
    except:  # yuck
        # nengo <= 2.3.0
        targets = nengo_connection_builder.get_targets(
            model, nengo_connection, eval_points)

    x = numpy.dot(eval_points, encoders.T / nengo_connection.pre_obj.radius)
    e = None
    if nengo_connection.solver.weights:
        e = nengo_to_app_graph_map[
            nengo_connection.post_obj].scaled_encoders.T[
                nengo_connection.post_slice]

        # include transform in solved weights
        targets = nengo_connection_builder.multiply(
            targets, nengo_connection.transform.T)

    try:
        wrapped_solver = model.decoder_cache.wrap_solver(
            nengo_connection_builder.solve_for_decoders)
        try:
            decoders, solver_info = wrapped_solver(
                nengo_connection, gain, bias, x, targets,
                rng=random_number_generator, E=e)
        except TypeError:
            # fallback for older nengo versions
            decoders, solver_info = wrapped_solver(
                nengo_connection.solver, nengo_connection.pre_obj.neuron_type,
                gain, bias, x, targets, rng=random_number_generator, E=e)
    except BuildError:
        raise BuildError(
            "Building {}: 'activities' matrix is all zero for {}. "
            "This is because no evaluation points fall in the firing "
            "ranges of any neurons.".format(
                nengo_connection, nengo_connection.pre_obj))

    return decoders
