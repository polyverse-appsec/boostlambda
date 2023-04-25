import openai
from . import pvsecret
import os

secret_json = pvsecret.get_secrets()

# TEMP - put this back to the polyverse key once gpt-4 access is approved there
openai_key = secret_json["openai-personal"]
openai.api_key = openai_key
print("openai key ", openai_key)

# Define the directory where prompt files are stored
PROMPT_DIR = "chalicelib/prompts"

# Define the filenames for each prompt file
COMPLIANCE_PROMPT_FILENAME = "compliance.prompt"
ROLE_SYSTEM_FILENAME = "compliance-role-system.prompt"


# Load the prompt files and replace the placeholders with the actual values
def load_prompts():
    promptdir = os.path.join(os.path.abspath(os.path.curdir), PROMPT_DIR)
    print("promptdir: " + promptdir)

    # Load the prompt file for seed
    with open(os.path.join(promptdir, COMPLIANCE_PROMPT_FILENAME), 'r') as f:
        guidelines_prompt = f.read()

    # Load the prompt file for role content
    with open(os.path.join(promptdir, ROLE_SYSTEM_FILENAME), 'r') as f:
        role_system = f.read()

    return guidelines_prompt, role_system


compliance_prompt, role_system = load_prompts()


# a function to call openai to check code for data compliance
def compliance_code(code):

    prompt = compliance_prompt.format(code=code)

    print("calling openai with prompt: " + prompt + "\n\n")
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
        {   "role": "system",
            "content": role_system
        },
        {
            "role": "user",
            "content": prompt
        }]
    )
    explanation = response.choices[0].message.content
    return explanation
