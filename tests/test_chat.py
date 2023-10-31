from chalice.test import Client
import app as app_module
from app import ChatProcessor
import chalicelib.storage

import json
import os

from .test_version import client_version
from .test_utils import warn


# load the data files into a string, relative to the root directory
with open('./tests/data/chat/blueprint.json', 'r') as file:
    blueprint_json = file.read()
    blueprint = json.loads(blueprint_json).get('data')


# load the data files into a string, relative to the root directory
with open('./tests/data/sha512.c', 'r') as file:
    sha512_c = file.read()


def concatenate_object_properties(obj):
    concatenated_string = ""

    for attr_name in dir(obj):
        # Check if the attribute is not a method and not a magic method or system attribute
        if not callable(getattr(obj, attr_name)) and not attr_name.startswith("__"):
            concatenated_string += str(getattr(obj, attr_name))

    return concatenated_string


# load the data files into a string, relative to the root directory
with open('./tests/data/chat/summary.json', 'r') as file:
    summary_json = file.read()
    summary = json.loads(summary_json)
    all_summaries = concatenate_object_properties(summary)


def test_chat():
    with Client(app_module.app) as client:
        request_body = {
            'query': 'What is this project?',
            'summaries': ['system', [blueprint]],
            'session': 'testemail: unittest@polytest.ai',
            'organization': 'polytest.ai',
            'version': client_version
        }

        response = client.lambda_.invoke(
            'chat', request_body)

        assert response.payload['statusCode'] == 200

        print(f"\nResponse:\n\n{response.payload['body']}")

        result = json.loads(response.payload['body'])
        assert result['analysis'] is not None
        if not (("unknown" in result['analysis'].lower()) or ("javascript" in result['analysis'].lower()) or ("credit card" in result['analysis'].lower())):
            warn(lambda: "The analysis result is not what was expected.")
        assert result['account'] is not None
        assert result['account']['email'] == 'unittest@polytest.ai'
        assert result['account']['org'] == 'polytest.ai'


def test_chat_with_code():
    with Client(app_module.app) as client:
        request_body = {
            'code': 'int main() {\n\tprintf("Hello world!");\n\treturn 0;\n}',
            'query': 'What is this code language?',
            'summaries': ['system', [blueprint]],
            'session': 'testemail: unittest@polytest.ai',
            'organization': 'polytest.ai',
            'version': client_version
        }

        response = client.lambda_.invoke(
            'chat', request_body)

        assert response.payload['statusCode'] == 200

        print(f"\nResponse:\n\n{response.payload['body']}")

        result = json.loads(response.payload['body'])
        assert result['analysis'] is not None
        assert ("C" in result['analysis'])

        assert result['account'] is not None
        assert result['account']['email'] == 'unittest@polytest.ai'
        assert result['account']['org'] == 'polytest.ai'


def test_chat_with_local_doc_boost_ignore():
    with Client(app_module.app) as client:
        request_body = {
            'query': 'How do I exclude files from analysis?',
            'summaries': ['system', [blueprint]],
            'session': 'testemail: unittest@polytest.ai',
            'organization': 'polytest.ai',
            'version': client_version
        }

        response = client.lambda_.invoke(
            'chat', request_body)

        assert response.payload['statusCode'] == 200

        print(f"\nResponse:\n\n{response.payload['body']}")

        result = json.loads(response.payload['body'])

        assert result['account'] is not None
        assert result['account']['email'] == 'unittest@polytest.ai'
        assert result['account']['org'] == 'polytest.ai'

        assert result['analysis'] is not None
        assert (".boostignore" in result['analysis'].lower())


def test_chat_with_s3_doc_boost_ignore():
    with Client(app_module.app) as client:
        request_body = {
            'query': 'How do I exclude files from analysis?',
            'summaries': ['system', [blueprint]],
            'session': 'testemail: unittest@polytest.ai',
            'organization': 'polytest.ai',
            'version': client_version
        }

        old_stage = os.environ.get('CHALICE_STAGE', None)
        os.environ['CHALICE_STAGE'] = 'dev'
        try:
            chalicelib.storage.file_contents_cache = {}
            app_module.chatProcessor = ChatProcessor()

            response = client.lambda_.invoke(
                'chat', request_body)

            assert response.payload['statusCode'] == 200

            print(f"\nResponse:\n\n{response.payload['body']}")

            result = json.loads(response.payload['body'])

            assert result['account'] is not None
            assert result['account']['email'] == 'unittest@polytest.ai'
            assert result['account']['org'] == 'polytest.ai'

            assert result['analysis'] is not None
            assert (".boostignore" in result['analysis'].lower())
        finally:
            if old_stage is not None:
                os.environ['CHALICE_STAGE'] = old_stage


