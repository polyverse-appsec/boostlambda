import openai
from . import pvsecret

secret_json = pvsecret.get_secrets()

# TEMP - put this back to the polyverse key once gpt-4 access is approved there
openai_key = secret_json["openai-personal"]
openai.api_key = openai_key
print("openai key ", openai_key)


# a function to call openai to evaluate code for coding guidelines
def guidelines_code(code):

    prompt = "You are an Architect for best development practices in an enterprise. Analyze the following code, describe the coding style and patterns used in the code and comments with examples. Identify exceptions to best practice coding guidelines in the code and comments. For any exceptions - explain why the best practice should be used. Where available, provide links to online material detailing each coding guidelines.:\n\n" + code

    print("calling openai with prompt: " + prompt + "\n\n")
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
        {   "role": "system",
            "content": "I am a code explanation bot. I will analyze the code below in detail for coding guidelines, best practices and developer education."
        },
        {
            "role": "user",
            "content": prompt
        }]
    )
    analysis = response.choices[0].message.content
    return analysis
