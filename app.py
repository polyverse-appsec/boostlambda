from chalice import Chalice
from chalicelib.convert import *
from chalicelib.auth import validate_request
from chalice import BadRequestError
from chalicelib.analyze import analyze_code
from chalicelib.testgen import testgen_code

import json

app = Chalice(app_name='boost')


@app.route('/explain', methods=['POST'])
def explain():
    # This is the JSON body the user sent in their POST request.
    json_data = app.current_request.json_body

    is_valid, error = validate_request(app.current_request)

    if not is_valid:
        return error

    #extract the code from the json data
    code = json_data.get('code')

    if code == None:
        raise BadRequestError("Error: please provide a code fragment to explain")
    
    # now call the explain function
    explanation = explain_code(code)

    print("explained code is: " + explanation)

    # put this into a json object
    json_obj = {}
    json_obj["explanation"] = explanation
    #now return the json object in the response
    return json_obj

@app.route('/generate/{language}', methods=['POST'])
def generate(language):

    is_valid, error = validate_request(app.current_request)

    if not is_valid:
        return error

    json_data = app.current_request.json_body
    #parse the request body as json

    print("got to generate with ")
    print(json_data)
    #extract the code from the json data
    explanation = json_data.get('explanation')
    if explanation == None:
        raise BadRequestError("Error: please provide the initial code explanation")
    
    original_code = json_data.get('originalCode')
    if original_code == None:
        raise BadRequestError("Error: please provide the original code")


    # the output language is optional, if not set, then default to python
    outputlanguage = language
    if outputlanguage == None:
        outputlanguage = "python"

    # now call the explain function
    code = generate_code(explanation, original_code, outputlanguage)

    print("generated code is: " + code)

    # put this into a json object
    json_obj = {}
    json_obj["code"] = code
    #now return the json object in the response
    return json_obj

@app.route('/testgen/{language}/{framework}', methods=['POST'])
def testgen(language, framework):

    is_valid, error = validate_request(app.current_request)

    if not is_valid:
        return error

    json_data = app.current_request.json_body
    #parse the request body as json

    print("got to generate with ")
    print(json_data)
    #extract the code from the json data
    
    code = json_data.get('code')
    if code == None:
        raise BadRequestError("Error: please provide the code to write tests for")


    # the output language is optional, if not set, then default to python
    outputlanguage = language
    if outputlanguage == None:
        outputlanguage = "python"

    # the framework is optional, if not set, then default to pytest if the language is python, otherwise default to unittest
    if framework == None:
        if outputlanguage == "python":
            framework = "pytest"
        else:
            framework = "the best framework for " + outputlanguage + " tests"

    # now call the explain function
    testcode = testgen_code(code, outputlanguage, framework)

    print("generated code is: " + testcode)

    # put this into a json object
    json_obj = {}
    json_obj["testcode"] = testcode
    #now return the json object in the response
    return json_obj

@app.route('/analyze', methods=['POST'])
def explain():
    # This is the JSON body the user sent in their POST request.
    json_data = app.current_request.json_body

    is_valid, error = validate_request(app.current_request)

    if not is_valid:
        return error

    #extract the code from the json data
    code = json_data.get('code')

    if code == None:
        raise BadRequestError("Error: please provide a code fragment to explain")
    
    # now call the explain function
    analysis = analyze_code(code)

    print("analyzed code is: " + analysis)

    # put this into a json object
    json_obj = {}
    json_obj["analysis"] = analysis
    #now return the json object in the response
    return json_obj