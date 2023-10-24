import time

default_lambda_service_memory_mb = 256


def lambda_cost(duration_in_seconds, memory_in_mb=default_lambda_service_memory_mb, request_count=1):
    """
    Approximate the AWS Lambda cost with tiered pricing.

    Parameters:
    - memory_in_mb (float): The amount of memory provisioned for the Lambda function.
    - duration_in_seconds (float): The duration of the Lambda invocation.
    - total_gb_seconds_used (float): The total GB-seconds used this month including the current invocation.
    - request_count (int): The number of requests (default is 1).

    Returns:
    - cost (float): The estimated cost in USD.
    """

    # AWS Lambda pricing details (as provided)
    request_rate = 0.20 / 1000000  # cost per request

    # Convert memory to GB
    memory_in_gb = memory_in_mb / 1024.0

    # Calculate GB-seconds for the current invocation
    current_gb_seconds = memory_in_gb * duration_in_seconds

    # Calculate cost for GB-seconds based on the tiered pricing
    if memory_in_gb <= 6e9:
        gb_second_rate = 0.0000166667
    elif memory_in_gb <= 15e9:
        gb_second_rate = 0.000015
    else:
        gb_second_rate = 0.0000133334

    compute_cost = gb_second_rate * current_gb_seconds
    request_cost = request_count * request_rate

    total_cost = compute_cost + request_cost

    return total_cost


default_approximate_memory_usage_mb = 185

# global dictionary for tracking current lambda operations and their start times
global_start_times = {}


def init_current_lambda_cost(correlationId):
    global_start_times[correlationId] = time.time()


def get_current_lambda_cost(correlationId):
    currentOperationStartTime = global_start_times.get(correlationId, None)
    elapsedOperationTime = time.time() - currentOperationStartTime

    # add 1 second to elapsed time for projected finish time
    projectedOperationFinishTime = elapsedOperationTime + 1

    return lambda_cost(projectedOperationFinishTime, default_approximate_memory_usage_mb, 1)