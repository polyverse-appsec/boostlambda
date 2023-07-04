#!/bin/bash

aws_region="us-west-2"
cloud_stage="$1"
monitors="$2"
whatif="$2"
client_src="$3"
exit_code=0

# Define colors
RED='\033[0;31m'
YELLOW='\033[0;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Check if no parameters are passed
if [[ -z "$cloud_stage" ]]; then
    echo -e "${YELLOW}Usage: $0 <cloud_stage> [--monitors] [--whatif] [client_src]${NC}"
    echo -e "${YELLOW}       cloud_stage: dev, test, staging, prod, all${NC}"
    echo -e "${YELLOW}       --monitors: Optional. Update service monitors instead of services.${NC}"
    echo -e "${YELLOW}       --whatif: Optional. Echo the actions without executing them.${NC}"
    echo -e "${YELLOW}       client_src: Optional. Relative path to the location of client source code.${NC}"
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
    if [[ "$monitors" == "--monitors" ]]; then
        functions=$(aws lambda list-functions --region "$aws_region" --query "Functions[?starts_with(FunctionName, 'boost-monitor-${stage}')].FunctionName" --output text)
    else
        functions=$(aws lambda list-functions --region "$aws_region" --query "Functions[?starts_with(FunctionName, 'boost-${stage}')].FunctionName" --output text)
    fi

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
        # Get the function configuration
        config=$(aws lambda get-function-url-config --region "$aws_region" --function-name "$function" 2>/dev/null)

        # Extract the function ARN
        url=$(echo "$config" | jq -r '.FunctionUrl')

        # Check if the function already has public access
        existing_permissions=$(aws lambda get-policy --region "$aws_region" --function-name "$function" --query 'Policy' --output text 2>/dev/null)

        if [[ -z "$config" || -z "$existing_permissions" || -z "$url" ]]; then
            # Create public access for the function
            if [[ "$whatif" == "--whatif" ]]; then
                echo -e "${RED}    Missing Public Uri for $function; would create via create-function-url-config and add-permission${NC}" >&2
                exit_code=1
                ((missing_functions++))

            else
                if aws lambda create-function-url-config --function-name "$function" --auth-type NONE --output text --region "$aws_region" >/dev/null 2>&1; then
                    echo -e "${GREEN}    Created public URI for function $function${NC}"

                    # Get the function configuration
                    config=$(aws lambda get-function-url-config --region "$aws_region" --function-name "$function")            
                    # Extract the function ARN
                    url=$(echo "$config" | jq -r '.FunctionUrl')
                    echo "      New $function public url: $url"

                    if aws lambda add-permission --region "$aws_region" --function-name "$function" --statement-id 'FunctionURLAllowPublicAccess' --principal '*' --action 'lambda:InvokeFunction' >/dev/null 2>&1; then
                        echo -e "${GREEN}      Set public-access for function $function${NC}"

                        if [[ -n "$client_src" ]]; then
                                # Search for URI in source code files
                            uri_found=0
                            while IFS= read -r -d '' file; do
                                if grep -q "$url" "$file"; then
                                    echo "      Found in client $file"
                                    uri_found=1
                                    break
                                fi
                            done < <(find "$client_src" -type f -name "*.ts" -print0)

                            if [[ $uri_found -eq 0 ]]; then
                                echo -e "${RED}      URI $url not found in client source${NC}" >&2
                                exit_code=1
                                ((missing_client_src++))
                            fi
                        fi
                        
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
    
            echo "    $function already public: $url"

            if [[ -n "$client_src" ]]; then
                # Search for URI in source code files
                uri_found=0
                while IFS= read -r -d '' file; do
                    if grep -q "$url" "$file"; then
                        echo "      Found in client $file"
                        uri_found=1
                        break
                    fi
                done < <(find "$client_src" -type f -name "*.ts" -print0)

                if [[ $uri_found -eq 0 ]]; then
                    echo -e "${RED}      URI $url not found in client source${NC}" >&2
                    exit_code=1
                    ((missing_client_src++))

                fi
            fi

        fi
    done <<< "$functions"

    echo "  Finished processing functions in stage: $stage"
    if [[ $missing_functions -gt 0 ]]; then
        echo -e "${RED}  Missing functions count in stage $stage: $missing_functions${NC}" >&2
    else
        echo -e "${GREEN}  All functions public in stage $stage${NC}"
    fi
    missing_functions=0

    if [[ $missing_client_src -gt 0 ]]; then
        echo -e "${RED}  Missing client references in stage $stage: $missing_client_src${NC}" >&2
    else
        echo -e "${GREEN}  All public functions referenced in client in stage $stage${NC}"
    fi
    missing_client_src=0
done

if [[ $exit_code -gt 0 ]]; then
    echo -e "${RED}Errors - code $exit_code${NC}" >&2
else
    echo -e "${GREEN}Success${NC}"
fi

exit $exit_code
