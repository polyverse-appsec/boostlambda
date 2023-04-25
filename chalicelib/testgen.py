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
TESTGEN_PROMPT_FILENAME = "testgen.prompt"
ROLE_SYSTEM_FILENAME = "testgen-role-system.prompt"


# Load the prompt files and replace the placeholders with the actual values
def load_prompts():
    promptdir = os.path.join(os.path.abspath(os.path.curdir), PROMPT_DIR)
    print("promptdir: " + promptdir)

    # Load the prompt file for seed
    with open(os.path.join(promptdir, TESTGEN_PROMPT_FILENAME), 'r') as f:
        testgen_prompt = f.read()

    # Load the prompt file for role content
    with open(os.path.join(promptdir, ROLE_SYSTEM_FILENAME), 'r') as f:
        role_system = f.read()

    return testgen_prompt, role_system


testgen_prompt, role_system = load_prompts()


# a function to call openai to generate code from english
def testgen_code(original_code, language, framework):

    prompt = testgen_prompt.format(original_code=original_code, language=language, framework=framework)

    print("calling openai with prompt: " + prompt + "\n\n")
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {
                "role": "system",
                "content": role_system
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )
    generated_code = response.choices[0].message.content

    return generated_code
