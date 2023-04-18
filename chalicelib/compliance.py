import openai
from . import pvsecret

secret_json = pvsecret.get_secrets()

# TEMP - put this back to the polyverse key once gpt-4 access is approved there
openai_key = secret_json["openai-personal"]
openai.api_key = openai_key
print("openai key ", openai_key)


# a function to call openai to check code for data compliance
def compliance_code(code):

    prompt = "Analyze this code for compliance issues related to GDPR, PCI DSS, and HIPAA compliance. For each issue, indicate a severity on a ten point scale, ten being the worse. Explain the compliance issue and if possible, suggest a solution.:\n\n" + code

    print("calling openai with prompt: " + prompt + "\n\n")
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
        {   "role": "system",
            "content": "I am a code explanation bot. I will analyze the code below in detail for compliance issues related to GDPR, PCI DSS, and HIPAA compliance."
        },
        {
            "role": "user",
            "content": prompt
        }]
    )
    explanation = response.choices[0].message.content
    return explanation