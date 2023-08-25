from chalicelib.processors.CustomProcessor import CustomProcessor
from chalice import Chalice

client_version = '0.9.5'

app = Chalice(app_name='boost')


class ContentOptimizationTestProcessor(CustomProcessor):
    def get_chunkable_input(self) -> str:
        return super().get_chunkable_input(self)


contentOptimizerTest = ContentOptimizationTestProcessor()


def test_basic_functionality():
    messages = [{"content": "Hello", "role": "user"}]
    data = {"model": "test_model"}
    optimized_messages, truncated = contentOptimizerTest.optimize_content(messages, data)
    assert len(optimized_messages) == 1
    assert truncated == 0


def test_system_message_unaltered():
    messages = [
        {"content": "Hello", "role": "user"},
        {"content": "System message that is very very long and will be truncated", "role": "system"},
        {"content": "Goodbye", "role": "user"}
    ]
    data = {"model": "test_model"}
    optimized_messages, truncated = contentOptimizerTest.optimize_content(messages, data)
    assert len(optimized_messages) == 3
    assert truncated == 0
    assert len(optimized_messages[1]["content"].split()) == len(messages[1]["content"].split())
