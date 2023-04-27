#!/bin/bash

# get list of all function names
function_names=$(aws lambda list-functions --query 'Functions[*].FunctionName' --output text)

# iterate over each function name
for function_name in $function_names; do
  # check if the function name contains "boost"
  if [[ "$function_name" == *"boost"* ]]; then
    # enable tracing for the function
    aws lambda update-function-configuration \
      --function-name "$function_name" \
      --tracing-config Mode=Active >/dev/null
    # check if the update was successful
    if [ $? -ne 0 ]; then
      echo "Error: failed to enable tracing for function $function_name"
      exit 1
    fi
    echo "Enabled tracing for function $function_name"
  fi
done

