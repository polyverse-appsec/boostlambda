import openai
from . import pvsecret
import os
from chalicelib.version import API_VERSION
from chalicelib.telemetry import capture_metric, CostMetrics
from chalicelib.usage import get_openai_usage, get_boost_cost, OpenAIDefaults

customprocess_api_version = API_VERSION  # API version is global for now, not service specific
print("customprocess_api_version: ", customprocess_api_version)

secret_json = pvsecret.get_secrets()

# TEMP - put this back to the polyverse key once gpt-4 access is approved there
openai_key = secret_json["openai-personal"]
openai.api_key = openai_key

# Define the directory where prompt files are stored
PROMPT_DIR = "chalicelib/prompts"

# Define the filenames for each prompt file
CUSTOMPROCESS_PROMPT_FILENAME = "customprocess.prompt"
ROLE_SYSTEM_FILENAME = "customprocess-role-system.prompt"


# Load the prompt files and replace the placeholders with the actual values
def load_prompts():
    promptdir = os.path.join(os.path.abspath(os.path.curdir), PROMPT_DIR)

    # Load the prompt file for this kernels
    with open(os.path.join(promptdir, CUSTOMPROCESS_PROMPT_FILENAME), 'r') as f:
        guidelines_prompt = f.read()

    # Load the prompt file for system role
    with open(os.path.join(promptdir, ROLE_SYSTEM_FILENAME), 'r') as f:
        role_system = f.read()

    return guidelines_prompt, role_system


customprocess_prompt, role_system = load_prompts()


# a function to call openai to evaluate code for processing
def customprocess_code(code, customprompt, email, context, correlation_id):

    # if the user-provided prompt includes {code} block, then use that as the prompt
    if ("{{code}}" in customprompt):
        prompt = customprompt.format(code=code, prompt=customprompt)
    # otherwise, use the default prompt to also inject {code} block into the prompt
    else:
        prompt = customprocess_prompt.format(code=code, prompt=customprompt)

    response = openai.ChatCompletion.create(
        model=OpenAIDefaults.boost_default_gpt_model,
        messages=[
            {
                "role": "system",
                "content": role_system
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        max_tokens=OpenAIDefaults.boost_tuned_max_tokens if OpenAIDefaults.boost_tuned_max_tokens != 0 else None
    )
    analysis = response.choices[0].message.content

    try:
        # Get the cost of the prompting - so we have visibiity into our cost per user API
        prompt_size = len(prompt) + len(role_system)
        analysis_size = len(analysis)
        boost_cost = get_boost_cost(prompt_size + analysis_size)
        openai_input_tokens, openai_input_cost = get_openai_usage(prompt + role_system)
        openai_customerinput_tokens, openai_customerinput_cost = get_openai_usage(code) + get_openai_usage(customprompt)
        openai_output_tokens, openai_output_cost = get_openai_usage(analysis, False)
        openai_tokens = openai_input_tokens + openai_output_tokens
        openai_cost = openai_input_cost + openai_output_cost

        capture_metric(email, correlation_id, context,
                       {'name': CostMetrics.PROMPT_SIZE, 'value': prompt_size, 'unit': 'Count'},
                       {'name': CostMetrics.RESPONSE_SIZE, 'value': analysis_size, 'unit': 'Count'},
                       {'name': CostMetrics.OPENAI_INPUT_COST, 'value': round(openai_input_cost, 5), 'unit': 'None'},
                       {'name': CostMetrics.OPENAI_CUSTOMERINPUT_COST, 'value': round(openai_customerinput_cost, 5), 'unit': 'None'},
                       {'name': CostMetrics.OPENAI_OUTPUT_COST, 'value': round(openai_output_cost, 5), 'unit': 'None'},
                       {'name': CostMetrics.OPENAI_COST, 'value': round(openai_cost, 5), 'unit': 'None'},
                       {'name': CostMetrics.BOOST_COST, 'value': round(boost_cost, 5), 'unit': 'None'},
                       {'name': CostMetrics.OPENAI_INPUT_TOKENS, 'value': openai_input_tokens, 'unit': 'Count'},
                       {'name': CostMetrics.OPENAI_CUSTOMERINPUT_TOKENS, 'value': openai_customerinput_tokens, 'unit': 'Count'},
                       {'name': CostMetrics.OPENAI_OUTPUT_TOKENS, 'value': openai_output_tokens, 'unit': 'Count'},
                       {'name': CostMetrics.OPENAI_TOKENS, 'value': openai_tokens, 'unit': 'Count'})

    except Exception as e:
        print("{email}:{correlation_id}:Error capturing metrics: ", e)
        pass  # Don't fail if we can't capture metrics

    return analysis