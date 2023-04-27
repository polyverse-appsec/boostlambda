import openai
from . import pvsecret
import os
from chalicelib.version import API_VERSION
from chalicelib.telemetry import cw_client

guidelines_api_version = API_VERSION  # API version is global for now, not service specific
print("guidelines_api_version: ", guidelines_api_version)

secret_json = pvsecret.get_secrets()

# TEMP - put this back to the polyverse key once gpt-4 access is approved there
openai_key = secret_json["openai-personal"]
openai.api_key = openai_key

# Define the directory where prompt files are stored
PROMPT_DIR = "chalicelib/prompts"

# Define the filenames for each prompt file
GUIDELINES_PROMPT_FILENAME = "guidelines.prompt"
ROLE_SYSTEM_FILENAME = "guidelines-role-system.prompt"


# Load the prompt files and replace the placeholders with the actual values
def load_prompts():
    promptdir = os.path.join(os.path.abspath(os.path.curdir), PROMPT_DIR)

    # Load the prompt file for guidelines
    with open(os.path.join(promptdir, GUIDELINES_PROMPT_FILENAME), 'r') as f:
        guidelines_prompt = f.read()

    # Load the prompt file for system role
    with open(os.path.join(promptdir, ROLE_SYSTEM_FILENAME), 'r') as f:
        role_system = f.read()

    return guidelines_prompt, role_system


guidelines_prompt, role_system = load_prompts()


# a function to call openai to evaluate code for coding guidelines
def guidelines_code(code, event, context, correlation_id):

    prompt = guidelines_prompt.format(code=code)

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
    analysis = response.choices[0].message.content

    # Get the size of the code and explanation
    prompt_size = len(prompt) + len(role_system)
    analysis_size = len(analysis)

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
                    'Value': analysis_size
                }
            ]
        )

    return analysis
