import boto3
import os
from typing import List


def get_functions(stage: str, monitors: bool) -> List[str]:
    aws_region = "us-west-2"
    lambda_client = boto3.client('lambda', region_name=aws_region)
    if monitors:
        response = lambda_client.list_functions(FunctionVersion='ALL')
        functions = [function['FunctionName'] for function in response['Functions'] if function['FunctionName'].startswith(f'boost-monitor-{stage}')]
    else:
        response = lambda_client.list_functions(FunctionVersion='ALL')
        functions = [function['FunctionName'] for function in response['Functions'] if function['FunctionName'].startswith(f'boost-{stage}')]
    return functions


def get_function_url_config(function_name: str) -> dict:
    aws_region = "us-west-2"
    lambda_client = boto3.client('lambda', region_name=aws_region)
    response = lambda_client.get_function_configuration(FunctionName=function_name)
    return response


def create_function_url_config(function_name: str):
    aws_region = "us-west-2"
    lambda_client = boto3.client('lambda', region_name=aws_region)
    response = lambda_client.update_function_configuration(FunctionName=function_name, Environment={'Variables': {'auth-type': 'NONE'}})
    return response


def add_permission(function_name: str):
    aws_region = "us-west-2"
    lambda_client = boto3.client('lambda', region_name=aws_region)
    response = lambda_client.add_permission(FunctionName=function_name, StatementId='FunctionURLAllowPublicAccess', Action='lambda:InvokeFunction', Principal='*')
    return response


def find_in_client_source(client_src: str, url: str) -> bool:
    for root, dirs, files in os.walk(client_src):
        for file in files:
            if file.endswith(".ts"):
                with open(os.path.join(root, file), "r") as file_obj:
                    if url in file_obj.read():
                        return True
    return False


def main():
    stages = ["dev", "test", "prod"]
    monitors = False
    whatif = False
    client_src = ""
    for stage in stages:
        functions = get_functions(stage, monitors)
        for function in functions:
            config = get_function_url_config(function)
            url = config['Environment']['Variables']['FunctionUrl'] if 'FunctionUrl' in config['Environment']['Variables'] else None
            if url is None:
                if whatif:
                    print(f"Missing Public Uri for {function}; would create via create-function-url-config and add-permission")
                else:
                    create_function_url_config(function)
                    add_permission(function)
                    config = get_function_url_config(function)
                    url = config['Environment']['Variables']['FunctionUrl']
                    print(f"New {function} public url: {url}")
            if client_src and not find_in_client_source(client_src, url):
                print(f"URI {url} not found in client source")
            else:
                print(f"{function} already public: {url}")


if __name__ == "__main__":
    main()