def test_chat_with_large_context():
    with Client(app_module.app) as client:
        request_body = {
            'query': 'What is this code language?',
            'context': [{'type': 'userFocus', 'data': sha512_c, 'name': 'activeCode'},
                        {'type': 'projectSummary', 'data': all_summaries, 'name': 'allSummaries'}],
            'session': 'testemail: unittest@polytest.ai',
            'organization': 'polytest.ai',
            'version': client_version
        }

        response = client.lambda_.invoke(
            'chat', request_body)

        assert response.payload['statusCode'] == 200

        print(f"\nResponse:\n\n{response.payload['body']}")

        result = json.loads(response.payload['body'])
        assert result['analysis'] is not None
        assert ("C" in result['analysis'])

        assert result['account'] is not None
        assert result['account']['email'] == 'unittest@polytest.ai'
        assert result['account']['org'] == 'polytest.ai'


def test_chat_with_trained_answer():
    with Client(app_module.app) as client:
        prompt = 'What is this code language?'
        request_body = {
            'query': prompt,
            'context': [{'type': 'userFocus', 'data': sha512_c, 'name': 'activeCode'},
                        {'type': 'projectSummary', 'data': all_summaries, 'name': 'allSummaries'},
                        {'type': 'training', 'data': {'prompt': prompt, 'response': 'The language is COBOL.'}, 'name': 'training'}],
            'session': 'testemail: unittest@polytest.ai',
            'organization': 'polytest.ai',
            'version': client_version
        }

        response = client.lambda_.invoke(
            'chat', request_body)

        assert response.payload['statusCode'] == 200

        print(f"\nResponse:\n\n{response.payload['body']}")

        result = json.loads(response.payload['body'])
        assert result['analysis'] is not None
        assert ("COBOL" in result['analysis'])

        assert result['account'] is not None
        assert result['account']['email'] == 'unittest@polytest.ai'
        assert result['account']['org'] == 'polytest.ai'


def test_chat_with_multiple_trained_answers_first():
    with Client(app_module.app) as client:
        prompt = 'What is this code language?'
        second_prompt = 'What is your name?'
        second_response = 'My name is Sara.'
        request_body = {
            'query': prompt,
            'context': [{'type': 'userFocus', 'data': sha512_c, 'name': 'activeCode'},
                        {'type': 'projectSummary', 'data': all_summaries, 'name': 'allSummaries'},
                        {'type': 'training', 'data': {'prompt': prompt, 'response': 'The language is COBOL.'}, 'name': 'training'},
                        {'type': 'training', 'data': {'prompt': second_prompt, 'response': second_response}, 'name': 'training'}],
            'session': 'testemail: unittest@polytest.ai',
            'organization': 'polytest.ai',
            'version': client_version
        }

        response = client.lambda_.invoke(
            'chat', request_body)

        assert response.payload['statusCode'] == 200

        print(f"\nResponse:\n\n{response.payload['body']}")

        result = json.loads(response.payload['body'])
        assert result['analysis'] is not None
        assert ("COBOL" in result['analysis'])

        assert result['account'] is not None
        assert result['account']['email'] == 'unittest@polytest.ai'
        assert result['account']['org'] == 'polytest.ai'


def test_chat_with_multiple_trained_answers_second():
    with Client(app_module.app) as client:
        prompt = 'What is this code language?'
        second_prompt = 'What is your name?'
        second_response = 'My name is Sara.'
        request_body = {
            'query': second_prompt,
            'context': [{'type': 'userFocus', 'data': sha512_c, 'name': 'activeCode'},
                        {'type': 'projectSummary', 'data': all_summaries, 'name': 'allSummaries'},
                        {'type': 'training', 'data': {'prompt': prompt, 'response': 'The language is COBOL.'}, 'name': 'training'},
                        {'type': 'training', 'data': {'prompt': second_prompt, 'response': second_response}, 'name': 'training'}],
            'session': 'testemail: unittest@polytest.ai',
            'organization': 'polytest.ai',
            'version': client_version
        }

        response = client.lambda_.invoke(
            'chat', request_body)

        assert response.payload['statusCode'] == 200

        print(f"\nResponse:\n\n{response.payload['body']}")

        result = json.loads(response.payload['body'])
        assert result['analysis'] is not None
        assert ("COBOL" in result['analysis'])

        assert result['account'] is not None
        assert result['account']['email'] == 'unittest@polytest.ai'
        assert result['account']['org'] == 'polytest.ai'
