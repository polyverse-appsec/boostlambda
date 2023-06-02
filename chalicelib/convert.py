import openai
import traceback
from . import pvsecret
import os
from chalicelib.version import API_VERSION
from chalicelib.telemetry import capture_metric, CostMetrics, InfoMetrics
from chalicelib.usage import get_openai_usage, get_boost_cost, OpenAIDefaults
from chalicelib.payments import update_usage_for_text


explain_api_version = API_VERSION  # API version is global for now, not service specific
convert_api_version = API_VERSION  # API version is global for now, not service specific
print("explain_api_version: ", explain_api_version)
print("convert_api_version: ", convert_api_version)

if 'AWS_CHALICE_CLI_MODE' not in os.environ:

    secret_json = pvsecret.get_secrets()

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


if 'AWS_CHALICE_CLI_MODE' not in os.environ:
    explain_prompt, convert_prompt, role_system, role_user, role_assistant = load_prompts()


# a function to call openai to explain code
def explain_code(data, code, account, function_name, correlation_id):

    prompt = explain_prompt.format(code=code)

    # enable user to override the model to gpt-3 or gpt-4
    model = OpenAIDefaults.boost_default_gpt_model
    if 'model' in data:
        model = data['model']

    params = {
        "model": model,
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

    explanation = response.choices[0].message.content

    # {"customer": customer, "subscription": subscription, "subscription_item": subscription_item, "email": email}
    customer = account['customer']
    email = account['email']

    try:
        # Get the cost of the prompting - so we have visibiity into our cost per user API
        prompt_size = len(prompt) + len(role_system)
        explanation_size = len(explanation)
        boost_cost = get_boost_cost(prompt_size + explanation_size)
        openai_input_tokens, openai_input_cost = get_openai_usage(prompt + role_system)
        openai_customerinput_tokens, openai_customerinput_cost = get_openai_usage(code)
        openai_output_tokens, openai_output_cost = get_openai_usage(explanation, False)
        openai_tokens = openai_input_tokens + openai_output_tokens
        openai_cost = openai_input_cost + openai_output_cost

        try:
            # update the billing usage for this analysis
            update_usage_for_text(account, prompt + explanation)
        except Exception:
            exception_info = traceback.format_exc().replace('\n', ' ')
            print("UPDATE_USAGE:FAILURE:{}:{}:{}:{}:Error updating ~${} usage: ".format(customer['name'], customer['id'], email, correlation_id, boost_cost), exception_info)
            capture_metric(customer, email, function_name, correlation_id,
                           {"name": InfoMetrics.BILLING_USAGE_FAILURE, "value": round(boost_cost, 5), "unit": "None"})

            pass  # Don't fail if we can't update usage / but that means we may have lost revenue

        capture_metric(customer, email, function_name, correlation_id,
                       {'name': CostMetrics.PROMPT_SIZE, 'value': prompt_size, 'unit': 'Count'},
                       {'name': CostMetrics.RESPONSE_SIZE, 'value': explanation_size, 'unit': 'Count'},
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

    return explanation


# a function to call openai to generate code from english
def generate_code(data, summary, original_code, language, account, function_name, correlation_id):

    prompt = convert_prompt.format(summary=summary, original_code=original_code, language=language)
    this_role_system = role_system.format(language=language)
    this_role_user = role_user.format(original_code=original_code)
    this_role_assistant = role_assistant.format(summary=summary)

    # enable user to override the model to gpt-3 or gpt-4
    model = OpenAIDefaults.boost_default_gpt_model
    if 'model' in data:
        model = data['model']

    params = {
        "model": model,
        "messages": [
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
        prompt_size = len(prompt) + len(this_role_assistant) + len(this_role_system) + len(this_role_user)
        generatedcode_size = len(generated_code)
        boost_cost = get_boost_cost(prompt_size + generatedcode_size)
        openai_input_tokens, openai_input_cost = get_openai_usage(prompt + role_system + role_assistant + role_user)
        openai_customerinput_tokens, openai_customerinput_cost = get_openai_usage(original_code)
        openai_output_tokens, openai_output_cost = get_openai_usage(generated_code, False)
        openai_tokens = openai_input_tokens + openai_output_tokens
        openai_cost = openai_input_cost + openai_output_cost

        try:
            # update the billing usage for this analysis
            update_usage_for_text(account, prompt + generated_code)
        except Exception:
            exception_info = traceback.format_exc().replace('\n', ' ')
            print("UPDATE_USAGE:FAILURE:{}:{}:{}:{}:Error updating ~${} usage: ".format(customer['name'], customer['id'], email, correlation_id, boost_cost), exception_info)
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
