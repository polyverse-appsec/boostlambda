import openai
import sys
import os

# Get the script's directory
script_dir = os.path.dirname(os.path.realpath(__file__))

# Adjust the path to ensure you can import pvsecret
sys.path.append(os.path.join(script_dir, '../chalicelib'))
prompt_filename = 'product-usage-system.prompt'

from pvsecret import get_secrets  # noqa
from usage import num_tokens_from_string  # noqa

# Use the get_secrets function to retrieve the OpenAI API key
secrets = get_secrets()
openai.api_key = secrets['openai-personal']  # Assuming the key is stored with 'openai' as the key in the secrets


def call_openai_api(prompt, model="gpt-4-0613"):
    data = {
        "model": model,
        'max_tokens': 1000,
        "messages": [
            {"role": "user", "content": prompt},
        ],
    }

    # Assuming you have set the API key and imported the OpenAI library
    response = openai.ChatCompletion.create(**data)
    return response.choices[0].message['content']


def get_input_content(paths):
    content = ""

    for path in paths:
        if os.path.isfile(path):
            relPath = os.path.relpath(path, script_dir)
            print(f"Importing doc file: {relPath}")
            with open(path, 'r') as f:
                content += f.read() + "\n\n"
        elif os.path.isdir(path):
            # Get all items in the directory
            items_in_directory = [os.path.join(path, item) for item in os.listdir(path)]
            # Call the function recursively on the items in the directory
            content += get_input_content(items_in_directory)

    return content


if __name__ == "__main__":
    # Get list of markdown files from command-line arguments
    markdown_files = sys.argv[1:]

    # Generate terse prompt
    print(f"Searching for docs at: {markdown_files}")
    raw_content = get_input_content(markdown_files)

    prompt = (
        f"Rewrite the following product instructions that can be used as a system prompt for OpenAI prompts - to enable a product user to ask questions about the product after installed.\n"
        f" * Critical information and details about product should be retained in terse form\n"
        f" * Use neutral practical langauge\n"
        f" * Omit all instructions related to download and install of the Extension\n"
        f" {raw_content}"
    )

    print("Using OpenAI to rewrite and compress the source documentation...")
    terse_content = call_openai_api(prompt)

    # Write to product-usage-system.prompt
    with open(os.path.join(script_dir, f'../chalicelib/prompts/{prompt_filename}'), 'w') as f:
        f.write(terse_content)

    print(f"Terse system prompt written to {prompt_filename}")

    raw_tokens = num_tokens_from_string(raw_content)[0]
    terse_tokens = num_tokens_from_string(terse_content)[0]
    print(f"Instructions compressed from {raw_tokens} to {terse_tokens} tokens: {round(terse_tokens / raw_tokens * 100,2)}% of original length")

    print("\n\n")
    print(terse_content)
