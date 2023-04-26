import openai
from . import pvsecret
import os
from chalicelib.version import API_VERSION

secret_json = pvsecret.get_secrets()

explain_api_version = API_VERSION  # API version is global for now, not service specific
convert_api_version = API_VERSION  # API version is global for now, not service specific
print("explain_api_version: ", explain_api_version)
print("convert_api_version: ", convert_api_version)

# TEMP - put this back to the polyverse key once gpt-4 access is approved there
openai_key = secret_json["openai-personal"]
openai.api_key = openai_key

# Define the directory where prompt files are stored
PROMPT_DIR = "chalicelib/prompts"

# Define the filenames for each prompt file
EXPLAIN_PROMPT_FILENAME = "explain.prompt"
CONVERT_PROMPT_FILENAME = "convert.prompt"
ROLE_SYSTEM_FILENAME = "convert-role-system.prompt"
ROLE_USER_FILENAME = "convert-role-user.prompt"
ROLE_ASSISTANT_FILENAME = "convert-role-assistant.prompt"


# Load the prompt files and replace the placeholders with the actual values
def load_prompts():
    promptdir = os.path.join(os.path.abspath(os.path.curdir), PROMPT_DIR)

    # Load the prompt file
    with open(os.path.join(promptdir, EXPLAIN_PROMPT_FILENAME), 'r') as f:
        explain_prompt = f.read()

    with open(os.path.join(promptdir, CONVERT_PROMPT_FILENAME), 'r') as f:
        convert_prompt = f.read()

    # Load the prompt file for system role
    with open(os.path.join(promptdir, ROLE_SYSTEM_FILENAME), 'r') as f:
        role_system = f.read()

    # Load the prompt file for user role
    with open(os.path.join(promptdir, ROLE_USER_FILENAME), 'r') as f:
        role_user = f.read()

    # Load the prompt file for assistant role
    with open(os.path.join(promptdir, ROLE_ASSISTANT_FILENAME), 'r') as f:
        role_assistant = f.read()

    return explain_prompt, convert_prompt, role_system, role_user, role_assistant


explain_prompt, convert_prompt, role_system, role_user, role_assistant = load_prompts()


# a function to call openai to explain code
def explain_code(code):

    prompt = explain_prompt.format(code=code)

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


# a function to call openai to generate code from english
def generate_code(summary, original_code, language):

    prompt = convert_prompt.format(summary=summary, original_code=original_code, language=language)
    this_role_system = role_system.format(language=language)
    this_role_user = role_user.format(original_code=original_code)
    this_role_assistant = role_assistant.format(summary=summary)

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {
                "role": "system",
                "content": this_role_system
            },
            {
                "role": "user",
                "content": this_role_user
            },
            {
                "role": "assistant",
                "content": this_role_assistant
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
    )
    generated_code = response.choices[0].message.content

    return generated_code
