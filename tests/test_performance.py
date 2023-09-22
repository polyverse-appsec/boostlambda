from chalice.test import Client
from app import app
import json

with open('./tests/data/performance/ethereum_consensus.go', 'r') as file:
    concensus_source = file.read()

with open('./tests/data/performance/tensorFlow_inefficientuse.py', 'r') as file:
    tensorFlow_inefficientuse = file.read()

with open('./tests/data/performance/hadoop_commitBlockSynchronization.java', 'r') as file:
    hadoop_source = file.read()

with open('./tests/data/performance/linear_search.py', 'r') as file:
    linear_search = file.read()

with open('./tests/data/performance/linear_fibonacci.py', 'r') as file:
    linear_fibonacci = file.read()

with open('./tests/data/performance/exponential_fibonacci.py', 'r') as file:
    exponential_fibonacci = file.read()

with open('./tests/data/performance/constant_lookup.py', 'r') as file:
    constant_lookup = file.read()

from .test_version import client_version


def check_performance(code, issuesIdentified, use_function=False, issues=0):
    with Client(app) as client:

        if not use_function:
            request_body = {
                'code': code,
                'session': 'testemail: unittest@polytest.ai',
                'organization': 'polytest.ai',
                'version': client_version
            }
            response = client.lambda_.invoke(
                'performance', request_body)
        else:
            request_body = {
                'code': code,
                'inputMetadata': json.dumps({'lineNumberBase': 0}),
                'session': 'testemail: unittest@polytest.ai',
                'organization': 'polytest.ai',
                'version': client_version
            }
            response = client.lambda_.invoke(
                'performance_function', request_body)

        # print(response.payload)
        assert response.payload['statusCode'] == 200

        # body is a JSON string, so parse it into a JSON object
        analysis = json.loads(response.payload['body'])

        if (use_function):
            assert issues == 0 or analysis['status'] == 'bugsfound'

            assert len(analysis['details']) >= issues

            for issue in analysis['details']:
                assert len(issue['bugType']) > 0
                assert issue['severity'] >= 1
                assert issue['lineNumber'] >= 0

        else:

            for issue in issuesIdentified:

                print(f"Checking for {issue} in analysis")

                if issue in analysis['analysis']:
                    print(f"Found {issue} in analysis")

                else:
                    print(f"Could not find {issue} in analysis")
                    print()
                    print(analysis['analysis'])

                assert issue in analysis['analysis']


def test_performance_3rd_party():
    check_performance(concensus_source, ['memory', 'CPU'])

    check_performance(tensorFlow_inefficientuse, ['batch', 'map'])

    check_performance(hadoop_source, ['O(n)', 'lock'])


def test_performance_big_o():
    check_performance(linear_search, ['O(n)'])

    check_performance(constant_lookup, ['O(1)'])

    check_performance(exponential_fibonacci, ['O(2^n)', 'O(n)'])

    check_performance(linear_fibonacci, ['O(n)', 'O(1)'])


def test_performance_function_3rd_party():
    check_performance(tensorFlow_inefficientuse, ['batch', 'map'], True)

    check_performance(hadoop_source, ['O(n)', 'lock'], True)


def test_performance_function_large_3rd_party():
    # this checks if we fail due to chunking bug in processing
    check_performance(concensus_source, ['O(1)', 'O(n)'], True)


def test_performance_function_big_o():

    check_performance(linear_search, ['O(n)'], True)

    check_performance(constant_lookup, ['O(1)'], True, 0)

    check_performance(exponential_fibonacci, ['O(2^n)', 'O(n)'], True)

    check_performance(linear_fibonacci, ['O(n)', 'O(1)'], True)
