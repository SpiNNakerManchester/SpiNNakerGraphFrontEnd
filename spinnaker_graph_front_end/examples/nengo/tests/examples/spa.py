
import nengo.spa as spa


def create_model():
    D = 16

    model = spa.SPA(seed=1)
    with model:
        model.a = spa.State(dimensions=D)
        model.b = spa.State(dimensions=D)
        model.c = spa.State(dimensions=D)
        model.cortical = spa.Cortical(spa.Actions(
            'c = a+b',
            ))

        model.input = spa.Input(
            a='A',
            b=(lambda t: 'C*~A' if (t%0.1 < 0.05) else 'D*~A'),
            )
    return model, list(), dict()

