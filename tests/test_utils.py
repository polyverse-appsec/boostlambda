import inspect
import os

import builtins
import datetime

# when running under vscode debugger, all print() calls in the product and test code will print with timestamp
if 'VSCODE_PID' in os.environ:
    def print_with_timestamp(*args, **kwargs):
        builtins._print(f'[{datetime.datetime.now()}]', *args, **kwargs)

    print("VSCode detected, OVERRIDING builtin print() with custom print with timestamp")

    builtins._print = builtins.print
    builtins.print = print_with_timestamp


def warn(condition_fn):
    condition_str = inspect.getsource(condition_fn).split(":")[1].strip()

    if not condition_fn():
        print(f"TEST WARNING: {condition_str}")
    else:
        print(f"TEST SUCCESS: {condition_str}")
