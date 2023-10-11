import threading
import time
import random

from chalicelib.usage import OpenAIDefaults

# lambda AWS call must complete in 15 minutes, so our OpenAI call must complete in 12 mins
max_openai_wait_time_in_mins_before_lambda_timeout = 12

seconds_in_a_minute = 60

# Lambda calls must be done in 15 mins or less
#   We'll give ourselves a little buffer in case other operations
#   than OpenAI take 30-90 seconds (including stripe or GitHub calls)
total_analysis_time_buffer = int(13.50 * seconds_in_a_minute)  # 13 minutes 30 seconds

max_timeout_seconds_for_all_openai_calls = int(max_openai_wait_time_in_mins_before_lambda_timeout * seconds_in_a_minute)  # 12 minutes

max_timeout_seconds_for_single_openai_call = int(6 * seconds_in_a_minute)  # 6 minutes


class Throttler:
    def __init__(self, rate_limit_tokens_per_minute=OpenAIDefaults.rate_limit_tokens_per_minute):
        rate_limit_tokens_per_minute = OpenAIDefaults.rate_limit_tokens_per_minute
        self.rate = rate_limit_tokens_per_minute / seconds_in_a_minute
        self.bucket = rate_limit_tokens_per_minute
        self.lock = threading.Condition()
        self.max_wait_time = max_openai_wait_time_in_mins_before_lambda_timeout * seconds_in_a_minute

    def get_simple_processing_time_estimate(self, tokens):
        # Estimate the processing time based on the token count
        if 0 <= tokens <= 500:
            return 25
        elif 500 < tokens <= 3000:
            return 45
        elif 3000 < tokens <= 5000:
            return 90
        elif 5000 < tokens <= 8000:
            return 150
        else:
            return 180

    def get_weighted_proportional_processing_time_estimate(self, tokens, input_tokens):
        output_tokens = tokens - input_tokens

        input_weight = 1.3  # input tokens likely cause processing to take longer than output tokens to generate
        output_weight = 0.7

        # Calculate weighted token count
        weighted_tokens = int((input_tokens * input_weight) + (output_tokens * output_weight))

        # Proportional time estimates based on the given ranges:
        token_ranges = [500, 3000, 5000, 8000]
        time_estimates = [25, 45, 90, 150, 180]

        for i, upper_limit in enumerate(token_ranges):
            if weighted_tokens <= upper_limit:
                proportion = weighted_tokens / upper_limit
                return proportion * float(time_estimates[i])

        # If the weighted_tokens exceeds the highest defined range, return the maximum estimated time.
        return float(time_estimates[-1])

    def get_proportional_processing_time_estimate(self, tokens):
        # Define data points for tokens and their respective processing times
        token_ranges = [0, 500, 3000, 5000, 8000]
        time_estimates = [25, 45, 90, 150, 180]  # in seconds

        # Find the appropriate range for the given tokens
        for i in range(1, len(token_ranges)):
            if tokens <= token_ranges[i]:
                # Calculate proportional estimate using linear interpolation
                token_range_diff = token_ranges[i] - token_ranges[i - 1]
                time_estimate_diff = time_estimates[i] - time_estimates[i - 1]

                ratio = (tokens - token_ranges[i - 1]) / token_range_diff
                interpolated_time = time_estimates[i - 1] + ratio * time_estimate_diff

                return int(interpolated_time)

        # If tokens exceed the defined range, return the maximum estimated time
        return time_estimates[-1]

    def get_randomized_processing_time_estimate(self, tokens, input_tokens):
        wait_time = self.get_weighted_proportional_processing_time_estimate(tokens, input_tokens)

        # Random factor between 0.95 and 1.05
        random_factor = random.uniform(0.95, 1.05)

        return wait_time * random_factor

    def get_wait_time(self, tokens_needed, first_wait, input_tokens):
        with self.lock:
            if (tokens_needed != round(tokens_needed, 0)):
                print(f"Thread-{threading.get_ident()}:Throttler: {tokens_needed} tokens needed, {self.bucket} tokens available, waiting {first_wait} seconds")

            # if we're going to hit the max overall timeout for calls if we don't start this call, then just start it
            #       and bypass throttler... can't be worse than indefinite hang or exceeding overall timeout
            if (max_timeout_seconds_for_all_openai_calls - max_timeout_seconds_for_single_openai_call) < (time.time() - first_wait):
                print(f"Thread-{threading.get_ident()}:Throttler: {tokens_needed} tokens needed, {self.bucket} tokens available, but max overall timeout for calls is too close, so bypassing throttler")
                return float(-1)

            if self.bucket >= tokens_needed:
                print(f"Thread-{threading.get_ident()}:Throttler: {tokens_needed} tokens needed, {self.bucket} tokens available, no wait needed")
                self.bucket -= tokens_needed
                return float(0.0)

            tokens_short = tokens_needed - self.bucket

            # we'll wait the estimate for how long it will take to process the tokens we need
            wait_time = self.get_randomized_processing_time_estimate(tokens_short, input_tokens)

            return wait_time

    def refill(self, tokens_needed):
        with self.lock:
            if (tokens_needed != round(tokens_needed, 0)):
                print(f"Thread-{threading.get_ident()}:Throttler: Refilling bucket (was:{self.bucket}) with {tokens_needed} tokens")
            print(f"Thread-{threading.get_ident()}:Throttler: Refilling bucket (was:{self.bucket}) with {tokens_needed} tokens")
            self.bucket += tokens_needed
            self.bucket = min(self.bucket, OpenAIDefaults.rate_limit_tokens_per_minute)

            # notify all threads they can try again
            self.lock.notify_all()
