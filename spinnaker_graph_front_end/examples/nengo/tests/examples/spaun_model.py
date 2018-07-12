import run_spaun


def create_model():
    args, max_probe_time, _ = run_spaun.set_defaults()
    model, _, _, _, _, _, _, _ = run_spaun.create_spaun_model(
        0, args, max_probe_time)
    return model, list(), dict()
