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
ANALYZE_PROMPT_FILENAME = "analyze.prompt"
ROLE_SYSTEM_FILENAME = "analyze-role-system.prompt"


# Load the prompt files and replace the placeholders with the actual values
def load_prompts():
    promptdir = os.path.join(os.path.abspath(os.path.curdir), PROMPT_DIR)
    print("promptdir: " + promptdir)

    # Load the prompt file for analyze
    with open(os.path.join(promptdir, ANALYZE_PROMPT_FILENAME), 'r') as f:
        analyze_prompt = f.read()

    # Load the prompt file for system role
    with open(os.path.join(promptdir, ROLE_SYSTEM_FILENAME), 'r') as f:
        role_system = f.read()

    return analyze_prompt, role_system


analyze_prompt, role_system = load_prompts()


# a function to call openai to explain code
def analyze_code(code):

    prompt = analyze_prompt.format(code=code)

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
