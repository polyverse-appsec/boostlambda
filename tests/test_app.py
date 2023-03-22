from chalice.test import Client
from app import app
import json

def test_explain():
    with Client(app) as client:
        request_body = {
            'code': 'print("Hello, World!")',
            'session': 'testemail: alex@gounares.com'
        }
        response = client.http.post('/explain', headers={'Content-Type': 'application/json'}, body=json.dumps(request_body))
        assert response.status_code == 200
        # Add any additional assertions based on the expected response data

def test_generate_outputlanguage():
    with Client(app) as client:
        output_language = 'python'  # Replace this with the desired output language
        request_body = {
            'explanation': 'This is a simple program that prints "Hello, World!" to the console.',
            'originalCode': 'print("Hello, World!")',
            'session': 'testemail: alex@gounares.com'
        }
        response = client.http.post(f'/generate/{output_language}', headers={'Content-Type': 'application/json'}, body=json.dumps(request_body))
        assert response.status_code == 200
        # Add any additional assertions based on the expected response data


# test the authentication with the session parameter
def test_auth():
    with Client(app) as client:
        request_body = {
            'session': 'testemail: foo@bar.com',
            'code': 'print("Hello, World!")'
        }
        response = client.http.post('/explain', headers={'Content-Type': 'application/json'}, body=json.dumps(request_body))
        #print the response json
        print(response.json_body)
        assert response.status_code == 401

        # now test with an email of alexgo@gmail.com
        request_body = {
            'session': 'testemail: alexgo@gmail.com',
            'code': 'print("Hello, World!")'
        }  
        response = client.http.post('/explain', headers={'Content-Type': 'application/json'}, body=json.dumps(request_body))
        #print the response json
        print(response.json_body)
        assert response.status_code == 401
        
        # now test with an email of jkthecjer@gmail.com
        request_body = {
            'session': 'testemail: jkthecjer@gmail.com',
            'code': 'print("Hello, World!")'
        }  
        response = client.http.post('/explain', headers={'Content-Type': 'application/json'}, body=json.dumps(request_body))
        #print the response json
        print(response.json_body)
        assert response.status_code == 200

        # now test with an email of alex@darklight.ai
        request_body = {
            'session': 'testemail: alex@darklight.ai',
            'code': 'print("Hello, World!")'
        }  
        response = client.http.post('/explain', headers={'Content-Type': 'application/json'}, body=json.dumps(request_body))
        #print the response json
        print(response.json_body)
        assert response.status_code == 200


    