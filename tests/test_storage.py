import pytest
from unittest.mock import patch, Mock, MagicMock
import os
from botocore.exceptions import ClientError

import chalicelib.storage


def test_get_file_from_cache():
    chalicelib.storage.file_contents_cache = {"sample.txt": "This is a cached file."}  # noqa
    assert chalicelib.storage.get_file("sample.txt") == "This is a cached file."


@patch('chalicelib.storage.file_exists_in_s3', return_value=True)
@patch('boto3.client')
def test_get_file_from_s3(mock_client, mock_exists_in_s3):
    os.environ["CHALICE_STAGE"] = "dev"
    chalicelib.storage.file_contents_cache = {}
    s3_mock = Mock()
    s3_mock.get_object.return_value = {'Body': Mock(read=lambda: b"Content from S3")}
    mock_client.return_value = s3_mock

    assert chalicelib.storage.get_file("sample.txt") == "Content from S3"


@patch('chalicelib.storage.file_exists_in_s3', MagicMock(return_value=False))
@patch('builtins.open', side_effect=FileNotFoundError())
def test_get_file_not_found(mock_exists_in_s3):
    os.environ["CHALICE_STAGE"] = "dev"
    with pytest.raises(FileNotFoundError):
        chalicelib.storage.get_file("non_existent_file.txt")


class MockFile:
    def __init__(self, content):
        self.content = content

    def read(self):
        return self.content

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


@patch('chalicelib.storage.file_exists_in_s3', return_value=False)
@patch('builtins.open', side_effect=lambda x, y: MockFile("Local content"))
def test_get_file_from_local(mock_exists_in_s3, mock_open):
    chalicelib.storage.file_contents_cache = {}
    os.environ["CHALICE_STAGE"] = "dev"
    content = chalicelib.storage.get_file("sample.txt")
    assert content == "Local content"


@patch('boto3.client')
def test_file_exists_in_s3_true(mock_client):
    s3_mock = Mock()
    s3_mock.head_object.return_value = True
    mock_client.return_value = s3_mock

    assert chalicelib.storage.file_exists_in_s3("test_bucket", "sample.txt") is True


def mocked_client_error(*args, **kwargs):
    error_response = {
        'Error': {
            'Code': '404',
            'Message': 'Not Found'
        }
    }
    raise ClientError(error_response, 'HeadObject')


@patch('boto3.client')
def test_file_exists_in_s3_false(mock_client):

    s3_mock = Mock()
    s3_mock.head_object.side_effect = mocked_client_error
    mock_client.return_value = s3_mock

    assert chalicelib.storage.file_exists_in_s3(chalicelib.storage.s3_storage_bucket_name, "non_existent_file.txt") is False
