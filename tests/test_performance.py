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

client_version = '0.9.5'


def check_performance(code, issuesIdentified):
    with Client(app) as client:
        request_body = {
            'code': code,
            'session': 'testemail: unittest@polytest.ai',
            'organization': 'polytest.ai',
            'version': client_version
        }

        response = client.lambda_.invoke(
            'performance', request_body)

        # print(response.payload)
        assert response.payload['statusCode'] == 200

        # body is a JSON string, so parse it into a JSON object and print
        analysis = json.loads(response.payload['body'])

        assert analysis['analysis'] != ''

        for issue in issuesIdentified:

            print(f"Checking for {issue} in analysis")

            if issue in analysis['analysis']:
                print(f"Found {issue} in analysis")

            else:
                print(f"Could not find {issue} in analysis")
                print()
                print(analysis['analysis'])

            assert issue in analysis['analysis']


def test_performance():
    check_performance(concensus_source, ['O(1)', 'O(n)', 'big integer'])

    check_performance(tensorFlow_inefficientuse, ['batch', 'map'])

    check_performance(hadoop_source, ['O(n)', 'lock'])

    check_performance(linear_search, ['O(n)'])

    check_performance(constant_lookup, ['O(1)'])

    check_performance(exponential_fibonacci, ['O(2^n)', 'O(n)', 'memoization'])

    check_performance(linear_fibonacci, ['O(n)', 'O(1)'])
