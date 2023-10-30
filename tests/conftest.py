
print("Loading conftest.py")


def pytest_configure(config):
    print("Configuring pytest for boostlambda")
    config.addinivalue_line(
        "markers", "cleanOutput: mark test to sanitize output"
    )
    config.addinivalue_line(
        "markers", "codeInput: mark test to sanitize code input"
    )
