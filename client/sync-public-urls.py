import argparse
import boto3
import os
import json
from termcolor import colored


def split_server_parts(url):
    aws_server = ".lambda-url.us-west-2.on.aws/"

    return url.split(aws_server)[0], aws_server


def main(cloud_stage, monitors, whatif, client_src):
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

        aws_region = "us-west-2"

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

                if not monitors:
                    if not function_name.startswith(f"boost-{stage}"):
                        continue
                else:
                    if not function_name.startswith(f"boost-monitor-{stage}"):
                        continue

                try:
                    config = client.get_function_url_config(FunctionName=function_name)
                except Exception as e:
                    if "ResourceNotFoundException" not in str(e):
                        raise

                    config = None
                    pass

                # Check if the function already has public access
                try:
                    existing_permissions = client.get_policy(FunctionName=function_name)
                except Exception as e:
                    if "ResourceNotFoundException" not in str(e):
                        raise

                    existing_permissions = None
                    pass

                if existing_permissions:
                    policy = json.loads(existing_permissions['Policy'])
                    foundPublicAccess = False
                    for statement in policy['Statement']:
                        if statement['Sid'] == 'FunctionURLAllowPublicAccess':
                            if statement['Principal'] != '*':
                                print(colored(f"    Public access Principal for {function_name} is not set to *", 'red'))
                            elif statement['Effect'] != 'Allow':
                                print(colored(f"    Public access Effect for {function_name} is not set to Allow", 'red'))
                            elif statement['Action'] != 'lambda:InvokeFunctionUrl':
                                print(colored(f"    Public access Action for {function_name} is not set to lambda:InvokeFunctionUrl", 'red'))
                            elif statement['Condition'] is None:
                                print(colored(f"    Public access Condition for {function_name} is not set", 'red'))
                            elif statement['Condition']['StringEquals']['lambda:FunctionUrlAuthType'] != 'NONE':
                                print(colored(f"    Public access Condition for {function_name} is not set to NONE", 'red'))
                            else:
                                # Public access already exists
                                foundPublicAccess = True
                                break

                    # if we didn't find public access, then try to create it
                    if not foundPublicAccess:
                        existing_permissions = None

                url = None
                # if the config for the URL is missing, rebuild it
                if config:
                    if config['FunctionUrl'] is None:
                        config = None
                    else:
                        url = config['FunctionUrl']

                if not config or not existing_permissions:
                    # Create public access for the function
                    if whatif:
                        print(colored(f"    Missing Public Uri for {function_name}; would create via create-function-url-config and add-permission", 'red'))
                        exit_code = 1
                        missing_functions += 1

                    else:
                        try:
                            if config is None:
                                response = client.create_function_url_config(
                                    FunctionName=f'{function_name}',
                                    AuthType='NONE',
                                )
                                if 'FunctionUrl' not in response or response['FunctionUrl'] is None:
                                    print(colored(f"    Failed to validate public URI for function {function_name} after creation", 'red'))
                                    exit_code = 1
                                    missing_functions += 1
                                else:
                                    print(colored(f"    Created public URI for function {function_name}", 'green'))

                                config = client.get_function_url_config(FunctionName=function_name)
                                url = config['FunctionUrl'] if config else None
                                if url is None:
                                    print(colored(f"    Failed to retrieve public URI for function {function_name}", 'red'))
                                    exit_code = 1
                                    missing_functions += 1

                                else:
                                    print(colored(f"    Public URI validated for function {function_name} is {url}", 'green'))

                            if existing_permissions is None:
                                response = client.add_permission(
                                    FunctionName=function_name,
                                    StatementId='FunctionURLAllowPublicAccess',
                                    FunctionUrlAuthType='NONE',
                                    Action='lambda:InvokeFunctionUrl',
                                    Principal='*'
                                )
                                print(colored(f"    Attached Public URL permission to function {function_name}", 'green'))

                        except Exception:
                            print(colored(f"    Failed to create public URI for function {function_name}", 'red'))
                            exit_code = 1
                            missing_functions += 1

                if url is not None:
                    first, second = split_server_parts(url)
                    print(f"    {function_name} public: {colored(first, 'yellow')}{second}")

                    if client_src:
                        # Search for URI in source code files
                        uri_found = 0
                        for root, dirs, files in os.walk(client_src):
                            for file in files:
                                if file.endswith(".ts"):
                                    with open(os.path.join(root, file), "r") as file:
                                        if url in file.read():
                                            print(f"      Found in client {file}")
                                            uri_found = 1
                                            break
                        if uri_found == 0:
                            print(colored(f"      URI {url} not found in client source", 'red'))
                            exit_code = 1
                            missing_client_src += 1

        print(f"  Finished processing functions in stage: {stage}")
        if missing_functions > 0:
            print(colored(f"  Missing functions count in stage {stage}: {missing_functions}", 'red'))
        elif client_src:
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

    return exit_code


parser = argparse.ArgumentParser(description="Check and update functions in specified stage(s)")
parser.add_argument("cloud_stage", choices=["dev", "test", "staging", "prod", "all"], help="Specify the cloud stage: dev, test, staging, prod, all")
parser.add_argument("--monitors", action="store_true", help="Update service monitors instead of services")
parser.add_argument("--whatif", action="store_true", help="Echo the actions without executing them")
parser.add_argument("--client_src", nargs="?", help="Relative path to the location of client source code")

args = parser.parse_args()


try:
    exit_code = main(args.cloud_stage, args.monitors, args.whatif, args.client_src)
    exit(exit_code)
except KeyboardInterrupt:
    print(colored("Interrupted by user", 'red'))
    exit(1)
