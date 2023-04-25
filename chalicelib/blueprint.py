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
SEED_PROMPT_FILENAME = "blueprint-seed.prompt"
UPDATE_PROMPT_FILENAME = "blueprint-update.prompt"
ROLE_SYSTEM_FILENAME = "blueprint-role-system.prompt"


# Load the prompt files and replace the placeholders with the actual values
def load_prompts():
    promptdir = os.path.join(os.path.abspath(os.path.curdir), PROMPT_DIR)
    print("promptdir: " + promptdir)

    # Load the prompt file for seed
    with open(os.path.join(promptdir, SEED_PROMPT_FILENAME), 'r') as f:
        seed_prompt = f.read()

    # Load the prompt file for update
    with open(os.path.join(promptdir, UPDATE_PROMPT_FILENAME), 'r') as f:
        update_prompt = f.read()

    # Load the prompt file for system role
    with open(os.path.join(promptdir, ROLE_SYSTEM_FILENAME), 'r') as f:
        role_system = f.read()

    return seed_prompt, update_prompt, role_system


blueprint_seed_prompt, blueprint_update_prompt, role_system = load_prompts()


# a function to call openai to blueprint code for architecture
def blueprint_code(json_data):

    # Extract the code from the json data
    code = json_data['code']

    # Extract the prior blueprint from the json data
    if 'blueprint' in json_data:
        prior_blueprint = json_data['blueprint']
        # If there is no prior blueprint, set the prompt is creating the seed blueprint from the ingested code
        if prior_blueprint is None:
            prompt = blueprint_seed_prompt.format(code=code)
        else:
            prompt = blueprint_seed_prompt.format(code=code, prior_blueprint=prior_blueprint)
    else:
        prompt = blueprint_seed_prompt.format(code=code)

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
    blueprint = response.choices[0].message.content
    return blueprint
