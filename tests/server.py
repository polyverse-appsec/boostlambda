import http.server
import json
from chalice.test import Client
import os
import sys
from urllib.parse import urlparse

# Determine the parent directory's path.
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Append the parent directory to sys.path.
sys.path.append(parent_dir)

# Import the app module from the parent directory - needs to happen after the parent directory is appended to sys.path.
from app import app # noqa


class MyRequestHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        # Parse the URL to extract the verb.
        parsed_url = urlparse(self.path)
        verb = parsed_url.path.strip('/').split('/')[0]

        # Read and parse the JSON data from the request body.
        content_length = int(self.headers['Content-Length'])
        request_body = self.rfile.read(content_length)
        json_data = json.loads(request_body) if request_body else {}

        # Check if the verb is a valid Lambda function in the Chalice app.
        # print the app.routes and app functions
        # print(app.routes)
        # print(app.pure_lambda_functions)

        # Check if the verb is a valid Lambda function in the Chalice app.
        lambda_function_names = [func.name for func in app.pure_lambda_functions]
        if verb in lambda_function_names:
            # Use the Chalice test client to invoke the corresponding Lambda function.
            with Client(app) as client:
                # no way to pass HTTP headers through Client invoke, so we convert to json payload
                user_agent = ''
                for key, value in self.headers.items():
                    if key == 'User-Agent':
                        user_agent = value
                        break
                json_data['version'] = user_agent

                response = client.lambda_.invoke(verb, json_data)

            # debug only local code for payload
            # print('response payload\n' + response.payload["body"])

            # Convert the response to a JSON-formatted string if it's not already a string.
            response_str = json.dumps(response.payload["body"]) if not isinstance(response.payload["body"], str) else response.payload["body"]

            # Send the response back to the client.
            self.send_response(200)
            headers = response.payload["headers"]
            for header_name, header_value in headers.items():
                self.send_header(header_name, header_value)
            self.end_headers()
            self.wfile.write(response_str.encode())
        else:
            self.send_response(404)
            self.end_headers()


def run(server_class=http.server.HTTPServer, handler_class=MyRequestHandler):
    server_address = ('', 8000)
    httpd = server_class(server_address, handler_class)
    print('Starting HTTP server on port 8000...')
    httpd.serve_forever()


if __name__ == '__main__':
    try:
        run()
    except KeyboardInterrupt:
        print('Stopping HTTP server...')
        sys.exit(0)
