#!/bin/bash

aws_region="us-west-2"
cloud_stage="$1"
whatif="$2"

# Check if no parameters are passed
if [[ -z "$cloud_stage" ]]; then
    echo "Usage: $0 <cloud_stage> [--whatif]"
    echo "       cloud_stage: dev, test, staging, prod"
    echo "       --whatif: Optional. Echo the actions without executing them."
    exit 1
fi

# Get a list of all Lambda functions in the specified stage
functions=$(aws lambda list-functions --region "$aws_region" --query 'Functions[?ends_with(FunctionName, `-'${cloud_stage}'`)].FunctionName' --output text)

# Iterate over each function
while IFS= read -r function; do
    # Check if the function already has public access
    existing_permissions=$(aws lambda get-policy --region "$aws_region" --function-name "$function" --query 'Policy' --output text)

    if [[ -z "$existing_permissions" ]]; then
        # Create public access for the function
        if [[ "$whatif" == "--whatif" ]]; then
            echo "What if: aws lambda add-permission --region $aws_region --function-name $function --statement-id 'public-access' --principal '*' --action 'lambda:InvokeFunction'"
        else
            aws lambda add-permission --region "$aws_region" --function-name "$function" --statement-id 'public-access' --principal '*' --action 'lambda:InvokeFunction'
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
