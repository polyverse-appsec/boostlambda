#!/bin/bash

aws_region="us-west-2"
cloud_stage="$1"
whatif="$2"
exit_code=0

# Define colors
RED='\033[0;31m'
YELLOW='\033[0;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Check if no parameters are passed
if [[ -z "$cloud_stage" ]]; then
    echo -e "${YELLOW}Usage: $0 <cloud_stage> [--whatif]${NC}"
    echo -e "${YELLOW}       cloud_stage: dev, test, staging, prod, all${NC}"
    echo -e "${YELLOW}       --whatif: Optional. Echo the actions without executing them.${NC}"
    exit 1
fi

# Get a list of all Lambda functions in the specified stage(s)
if [[ "$cloud_stage" == "all" ]]; then
    # Get all stages
    stages=("dev" "test" "prod")
    # Exclude staging for now in 'all' checks, since it hasn't yet been published
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
                echo -e "${RED}    Missing Public Uri for $function; would create via create-function-url-config and add-permission${NC}" >&2
                exit_code=1
                ((missing_functions++))

            else
                if aws lambda create-function-url-config --function-name "$function" --auth-type NONE --output text --region "$aws_region" >/dev/null 2>&1; then
                    echo "    Created public URI for function $function"

                    # Get the function configuration
                    config=$(aws lambda get-function-url-config --region "$aws_region" --function-name "$function")            
                    # Extract the function ARN
                    url=$(echo "$config" | jq -r '.FunctionUrl')
                    echo "    Created $function public url: $url"

                    if aws lambda add-permission --region "$aws_region" --function-name "$function" --statement-id 'public-access' --principal '*' --action 'lambda:InvokeFunction' >/dev/null 2>&1; then
                        echo "    Created public URI for function $function"
                    else
                        echo -e "${RED}    Failed to create public URI for function $function${NC}" >&2
                        exit_code=1
                        ((missing_functions++))
                    fi

                else
                    echo -e "${RED}    Failed to create public URI for function $function${NC}" >&2
                    exit_code=1
                    ((missing_functions++))
                fi
            fi
        else
            # Get the function configuration
            config=$(aws lambda get-function-url-config --region "$aws_region" --function-name "$function")
    
            # Extract the function ARN
            url=$(echo "$config" | jq -r '.FunctionUrl')
    
            echo "    $function already public: $url"
        fi
    done <<< "$functions"

    echo "  Finished processing functions in stage: $stage"
    if [[ $missing_functions -gt 0 ]]; then
        echo -e "${RED}  Missing functions count in stage $stage: $missing_functions${NC}" >&2
    else
        echo -e "${GREEN}  All functions public in stage $stage${NC}"
    fi
    missing_functions=0
done

echo -e "${RED}Errors - code $exit_code" >&2

exit $exit_code
