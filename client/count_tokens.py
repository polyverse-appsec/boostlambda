import argparse
import sys
import os
from pathlib import Path

# Determine the parent directory's path.
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# Append the parent directory to sys.path.
sys.path.append(parent_dir)


from chalicelib.usage import (  # noqa
    OpenAIDefaults,
    num_tokens_from_string,
    get_openai_usage_per_string
)


def main():
    parser = argparse.ArgumentParser(description="Count OpenAI tokens from the contents of a file and suggest a possible cost to process the tokens.")
    parser.add_argument("filename", help="The name of the file to read and count tokens from.")
    parser.add_argument("--model_name", default=OpenAIDefaults.boost_default_gpt_model, help="The model name to use for estimating cost. Defaults to the current best GPT model.")

    args = parser.parse_args()

    if not Path(args.filename).exists():
        print(f"File '{args.filename}' does not exist!")
        return

    with open(args.filename, 'r', encoding='utf-8') as file:
        content = file.read()

    token_count, tokenized_content = num_tokens_from_string(content, args.model_name)
    num_tokens, total_cost = get_openai_usage_per_string(content, True, args.model_name)

    print(f"File: {args.filename}")
    print(f"Model: {args.model_name}")
    print(f"Number of Tokens: {token_count}")
    print(f"Estimated Cost: ${total_cost:.4f}")


if __name__ == "__main__":
    main()
