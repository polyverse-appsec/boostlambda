# generic.py
import openai
import traceback
import os
import math
import time
import requests
import concurrent.futures
import threading
import random
import json
from typing import List, Tuple
import glob
import re

from chalice import UnprocessableEntityError

from .. import pvsecret

from chalicelib.markdown import markdown_emphasize
from chalicelib.telemetry import capture_metric, InfoMetrics, CostMetrics
from chalicelib.usage import (get_openai_usage_per_token, get_openai_usage_per_string, max_tokens_for_model,
                              get_boost_cost, OpenAIDefaults, num_tokens_from_string, decode_string_from_input)
from chalicelib.payments import update_usage_for_text

key_ChunkedInputs = 'chunked_inputs'
key_ChunkPrefix = 'chunk_prefix'
key_NumberOfChunks = 'chunks'
key_IsChunked = 'chunked'
key_ChunkingPrompt = 'chunking'

# Define the directory where prompt files are stored
PROMPT_DIR = "chalicelib/prompts"

secret_json = pvsecret.get_secrets()

# TEMP - put this back to the polyverse key once gpt-4 access is approved there
openai_key = secret_json["openai-personal"]
openai.api_key = openai_key


class GenericProcessor:

    def __init__(self, api_version, prompt_filenames, numbered_prompt_keys,
                 default_params={'model': OpenAIDefaults.boost_default_gpt_model,
                                 'temperature': OpenAIDefaults.default_temperature}):

        self.api_version = api_version

        self.prompt_filenames = []
        self.prompt_filenames.extend(prompt_filenames if prompt_filenames is not None else [])
