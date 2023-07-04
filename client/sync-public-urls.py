import argparse
import boto3
import os
from termcolor import colored

aws_region = "us-west-2"

parser = argparse.ArgumentParser(description="Check and update functions in specified stage(s)")
parser.add_argument("cloud_stage", choices=["dev", "test", "staging", "prod", "all"], help="Specify the cloud stage: dev, test, staging, prod, all")
parser.add_argument("--monitors", action="store_true", help="Update service monitors instead of services")
parser.add_argument("--whatif", action="store_true", help="Echo the actions without executing them")
parser.add_argument("--client_src", nargs="?", help="Relative path to the location of client source code")

args = parser.parse_args()

cloud_stage = args.cloud_stage
monitors = args.monitors
whatif = args.whatif
client_src = args.client_src
exit_code = 0
missing_functions = 0
missing_client_src = 0

# Get a list of all Lambda functions in the specified stage(s)
if cloud_stage == "all":
    # Get all stages
    stages = ["dev", "test", "prod"]
    # Exclude staging for now in 'all' checks, since it hasn't yet been published
else:
    # Use the specified stage
    stages = [cloud_stage]

# Iterate over each stage
for stage in stages:
    print(f"Checking and updating functions in stage: {stage}")

    # Get a list of all Lambda functions in the stage
    client = boto3.client('lambda', region_name=aws_region)

    paginator = client.get_paginator('list_functions')
    iterator = paginator.paginate(
        FunctionVersion='ALL',
        PaginationConfig={
            'MaxItems': 500,
            'PageSize': 50
        }
    )

    for page in iterator:
        for function in page['Functions']:

            function_name = function['FunctionName']
            config = client.get_function_configuration(FunctionName=function_name)

            if not monitors:
                if not function_name.startswith(f"boost-{stage}"):
                    continue
            else:
                if not function_name.startswith(f"boost-monitor-{stage}"):
                    continue

            # Check if the function already has public access
            existing_permissions = client.get_policy(FunctionName=function_name)

            if not config or not existing_permissions:
                # Create public access for the function
                if whatif:
                    print(colored(f"    Missing Public Uri for {function_name}; would create via create-function-url-config and add-permission", 'red'))
                    exit_code = 1
                    missing_functions += 1

                else:
                    try:
                        response = client.add_permission(
                            FunctionName=function_name,
                            StatementId='FunctionURLAllowPublicAccess',
                            Action='lambda:InvokeFunction',
                            Conditions="StringEquals",
                            Principal='*'
                        )
                        print(colored(f"    Created public URI for function {function_name}", 'green'))

                        if client_src:
                            # Search for URI in source code files
                            uri_found = 0
                            for root, dirs, files in os.walk(client_src):
                                for file in files:
                                    if file.endswith(".ts"):
                                        with open(os.path.join(root, file), "r") as file:
                                            if function_name in file.read():
                                                print(f"      Found in client {file}")
                                                uri_found = 1
                                                break
                            if uri_found == 0:
                                print(colored(f"      URI {function_name} not found in client source", 'red'))
                                exit_code = 1
                                missing_client_src += 1

                    except Exception:
                        print(colored(f"    Failed to create public URI for function {function_name}", 'red'))
                        exit_code = 1
                        missing_functions += 1

            else:
                print(f"    {function_name} already public: {function_name}")

                if client_src:
                    # Search for URI in source code files
                    uri_found = 0
                    for root, dirs, files in os.walk(client_src):
                        for file in files:
                            if file.endswith(".ts"):
                                with open(os.path.join(root, file), "r") as file:
                                    if function_name in file.read():
                                        print(f"      Found in client {file}")
                                        uri_found = 1
                                        break
                    if uri_found == 0:
                        print(colored(f"      URI {function_name} not found in client source", 'red'))
                        exit_code = 1
                        missing_client_src += 1

    print(f"  Finished processing functions in stage: {stage}")
    if missing_functions > 0:
        print(colored(f"  Missing functions count in stage {stage}: {missing_functions}", 'red'))
    else:
        print(colored(f"  All functions public in stage {stage}", 'green'))
    missing_functions = 0

    if missing_client_src > 0:
        print(colored(f"  Missing client references in stage {stage}: {missing_client_src}", 'red'))
    else:
        print(colored(f"  All public functions referenced in client in stage {stage}", 'green'))
    missing_client_src = 0

if exit_code > 0:
    print(colored(f"Errors - code {exit_code}", 'red'))
else:
    print(colored("Success", 'green'))

exit(exit_code)
