import openai
import traceback
from . import pvsecret
import os
from chalicelib.version import API_VERSION
from chalicelib.telemetry import capture_metric, CostMetrics, InfoMetrics
from chalicelib.usage import get_openai_usage, get_boost_cost, OpenAIDefaults
from chalicelib.payments import update_usage_for_code

blueprint_api_version = API_VERSION  # API version is global for now, not service specific
print("blueprint_api_version: ", blueprint_api_version)

secret_json = pvsecret.get_secrets()

# TEMP - put this back to the polyverse key once gpt-4 access is approved there
openai_key = secret_json["openai-personal"]
openai.api_key = openai_key

# Define the directory where prompt files are stored
PROMPT_DIR = "chalicelib/prompts"

# Define the filenames for each prompt file
SEED_PROMPT_FILENAME = "blueprint-seed.prompt"
UPDATE_PROMPT_FILENAME = "blueprint-update.prompt"
ROLE_SYSTEM_FILENAME = "blueprint-role-system.prompt"


# Load the prompt files and replace the placeholders with the actual values
def load_prompts():
    promptdir = os.path.join(os.path.abspath(os.path.curdir), PROMPT_DIR)

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
def blueprint_code(json_data, account, context, correlation_id):

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
    blueprint = response.choices[0].message.content

    # {"customer": customer, "subscription": subscription, "subscription_item": subscription_item, "email": email}
    customer = account['customer']
    email = account['email']

    try:
        # Get the cost of the prompting - so we have visibiity into our cost per user API
        prompt_size = len(prompt) + len(role_system)
        blueprint_size = len(blueprint)
        boost_cost = get_boost_cost(prompt_size + blueprint_size)
        openai_input_tokens, openai_input_cost = get_openai_usage(prompt + role_system)
        openai_customerinput_tokens, openai_customerinput_cost = get_openai_usage(code)
        openai_output_tokens, openai_output_cost = get_openai_usage(blueprint, False)
        openai_tokens = openai_input_tokens + openai_output_tokens
        openai_cost = openai_input_cost + openai_output_cost

        try:
            # update the billing usage for this analysis
            update_usage_for_code(account, prompt + blueprint)
        except Exception:
            exception_info = traceback.format_exc()
            print("UPDATE_USAGE:FAILURE:{}:{}:{}:{}:Error updating ~${} usage: ".format(customer['name'], customer['id'], email, correlation_id, boost_cost), exception_info)
            capture_metric(customer, email, correlation_id, context,
                           {"name": InfoMetrics.BILLING_USAGE_FAILURE, "value": round(boost_cost, 5), "unit": "None"})

            pass  # Don't fail if we can't update usage / but that means we may have lost revenue

        capture_metric(customer, email, correlation_id, context,
                       {'name': CostMetrics.PROMPT_SIZE, 'value': prompt_size, 'unit': 'Count'},
                       {'name': CostMetrics.RESPONSE_SIZE, 'value': blueprint_size, 'unit': 'Count'},
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
        exception_info = traceback.format_exc()
        print(f"{customer['name']}:{customer['id']}:{email}:{correlation_id}:Error capturing metrics: ", exception_info)
        pass  # Don't fail if we can't capture metrics

    return blueprint