#         self.prompt_filenames.append(['system', 'guidelines-system.prompt'])

        self.default_params = default_params

        self.numbered_prompt_keys = []
        self.numbered_prompt_keys.append(['response', 'guidelines'])
        self.numbered_prompt_keys.extend(numbered_prompt_keys if numbered_prompt_keys is not None else [])

        print(f"{self.__class__.__name__}_api_version: ", self.api_version)

        self.prompts = self.load_prompts()

    def load_prompts(self):
        promptdir = os.path.join(os.path.abspath(os.path.curdir), PROMPT_DIR)
        prompts = []

        # load prompts specified in 'prompt_filenames'
        for prompt_filename in self.prompt_filenames:
            with open(os.path.join(promptdir, prompt_filename[1]), 'r') as f:
                prompts.append([prompt_filename[0], f.read()])

        # load numbered prompts
        for prompt_key in self.numbered_prompt_keys if self.numbered_prompt_keys is not None else []:
            # if the definition is a prompt & response, pairing, load both files and process in order
            if prompt_key[0] == 'response':
                for file in sorted(glob.glob(os.path.join(promptdir, f"{prompt_key[1]}-user-*.prompt"))):
                    # response has a user prompt....
                    with open(file, 'r') as f:
                        prompts.append(["user", f.read()])

                    # construct the corresponding assistant file name
                    assistant_file = file.replace("-user-", "-assistant-")

                    # Open assistant file, if it exists
                    if os.path.isfile(assistant_file):
                        with open(assistant_file, 'r') as f:
                            prompts.append(["assistant", f.read()])
                    else:
                        raise FileNotFoundError(f"Assistant file {assistant_file} not found for {file}")
            else:
                file_list = sorted(glob.glob(os.path.join(promptdir, f"{prompt_key[1]}-{prompt_key[0]}-*.prompt")))
                if prompt_key not in prompts:
                    prompts.append([prompt_key, prompt_key[1]])

                for file in file_list:
                    with open(file, 'r') as f:
                        prompts[prompt_key[0]].append(f.read())

        return prompts

    def chunk_input_based_on_token_limit(self, data, prompt_format_args, input_token_buffer) -> List[Tuple[List[dict[str, any]], int]]:

        # get the ideal full prompt - then we'll figure out if we need to break it up further
        this_messages = self.generate_messages(data, prompt_format_args)
        fullMessageContentTokensCount = 0
        for message in this_messages:
            if 'content' in message:
                fullMessageContentTokensCount += num_tokens_from_string(message["content"])[0]

        # if we can fit the chunk into one token buffer, we'll process and be done
        max_tokens = max_tokens_for_model(data.get('model'))
        tuned_max_tokens = max_tokens - fullMessageContentTokensCount
        tuned_output = self.calculate_output_token_buffer(fullMessageContentTokensCount, tuned_max_tokens, max_tokens)
        if (fullMessageContentTokensCount < input_token_buffer):
            return [(this_messages, tuned_output)]

        # otherwise, we'll need to break the chunk into smaller chunks
        # we're going to extract ONLY the bit of user-content (not the prompt wrapper) that we can try and break up
        userContentTokenCount, userContentTokens = num_tokens_from_string(data[self.get_chunkable_input()])

        # let's figure out how big the non-user content is... since we'll create user chunks that can accomodate the non-user content added back
        nonUserContentTokenCount = fullMessageContentTokensCount - userContentTokenCount

        # if the fixed non-user content (e.g. other parts of prompt messages) are beyond the buffer size, then
        # we won't be able to process the user content at all, so raise an error and give up
        if nonUserContentTokenCount > input_token_buffer:
            print(f"ChunkingInputFailed: InputBuffer size={input_token_buffer}, Fixed non-User content size={nonUserContentTokenCount}, User content size={userContentTokenCount} ")
            raise UnprocessableEntityError("Background context for analysis is too large to process. Please try again with less context.")

        remainingBuffer = input_token_buffer - nonUserContentTokenCount

        # Subtract 100 from the total buffer size to account for possible calculation errors (in the prompt engineering)
        safe_buffer = remainingBuffer - 100

        full_buffer_chunks = userContentTokenCount // safe_buffer  # How many full buffer chunks you can make
        remainder = userContentTokenCount % safe_buffer  # What remains after consuming full buffers

        # If the remainder is less than 20% of the full remaining buffer, switch to equal size chunks
        if remainder < (safe_buffer * 0.2):
            n_chunks = math.ceil(userContentTokenCount / safe_buffer)
            chunk_size = math.ceil(userContentTokenCount / n_chunks)
        else:
            n_chunks = full_buffer_chunks + 1  # The full buffer chunks plus the remainder
            chunk_size = safe_buffer  # Except for the last chunk, the chunks are the size of the full buffer

        this_messages_chunked = []

        for i in range(0, userContentTokenCount, chunk_size):

            # decode this smaller chunk of the original user content
            user_chunk_tokens = userContentTokens[i:i + chunk_size]
            user_chunk_text = decode_string_from_input(user_chunk_tokens)

            # rebuild the prompt with the smaller user input chunk
            data_copy = data.copy()
            data_copy[self.get_chunkable_input()] = user_chunk_text
            prompt_format_args_copy = prompt_format_args.copy()
            prompt_format_args_copy[self.get_chunkable_input()] = user_chunk_text
            this_messages = self.generate_messages(data_copy, prompt_format_args_copy)

            these_tokens_count = 0
            for message in this_messages:
                if 'content' in message:
                    these_tokens_count += num_tokens_from_string(message["content"])[0]

            # get the new remaining max tokens we can accomodate with output
            max_tokens = max_tokens_for_model(data.get('model'))
            tuned_max_tokens = max_tokens - these_tokens_count
            tuned_output = self.calculate_output_token_buffer(these_tokens_count, tuned_max_tokens, max_tokens)

            # store the updated message to be processed
            this_messages_chunked.append((this_messages, tuned_output))

        return this_messages_chunked

    def calculate_input_token_buffer(self, total_max) -> int:
        return math.floor(total_max * 0.5)

    def calculate_output_token_buffer(self, input_buffer_size, output_buffer_size, total_max) -> int:

        # if the input is larger than our output buffer already, we'll just allow the entire output buffer to be used
        if input_buffer_size > output_buffer_size:
            return output_buffer_size

        # otherwise, we'll calculate the remaining buffer size
        remainingBuffer = total_max - input_buffer_size

        # at least 10% of total max if it fits in remainingBuffer
        ten_percent_total = total_max * 0.1
        minimum_buffer = int(min(remainingBuffer, ten_percent_total))

        # the lesser of the remainingBuffer or 5x the input_buffer (for very tine inputs)
        buffer_size = int(min(remainingBuffer, math.floor(input_buffer_size * 2)))

        return max(buffer_size, minimum_buffer)

    # returns true if truncation was done
    # also returns a list of prompts to process - where each prompt includes the prompt text, and the max output tokens for that prompt
    def build_prompts_from_input(self, data, params, prompt_format_args, function_name) -> Tuple[bool, List[Tuple[List[dict[str, any]], int]], int]:

        max_tokens = max_tokens_for_model(data.get('model'))
        # get the max input buffer for this function if we are tuning tokens
        if max_tokens != 0:
            input_token_buffer = self.calculate_input_token_buffer(max_tokens)
        # otherwise, just send it all to the OpenAI endpoint, and ignore limits
        else:
            input_token_buffer = 0

        truncated = False

        # if single input, build the prompt to test length
        if 'chunks' not in prompt_format_args:
            this_messages = self.generate_messages(data, prompt_format_args)
            these_tokens_count = 0
            for message in this_messages:
                if 'content' in message:
                    these_tokens_count += num_tokens_from_string(message["content"])[0]

            # include the function-related content as part of the input buffer
            for key in ['function_call', 'functions']:
                if key in params:
                    # note that the function-related params are stored as dictionaries, unlike other user content
                    these_tokens_count += num_tokens_from_string(json.dumps(params[key]))[0]

            if input_token_buffer == 0:
                prompts_set = [(this_messages, 0)]

            elif these_tokens_count < input_token_buffer:
                tuned_max_tokens = max_tokens - these_tokens_count
                tuned_output = self.calculate_output_token_buffer(these_tokens_count, tuned_max_tokens, max_tokens)
                prompts_set = [(this_messages, tuned_output)]

            else:  # this single input has blown the input buffer, so we'll need to chunk it
                # If we are over the token limit, we're going to need to split it into chunks to process in parallel and then reassemble
                # enough buffer to get a useful result - say 20% - 50% of the original input
                prompts_set = self.chunk_input_based_on_token_limit(data, prompt_format_args, input_token_buffer)

        else:  # we have input chunks we need to break up, which themselves could be broken up
            cloned_prompt_format_args = prompt_format_args.copy()

            del cloned_prompt_format_args[key_NumberOfChunks]

            chunk_inputs = cloned_prompt_format_args[key_ChunkedInputs]
            del cloned_prompt_format_args[key_ChunkedInputs]

            del cloned_prompt_format_args[key_ChunkPrefix]

            prompts_set = []
            for i in range(len(chunk_inputs)):
                cloned_prompt_format_args[key_ChunkingPrompt] = f"This is part {i} of {len(chunk_inputs)} of the inputs you are analyzing."

                # inject the chunk into the input slot in the data and prompt fields
                data[self.get_chunkable_input()] = chunk_inputs[i]
                cloned_prompt_format_args[self.get_chunkable_input()] = chunk_inputs[i]

                # recursively call ourselves per chunk
                _, each_chunk_prompt_set, _ = self.build_prompts_from_input(data, params, cloned_prompt_format_args, function_name)

                # add the newly build prompt and max tokens into the list
                prompts_set.extend(each_chunk_prompt_set)

        user_prompts_size = 0
        for prompt, _ in prompts_set:
            for message in prompt:
                if 'content' in message and message["role"] == "user":
                    user_prompts_size += len(message["content"])

        return truncated, prompts_set, user_prompts_size

    def get_chunkable_input(self) -> str:
        raise NotImplementedError

    def safe_format(self, string, **kwargs):
        class SafeDict(dict):
            def __missing__(self, key):
                return '{' + key + '}'

        safe_dict = SafeDict(kwargs)
        return string.format_map(safe_dict)

    def safe_dict(self, d):
        return {k: v if v is not None else '' for k, v in d.items()}

    def generate_messages(self, data, prompt_format_args) -> List[dict[str, any]]:
        prompt_format_args = self.safe_dict(prompt_format_args)

        # handle variable replacements safely
        this_messages = []

        # Generate messages for all roles
        for prompt in self.prompts:
            if prompt[0] == 'main':  # we handle 'main' last
                main_prompt = prompt[1]
                continue

            # Check if prompt[1] contains a '{tag}' that exists in data
            tag = re.findall(r'\{(.+?)\}', prompt[1])
            if tag and tag[0] in data:
                if isinstance(data.get(tag[0]), list):

                    role, content_list = data[tag[0]]
                    for content in content_list:
                        # inject each piece of custom content into the prompt
                        this_prompt_format_args = prompt_format_args.copy()
                        this_prompt_format_args[tag[0]] = content
                        formatted_content = self.safe_format(content, **this_prompt_format_args)

                        if str.isspace(formatted_content):
                            print(f"Skipping empty prompt for role {role}")
                            continue

                        this_messages.append({
                            "role": role,
                            "content": formatted_content
                        })

                    # finished with this prompt
                    continue

            content = self.safe_format(prompt[1], **prompt_format_args)
            # skip empty content
            if str.isspace(content):
                print(f"Skipping empty prompt for role {prompt[0]}")
                continue

            this_messages.append({
                "role": prompt[0],
                "content": content
            })

        # Check if prompt[1] contains a '{tag}' that exists in data
        tag = re.findall(r'\{(.+?)\}', main_prompt)
        if tag and tag[0] in data:
            if isinstance(data.get(tag[0]), list):
                new_format_arg = ""
                role, content_list = data[tag[0]]
                for content in content_list:
                    new_format_arg = f"{new_format_arg}\n{content}"

                # inject the combined content into the args for prompt injection
                prompt_format_args[tag[0]] = new_format_arg

        # 'main' is always the last message and it's always from the 'user'
        this_messages.append({
            "role": "user",
            "content": self.safe_format(main_prompt, **prompt_format_args)
        })

        return this_messages

    def runAnalysis(self, params, account, function_name, correlation_id) -> dict:
        max_retries = 3
        # we're going to retry on intermittent network issues
        # e.g. throttling, connection issues, service down, etc..
        # Note that with RateLimit error, we could actually make it worse...
        #    So don't retry on rate limit
        # https://platform.openai.com/docs/guides/error-codes/python-library-error-types
        for attempt in range(max_retries + 1):
            try:
                try:
                    response = openai.ChatCompletion.create(**params)

                    if attempt > 0:
                        print(f"{function_name}:{account['email']}:{correlation_id}:Succeeded after {attempt} retries")

                    return dict(
                        message=response.choices[0].message,
                        response=response.choices[0].message.content,
                        finish=response.choices[0].finish_reason,
                        input_tokens=response.usage.prompt_tokens,
                        output_tokens=response.usage.completion_tokens)

                except openai.error.Timeout as e:
                    if attempt >= max_retries:  # If not the last attempt
                        raise
                    else:
                        recoverableError = e
                        pass  # Try again
                except requests.exceptions.Timeout as e:
                    if attempt >= max_retries:  # If not the last attempt
                        raise
                    else:
                        recoverableError = e
                        pass  # Try again
                except openai.error.APIConnectionError as e:
                    if attempt >= max_retries:  # If not the last attempt
                        raise
                    else:
                        recoverableError = e
                        pass  # Try again
                except openai.error.APIError as e:
                    if attempt >= max_retries:  # If not the last attempt
                        raise
                    else:
                        recoverableError = e
                        pass  # Try again
                except openai.error.ServiceUnavailableError as e:
                    if attempt >= max_retries:  # If not the last attempt
                        raise
                    else:
                        recoverableError = e
                        pass  # Try again
                except openai.error.RateLimitError as e:
                    # if we hit the rate limit, send a cloudwatch alert and raise the error
                    capture_metric(
                        account['customer'], account['email'], function_name, correlation_id,
                        {"name": InfoMetrics.OPENAI_RATE_LIMIT, "value": 1, "unit": "None"})
                    if attempt >= max_retries:  # If not the last attempt
                        raise
                    else:
                        # throttle way back if we hit the 40k processing limit
                        if "40000 / min" in str(e):
                            randomSleep = random.uniform(30, 60)
                        else:
                            randomSleep = random.uniform(5, 15)
                        print(f"{function_name}:{correlation_id}:RateLimitError, sleeping for {randomSleep} seconds before retry")
                        time.sleep(randomSleep)  # Sleep for 5-15 seconds to throttle, and avoid stampeding on retry
                        recoverableError = e
                        pass  # Try again
                except Exception:
                    raise

            except Exception as e:
                print(f"{function_name}:{account['email']}:{correlation_id}:FAILED after {attempt} retries:Error: {str(e)}")
                raise

            randomSleep = random.uniform(2, 5)
            print(f"{function_name}:{account['email']}:{correlation_id}:Retrying in {randomSleep} seconds after recoverable error: {str(recoverableError)}")
            time.sleep(randomSleep)  # Sleep for 2-5 seconds to throttle, and avoid stampeding on retry

    def runAnalysisForPrompt(self, i, this_messages, max_output_tokens, params_template, account, function_name, correlation_id) -> dict:
        params = params_template.copy()  # Create a copy of the template to avoid side effects

        if max_output_tokens != 0:
            params["max_tokens"] = int(max_output_tokens)

        params['messages'] = this_messages

        start_time = time.monotonic()
        print(f"{function_name}:{account['email']}:{correlation_id}:Thread-{threading.current_thread().ident}:Starting")
        result = None
        try:
            result = self.runAnalysis(params, account, function_name, correlation_id)
            end_time = time.monotonic()
            print(f"{function_name}:{account['email']}:{correlation_id}:Thread-{threading.current_thread().ident}:"
                  f"SUCCESS processing chunked prompt {i} in {end_time - start_time:.3f} seconds:"
                  f"Finish:{result['finish'] if result['finish'] is not None else 'Incomplete'}")
            return result
        except Exception as e:
            end_time = time.monotonic()
            print(f"{function_name}:{account['email']}:{correlation_id}:Thread-{threading.current_thread().ident}:"
                  f"Error processing chunked prompt {i} after {end_time - start_time:.3f} seconds:"
                  f"Finish:{result['finish'] if result is not None and 'finish' in result and result['finish'] is not None else 'Incomplete'}::error:{str(e)}")
            raise

    def process_input(self, data, account, function_name, correlation_id, prompt_format_args) -> dict:

        params = self.default_params.copy()  # Create a copy of the defaults

        # enable user to override the model to gpt-3 or gpt-4
        if 'model' in data:
            params["model"] = data['model']

        if "model" in params:
            print(f"{function_name}:{account['email']}:{correlation_id}:Using model {params['model']}")

        # https://community.openai.com/t/cheat-sheet-mastering-temperature-and-top-p-in-chatgpt-api-a-few-tips-and-tricks-on-controlling-the-creativity-deterministic-output-of-prompt-responses/172683
        if 'top_p' in data:
            params["top_p"] = float(data['top_p'])
        elif 'temperature' in data:
            params["temperature"] = float(data['temperature'])

        if 'guidelines' not in data:
            prompt_format_args['guidelines'] = "This software project has no additional special architectural guidelines or constraints."

        # {"customer": customer, "subscription": subscription, "subscription_item": subscription_item, "email": email}
        customer = account['customer']
        email = account['email']

        prompt_set: List[Tuple[str, int]] = []

        truncated, prompt_set, prompts_size = self.build_prompts_from_input(data, params, prompt_format_args, function_name)
        chunked = len(prompt_set) > 1

        success = False
        try:
            results = None
            result = None
            # if chunked, we're going to run all chunks in parallel and then concatenate the results at end
            if chunked:
                print(f"{function_name}:Chunked:{account['email']}:{correlation_id}:Chunked user input - {len(prompt_set)} chunks")

                openAIRateLimitPerMinute = 40000
                totalChunks = len(prompt_set)
                tokensPerChunk = openAIRateLimitPerMinute / totalChunks

                def runAnalysisForPromptThrottled(prompt_iteration):
                    index, prompt = prompt_iteration
                    model_max_tokens = max_tokens_for_model(data.get('model'))
                    if OpenAIDefaults.boost_max_tokens_default == 0:
                        delay = 0  # if we have no defined max, then no delay and no throttling - since tuning is disabled
                    else:

                        def calculateProcessingTime(estimatedTokensForThisPrompt, tokensPerChunk) -> float:
                            processingMinutes = estimatedTokensForThisPrompt / tokensPerChunk
                            processingSeconds = processingMinutes * 60
                            return processingSeconds

                        # we use an estimate that input tokens will be doubled in output
                        estimatedTokensForThisPrompt = min((model_max_tokens - prompt[1]) * (1 / self.calculate_input_token_buffer(
                            model_max_tokens)),
                            model_max_tokens)
                        delay = calculateProcessingTime(estimatedTokensForThisPrompt, tokensPerChunk)

                    print(f"{function_name}:{correlation_id}:Thread-{threading.current_thread().ident} "
                          f"Summary {index} delaying for {delay:.3f} secs")
                    time.sleep(delay)  # Delay based on the number of words in the prompt

                    if delay > 5:  # If delay is more than 5 seconds, log it
                        print(f"{function_name}:{correlation_id}:Thread-{threading.current_thread().ident} "
                              f"Summary {index} delayed for {delay:.3f} secs")
                    return self.runAnalysisForPrompt(index, prompt[0], prompt[1], params, account, function_name, correlation_id)

                # launch all the parallel threads to run analysis with the unique chunked prompt for each
                # Throttling the rate of file processing
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    results = list(executor.map(runAnalysisForPromptThrottled, enumerate(prompt_set)))
            # otherwise, run once
            else:
                # if truncated user input, report it out, and update the OpenAI input with the truncated input
                if truncated:
                    print(f"{function_name}:Truncation:{account['email']}:{correlation_id}:"
                          f"Truncated user input, discarded {max_tokens_for_model(data.get('model')) - prompt_set[0][1]} tokens")

                # run the analysis with single input
                singleIndex = 0
                results = [self.runAnalysisForPrompt(singleIndex, prompt_set[singleIndex][0],
                                                     prompt_set[singleIndex][1], params, account, function_name, correlation_id)]
                result = results[0]['response']

            # after we run the analysis, we need to update the result with the truncation warning
            if truncated:
                truncation = markdown_emphasize(f"Truncated input, discarded ~{max_tokens_for_model(data.get('model')) - prompt_set[0][1]} words\n\n")
                result = f"{truncation}{results[0]['response']}"

            # if chunked, we're going to reassemble all the chunks
            elif chunked:
                result = "\n\n".join([r['response'] for r in results])  # by concatenating all results into a single string

            success = True
        finally:

            try:
                user_input = self.collate_all_user_input(prompt_format_args)
                user_input_size = len(user_input)
                openai_customerinput_tokens, openai_customerinput_cost = get_openai_usage_per_string(user_input, True)
                openai_input_tokens, openai_input_cost = get_openai_usage_per_token(
                    sum([r['input_tokens'] for r in results]), True) if results is not None else (0, 0)

                # Get the cost of the outputs and prior inputs - so we have visibiity into our cost per user API
                output_size = len(result) if result is not None else 0

                boost_cost = get_boost_cost(user_input_size + output_size)

                openai_output_tokens, openai_output_cost = get_openai_usage_per_token(
                    sum([r['output_tokens'] for r in results]), False) if results is not None else (0, 0)
                openai_tokens = openai_input_tokens + openai_output_tokens
                openai_cost = openai_input_cost + openai_output_cost

                try:
                    if success:
                        # update the billing usage for this analysis (charge for input + output) as long as analysis is successful
                        update_usage_for_text(account, user_input_size + output_size)
                except Exception:
                    success = False
                    exception_info = traceback.format_exc().replace('\n', ' ')
                    print(f"UPDATE_USAGE:FAILURE:{customer['name']}:{customer['id']}:{email}:{correlation_id}:"
                          f"Error updating ~${boost_cost} usage: ", exception_info)
                    capture_metric(customer, email, function_name, correlation_id,
                                   {"name": InfoMetrics.BILLING_USAGE_FAILURE, "value": round(boost_cost, 5), "unit": "None"})

                    pass  # Don't fail if we can't update usage / but that means we may have lost revenue

                capture_metric(customer, email, function_name, correlation_id,
                               {'name': CostMetrics.PROMPT_SIZE, 'value': prompts_size, 'unit': 'Count'},
                               {'name': CostMetrics.RESPONSE_SIZE, 'value': user_input_size, 'unit': 'Count'},
                               {'name': CostMetrics.OPENAI_INPUT_COST, 'value': round(openai_input_cost, 5), 'unit': 'None'},
                               {'name': CostMetrics.OPENAI_CUSTOMERINPUT_COST, 'value': round(openai_customerinput_cost, 5), 'unit': 'None'},
                               {'name': CostMetrics.OPENAI_OUTPUT_COST, 'value': round(openai_output_cost, 5), 'unit': 'None'},
                               {'name': CostMetrics.OPENAI_COST, 'value': round(openai_cost, 5), 'unit': 'None'},
                               {'name': CostMetrics.BOOST_COST if success else CostMetrics.LOST_BOOST_COST, 'value': round(boost_cost, 5), 'unit': 'None'},
                               {'name': CostMetrics.OPENAI_INPUT_TOKENS, 'value': openai_input_tokens, 'unit': 'Count'},
                               {'name': CostMetrics.OPENAI_CUSTOMERINPUT_TOKENS, 'value': openai_customerinput_tokens, 'unit': 'Count'},
                               {'name': CostMetrics.OPENAI_OUTPUT_TOKENS, 'value': openai_output_tokens, 'unit': 'Count'},
                               {'name': CostMetrics.OPENAI_TOKENS, 'value': openai_tokens, 'unit': 'Count'})

            except Exception:
                exception_info = traceback.format_exc().replace('\n', ' ')
                print(f"{customer['name']}:{customer['id']}:{email}:{correlation_id}:Error capturing metrics: ", exception_info)
                pass  # Don't fail if we can't capture metrics

        return {
            "results": results,
            "output": result,
            "truncated": truncated,
            "chunked": chunked
        }

    def get_excluded_input_keys(self) -> list[str]:
        return ['model', 'top_p', 'temperature', 'chunking']

    def collate_all_user_input(self, prompt_format_args):
        # remove any keys used for control of the processing, so we only charge for user input
        excluded_keys = self.get_excluded_input_keys()

        # Use lambda function to handle list of strings
        input_list = map(
            lambda key: ' '.join(prompt_format_args[key]) if isinstance(prompt_format_args[key], list) else str(prompt_format_args[key]),
            [key for key in prompt_format_args if key not in excluded_keys]
        )

        return ' '.join(input_list)
