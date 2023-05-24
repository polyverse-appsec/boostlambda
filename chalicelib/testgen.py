import openai
import traceback
from . import pvsecret
import os
from chalicelib.version import API_VERSION
from chalicelib.telemetry import capture_metric, CostMetrics, InfoMetrics
from chalicelib.usage import get_openai_usage, get_boost_cost, OpenAIDefaults
from chalicelib.payments import update_usage_for_text

testgen_api_version = API_VERSION  # API version is global for now, not service specific
print("testgen_api_version: ", testgen_api_version)

if 'AWS_CHALICE_CLI_MODE' not in os.environ:

    secret_json = pvsecret.get_secrets()

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


if 'AWS_CHALICE_CLI_MODE' not in os.environ:
    testgen_prompt, role_system = load_prompts()


# a function to call openai to generate code from english
def testgen_code(data, original_code, language, framework, account, function_name, correlation_id):

    prompt = testgen_prompt.format(original_code=original_code, language=language, framework=framework)

    params = {
        "model": OpenAIDefaults.boost_default_gpt_model,
        "messages": [
            {
                "role": "system",
                "content": role_system
            },
            {
                "role": "user",
                "content": prompt
            }
        ]}

    if OpenAIDefaults.boost_tuned_max_tokens != 0:
        params["max_tokens"] = OpenAIDefaults.boost_tuned_max_tokens

    if 'top_p' in data:
        params["top_p"] = float(data['top_p'])
    elif 'temperature' in data:
        params["temperature"] = float(data['temperature'])

    try:
        response = openai.ChatCompletion.create(**params)
    except Exception as e:
        # check exception type for OpenAI rate limiting on API calls
        if isinstance(e, openai.error.RateLimitError):
            # if we hit the rate limit, send a cloudwatch alert and raise the error
            capture_metric(account['customer'], account['email'], function_name, correlation_id,
                           {"name": InfoMetrics.OPENAI_RATE_LIMIT, "value": 1, "unit": "None"})

        raise e
    generated_code = response.choices[0].message.content

    # {"customer": customer, "subscription": subscription, "subscription_item": subscription_item, "email": email}
    customer = account['customer']
    email = account['email']

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

        try:
            # update the billing usage for this analysis
            update_usage_for_text(account, prompt + generated_code)
        except Exception:
            exception_info = traceback.format_exc().replace('\n', ' ')
            print(f"UPDATE_USAGE:FAILURE:{customer['name']}:{customer['id']}:{email}:{correlation_id}:Error updating ~${boost_cost} usage: ", exception_info)
            capture_metric(customer, email, function_name, correlation_id,
                           {"name": InfoMetrics.BILLING_USAGE_FAILURE, "value": round(boost_cost, 5), "unit": "None"})

            pass  # Don't fail if we can't update usage / but that means we may have lost revenue

        capture_metric(customer, email, function_name, correlation_id,
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

    except Exception:
        exception_info = traceback.format_exc().replace('\n', ' ')
        print(f"{customer['name']}:{customer['id']}:{email}:{correlation_id}:Error capturing metrics: ", exception_info)
        pass  # Don't fail if we can't capture metrics

    return generated_code
