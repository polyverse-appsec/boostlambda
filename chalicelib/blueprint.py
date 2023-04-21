import openai
from . import pvsecret

secret_json = pvsecret.get_secrets()

# TEMP - put this back to the polyverse key once gpt-4 access is approved there
openai_key = secret_json["openai-personal"]
openai.api_key = openai_key
print("openai key ", openai_key)


# a function to call openai to blueprint code for architecture
def blueprint_code(json_data):

    # Extract the code from the json data
    code = json_data['code']

    # Extract the prior blueprint from the json data
    if 'blueprint' in json_data:
        prior_blueprint = json_data['blueprint']
        # If there is no prior blueprint, set the prompt is creating the seed blueprint from the ingested code
        if prior_blueprint is None:
            prompt = "You are an Architect for a software project. For the following code, please produce Architectural Summary such as:\n\n\n```\n* kind of software project for this code: web app, server code, cloud web service, mobile app, shared library, etc.\n* definition of software principles used in the code: multi-threaded, event-driven, data transformation, server processing, client app code, etc\n* how is data stored: shared memory, disk, database, SQL vs NoSQL, non-persisted\n* how is security handled: encrypted vs non-encrypted data, \n* how is performance handled: multi-threaded, non-blocking code, extra optimized, background tasks, CPU bound processing, etc.\n* describe software resiliency pattern in this software: fail fast, defensive code, error logging, etc.\n* analysis of the architectural soundness and best practices: \n* abnormalities in the architecture identified: coarse locks in multi-threaded, global and shared memory in library, UI in a non-interactive server, versioning fragility, etc.\n* terse short summary of the above that can be used as a reference for analyzing other code in this codebase\n\nUse the following sample code from a software project to create the Architectural Summary of the overall project.```\n\n" + code
        else:
            prompt = "You are an Architect for a software project. Based on samples of software code files in a project, you produce architectural summaries of the overall project in the following format:\n\n\n```\n* kind of software project for this code: web app, server code, cloud web service, mobile app, shared library, etc.\n* definition of software principles used in the code: multi-threaded, event-driven, data transformation, server processing, client app code, etc\n* how is data stored: shared memory, disk, database, SQL vs NoSQL, non-persisted\n* how is security handled: encrypted vs non-encrypted data, \n* how is performance handled: multi-threaded, non-blocking code, extra optimized, background tasks, CPU bound processing, etc.\n* describe software resiliency pattern in this software: fail fast, defensive code, error logging, etc.\n* analysis of the architectural soundness and best practices: \n* abnormalities in the architecture identified: coarse locks in multi-threaded, global and shared memory in library, UI in a non-interactive server, versioning fragility, etc.\n* terse short summary of the above that can be used as a reference for analyzing other code in this codebase\n```\n\nYou previously analyzed sample code in this software project and generated this project-level Architectural Summary as follows:" + prior_blueprint + "\n```\n\nNow, you are analyzing the following code from this same software project. You may update your previously generated Architectural Summary of this project as needed. Note that you can add additional aspects to the overall architecture, and you can clarify prior assumptions. But you should not remove prior architectural aspects from the prior generated Architectural Summary. And the final Architectural Summary should remain high-level, not specific to any one function.\n\nThe new code sample follows:\n\n```\n" + code
    else:
        prompt = "You are an Architect for a software project. For the following code, please produce Architectural Summary such as:\n\n\n```\n* kind of software project for this code: web app, server code, cloud web service, mobile app, shared library, etc.\n* definition of software principles used in the code: multi-threaded, event-driven, data transformation, server processing, client app code, etc\n* how is data stored: shared memory, disk, database, SQL vs NoSQL, non-persisted\n* how is security handled: encrypted vs non-encrypted data, \n* how is performance handled: multi-threaded, non-blocking code, extra optimized, background tasks, CPU bound processing, etc.\n* describe software resiliency pattern in this software: fail fast, defensive code, error logging, etc.\n* analysis of the architectural soundness and best practices: \n* abnormalities in the architecture identified: coarse locks in multi-threaded, global and shared memory in library, UI in a non-interactive server, versioning fragility, etc.\n* terse short summary of the above that can be used as a reference for analyzing other code in this codebase\n\nUse the following sample code from a software project to create the Architectural Summary of the overall project.```\n\n" + code

    print("calling openai with prompt: " + prompt + "\n\n")

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
        {   "role": "system",
            "content": "I am a code explanation bot. I will analyze the code below to help build an architectural summary of the overall software project that contains this code."
        },
        {
            "role": "user",
            "content": prompt
        }]
    )
    blueprint = response.choices[0].message.content
    return blueprint
