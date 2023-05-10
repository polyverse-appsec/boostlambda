from chalice.test import Client
from app import app

def test_flowdiagram_no_code():
    with Client(app) as client:
        request_body = {
            'code': 'This is not a code.',
            'session': 'testemail: alex@polytest.ai',
            'organization': 'polytest.ai',
            'version': '0.9.5'
        }
        response = client.lambda_.invoke('flowdiagram', request_body)
        assert response.payload['statusCode'] == 200  # Ensure the request was successful
        # Add further assertions based on expected response

def test_flowdiagram_simple_c_code():
    with Client(app) as client:
        request_body = {
            'code': """
            int main() {
              int a = 5;
              if (a > 0) {
                printf("A is positive");
              } else {
                printf("A is not positive");
              }
              return 0;
            }
            """,
            'session': 'testemail: alex@polytest.ai',
            'organization': 'polytest.ai',
            'version': '0.9.5'
        }
        response = client.lambda_.invoke('flowdiagram', request_body)
        assert response.payload['statusCode'] == 200  # Ensure the request was successful
        # Add further assertions based on expected response

def test_flowdiagram_c_style_comments():
    with Client(app) as client:
        request_body = {
            'code': """
            /* This is a block comment */
            // This is a line comment
            """,
            'session': 'testemail: alex@polytest.ai',
            'organization': 'polytest.ai',
            'version': '0.9.5'
        }
        response = client.lambda_.invoke('flowdiagram', request_body)
        assert response.payload['statusCode'] == 200  # Ensure the request was successful
        # Add further assertions based on expected response
