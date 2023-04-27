import openai
from . import pvsecret
import os
from chalicelib.version import API_VERSION
from chalicelib.telemetry import capture_metric, CostMetrics
from chalicelib.usage import get_openai_usage, get_boost_cost, OpenAIDefaults

secret_json = pvsecret.get_secrets()

testgen_api_version = API_VERSION  # API version is global for now, not service specific
print("testgen_api_version: ", testgen_api_version)

# TEMP - put this back to the polyverse key once gpt-4 access is approved there
openai_key = secret_json["openai-personal"]
openai.api_key = openai_key

# Define the directory where prompt files are stored
PROMPT_DIR = "chalicelib/prompts"

# Define the filenames for each prompt file
TESTGEN_PROMPT_FILENAME = "testgen.prompt"
ROLE_SYSTEM_FILENAME = "testgen-role-system.prompt"


# Load the prompt files and replace the placeholders with the actual values
def load_prompts():
    promptdir = os.path.join(os.path.abspath(os.path.curdir), PROMPT_DIR)

    # Load the prompt file for seed
    with open(os.path.join(promptdir, TESTGEN_PROMPT_FILENAME), 'r') as f:
        testgen_prompt = f.read()

    # Load the prompt file for role content
    with open(os.path.join(promptdir, ROLE_SYSTEM_FILENAME), 'r') as f:
        role_system = f.read()

    return testgen_prompt, role_system


testgen_prompt, role_system = load_prompts()


# a function to call openai to generate code from english
def testgen_code(original_code, language, framework, email, context, correlation_id):

    prompt = testgen_prompt.format(original_code=original_code, language=language, framework=framework)

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
        max_tokens=OpenAIDefaults.boost_tuned_max_tokens  # Max is 4000, but we're tuning lower for performance
    )
    generated_code = response.choices[0].message.content

    try:
        # Get the cost of the prompting - so we have visibiity into our cost per user API
        prompt_size = len(prompt) + len(role_system)
        generatedcode_size = len(generated_code)
        boost_cost = get_boost_cost(prompt_size + generatedcode_size)
        openai_input_tokens, openai_input_cost = get_openai_usage(prompt + role_system)
        openai_customerinput_tokens, openai_customerinput_cost = get_openai_usage(original_code)
        openai_output_tokens, openai_output_cost = get_openai_usage(generated_code, False)
        openai_tokens = openai_input_tokens + openai_output_tokens
        openai_cost = openai_input_cost + openai_output_cost

        capture_metric(email, correlation_id, context,
                       {'name': CostMetrics.PROMPT_SIZE, 'value': prompt_size, 'unit': 'Count'},
                       {'name': CostMetrics.RESPONSE_SIZE, 'value': generatedcode_size, 'unit': 'Count'},
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

    return generated_code
