import inspect


def warn(condition_fn):
    condition_str = inspect.getsource(condition_fn).split(":")[1].strip()

    if not condition_fn():
        print(f"TEST WARNING: {condition_str}")
    else:
        print(f"TEST SUCCESS: {condition_str}")
