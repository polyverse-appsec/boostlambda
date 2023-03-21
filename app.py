from chalice import Chalice
#from chalicelib.convert import *
#from chalicelib.auth import validate_github_session
import openai
import json
app = Chalice(app_name='boost')


@app.route('/')
def index():
    return {'hello': 'world'}

@app.route('/explain', methods=['POST'])
def explain():
    # This is the JSON body the user sent in their POST request.
    json_data = app.current_request.json_body


#    if not validate_request(request):
#        return Response("Error: you are not authorized to use this API, please visit https://polyverse.com to sign up")

    #parse the request body as json
    try:
        json_data = json.loads(request.body.decode('utf-8'))
    except ValueError:
        return {"error": "Error: invalid JSON data"}

    #extract the code from the json data
    code = json_data.get('code')

    if code == None:
        return {"error": "Error: please provide a code fragment"}
    
    # now call the explain function
    explanation = explain_code(code)

    print("explained code is: " + explanation)

    # put this into a json object
    json_obj = {}
    json_obj["explanation"] = explanation
    #now return the json object in the response
    return json_obj

# The view function above will return {"hello": "world"}
# whenever you make an HTTP GET request to '/'.
#
# Here are a few more examples:
#
# @app.route('/hello/{name}')
# def hello_name(name):
#    # '/hello/james' -> {"hello": "james"}
#    return {'hello': name}
#
# @app.route('/users', methods=['POST'])
# def create_user():
#     # This is the JSON body the user sent in their POST request.
#     user_as_json = app.current_request.json_body
#     # We'll echo the json body back to the user in a 'user' key.
#     return {'user': user_as_json}
#
# See the README documentation for more examples.
#
