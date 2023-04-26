import openai
from . import pvsecret
import os
from chalicelib.version import API_VERSION
from chalicelib.telemetry import cw_client

compliance_api_version = API_VERSION  # API version is global for now, not service specific
print("compliance_api_version: ", compliance_api_version)

secret_json = pvsecret.get_secrets()

# TEMP - put this back to the polyverse key once gpt-4 access is approved there
openai_key = secret_json["openai-personal"]
openai.api_key = openai_key

# Define the directory where prompt files are stored
PROMPT_DIR = "chalicelib/prompts"

# Define the filenames for each prompt file
COMPLIANCE_PROMPT_FILENAME = "compliance.prompt"
ROLE_SYSTEM_FILENAME = "compliance-role-system.prompt"


# Load the prompt files and replace the placeholders with the actual values
def load_prompts():
    promptdir = os.path.join(os.path.abspath(os.path.curdir), PROMPT_DIR)

    # Load the prompt file for seed
    with open(os.path.join(promptdir, COMPLIANCE_PROMPT_FILENAME), 'r') as f:
        guidelines_prompt = f.read()

    # Load the prompt file for role content
    with open(os.path.join(promptdir, ROLE_SYSTEM_FILENAME), 'r') as f:
        role_system = f.read()

    return guidelines_prompt, role_system


compliance_prompt, role_system = load_prompts()


# a function to call openai to check code for data compliance
def compliance_code(code, event, context, correlation_id):

    prompt = compliance_prompt.format(code=code)

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
    explanation = response.choices[0].message.content

    # Get the size of the code and explanation
    prompt_size = len(prompt) + len(role_system)
    explanation_size = len(explanation)

    if cw_client is not None:
        lambda_function = os.environ.get('AWS_LAMBDA_FUNCTION_NAME', context.function_name)
        cw_client.put_metric_data(
            Namespace='Boost/Lambda',
            MetricData=[
                {
                    'MetricName': 'PromptSize',
                    'Dimensions': [
                        {
                            'Name': 'LambdaFunctionName',
                            'Value': lambda_function
                        },
                        {
                            'Name': 'CorrelationID',
                            'Value': correlation_id
                        }
                    ],
                    'Unit': 'Bytes',
                    'Value': prompt_size
                },
                {
                    'MetricName': 'ResponseSize',
                    'Dimensions': [
                        {
                            'Name': 'LambdaFunctionName',
                            'Value': lambda_function
                        },
                        {
                            'Name': 'CorrelationID',
                            'Value': correlation_id
                        }
                    ],
                    'Unit': 'Bytes',
                    'Value': explanation_size
                }
            ]
        )

    return explanation
