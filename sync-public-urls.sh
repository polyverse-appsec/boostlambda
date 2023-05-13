#!/bin/bash

aws_region="us-west-2"
cloud_stage="$1"
whatif="$2"
exit_code=0

# Define colors
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if no parameters are passed
if [[ -z "$cloud_stage" ]]; then
    echo -e "${RED}Usage: $0 <cloud_stage> [--whatif]${NC}" >&2
    echo -e "${RED}       cloud_stage: dev, test, staging, prod, all${NC}" >&2
    echo -e "${RED}       --whatif: Optional. Echo the actions without executing them.${NC}" >&2
    exit 1
fi

# Get a list of all Lambda functions in the specified stage(s)
if [[ "$cloud_stage" == "all" ]]; then
    # Get all stages
    stages=("dev" "test" "staging" "prod")
else
    # Use the specified stage
    stages=("$cloud_stage")
fi

# Iterate over each stage
for stage in "${stages[@]}"; do
    echo "Checking and updating functions in stage: $stage"

    # Get a list of all Lambda functions in the stage
    functions=$(aws lambda list-functions --region "$aws_region" --query "Functions[?starts_with(FunctionName, 'boost-${stage}')].FunctionName" --output text)

    # Check if any functions exist in the stage
    if [[ -z "$functions" ]]; then
        echo -e "${RED}No functions found in stage: $stage${NC}" >&2
        exit_code=1
        continue
    fi

    # Replace tabs with newlines in the functions list
    functions=$(echo -e "$functions" | tr '\t' '\n')

    # Iterate over each function
    while IFS= read -r function; do
        # Check if the function already has public access
        existing_permissions=$(aws lambda get-policy --region "$aws_region" --function-name "$function" --query 'Policy' --output text 2>/dev/null)

        if [[ -z "$existing_permissions" ]]; then
            # Create public access for the function
            if [[ "$whatif" == "--whatif" ]]; then
                echo -e "${RED}Missing Public Uri for function $function; would be created via aws lambda add-permission${NC}" >&2
            else
                if aws lambda add-permission --region "$aws_region" --function-name "$function" --statement-id 'public-access' --principal '*' --action 'lambda:InvokeFunction' >/dev/null 2>&1; then
                    echo "Created public URI for function $function"
                else
                    echo -e "${RED}Failed to create public URI for function $function${NC}" >&2
                    exit_code=1
                fi
            fi
        
            # Get the function configuration
            config=$(aws lambda get-function-configuration --region "$aws_region" --function-name "$function")
    
            # Extract the function ARN
            arn=$(echo "$config" | jq -r '.FunctionArn')
    
            # Create a public function URL
            url="https://lambda.${aws_region}.amazonaws.com/2015-03-31/functions/${arn}/invocations"
    
            echo "Public URL for function $function: $url"
        else
            echo "Function $function already has public access."
        fi
    done <<< "$functions"

    echo "Finished processing functions in stage: $stage"
done

echo -e "${RED}Errors - code $exit_code" >&2

exit $exit_code
