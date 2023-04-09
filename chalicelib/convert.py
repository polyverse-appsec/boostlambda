import openai
from . import pvsecret

secret_json = pvsecret.get_secrets()

# TEMP - put this back to the polyverse key once gpt-4 access is approved there
openai_key = secret_json["openai-personal"]
openai.api_key = openai_key
print("openai key ", openai_key)


# a function to call openai to explain code
def explain_code(code):

    prompt = "Explain this code in detail including the algorithms used:\n\n" + code

    print("calling openai with prompt: " + prompt + "\n\n")
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
        {   "role": "system",
            "content": "I am a code explanation bot. I will explain the code below in detail."
        },
        {
            "role": "user",
            "content": prompt
        }]
    )
    explanation = response.choices[0].message.content
    return explanation


# a function to call openai to generate code from english
def generate_code(summary, original_code, language):

    prompt = "### Generate clean and concise " + language + " code from the summary above, using appropriate " + language + " techniques. Use the original code shown earlier as a reference for variable, data, and function names.\n\n"
    print("calling openai with prompt: " + prompt + "\n\n")
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {
                "role": "system",
                "content": "I am a code generation assistant that can translate code into " + language + ". I generate syntactically correct code and all other information is conveyed as syntactically correct comments."
            },
            {
                "role": "user",
                "content": "Explain this original code:\n\n" + original_code + "\n\n"
            },
            {
                "role": "assistant",
                "content": "Here is the summary:\n\n" + summary + "\n\n"
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )
    generated_code = response.choices[0].message.content

    return generated_code
