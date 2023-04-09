import openai
from . import pvsecret

secret_json = pvsecret.get_secrets()

# TEMP - put this back to the polyverse key once gpt-4 access is approved there
openai_key = secret_json["openai-personal"]
openai.api_key = openai_key
print("openai key ", openai_key)


# a function to call openai to generate code from english
def testgen_code(original_code, language, framework):

    prompt = "### Generate " + language + " test code from the code shown here, using the " + framework + " for " + language + ". Here the code to test: \n\n" + original_code + "\n\n"
    print("calling openai with prompt: " + prompt + "\n\n")
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {
                "role": "system",
                "content": "I am a code generation assistant that can generate " + language + "test code. I generate syntactically correct code."
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )
    generated_code = response.choices[0].message.content

    return generated_code
