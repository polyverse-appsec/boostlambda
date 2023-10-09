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
from typing import List, Tuple, Dict, Any
import glob
import re

from chalice import UnprocessableEntityError

from .. import pvsecret

from chalicelib.markdown import markdown_emphasize
from chalicelib.telemetry import capture_metric, InfoMetrics, CostMetrics
from chalicelib.usage import (
    get_openai_usage_per_token,
    get_openai_usage_per_string,
    max_tokens_for_model,
    get_boost_cost,
    OpenAIDefaults,
    num_tokens_from_string,
    decode_string_from_input)
from chalicelib.payments import update_usage_for_text
from chalicelib.log import mins_and_secs

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


class AnalysisOutputFormat:

    # formats to choose from
    bulletedList = "bulletedList"   # bulleted list of issues
    prose = "prose"                 # prose/generic text
    numberedList = "numberedList"   # numbered list of issues
    rankedList = "rankedList"       # ranked list of issues - by severity or importance
    json = "json"                   # json output (aka functions): NOTE: Not currently supported exception by special processor

    defaultFormat = prose


class AnalysisContextType:
    projectSummary = "projectSummary"
    userFocus = "userFocus"
    history = "history"
    related = "related"


class GenericProcessor:

    def __init__(self, api_version, prompt_filenames, numbered_prompt_keys,
                 default_params={'model': OpenAIDefaults.boost_default_gpt_model,
                                 'temperature': OpenAIDefaults.default_temperature},
                 default_output_format=AnalysisOutputFormat.defaultFormat,
                 supported_output_formats=[]):

        self.api_version = api_version

        self.default_output_format = default_output_format
        self.supported_output_formats = supported_output_formats.copy()
        self.supported_output_formats.append(default_output_format)

        # Create a new list with the project summaries data
        summaries = ['system', 'summaries-system.prompt']

        # create the context-aware prompts
        context_history = ['system', 'context-history-system.prompt']
        context_related = ['system', 'context-related-system.prompt']
        context_userFocus = ['system', 'context-userFocus-system.prompt']

        # If prompt_filenames is not None, create a copy, otherwise initialize an empty list
        new_prompt_filenames = prompt_filenames.copy() if prompt_filenames is not None else []

        # Iterate over the new_prompt_filenames
        for i, prompt in enumerate(new_prompt_filenames):
            # Check if the prompt type is 'system'
            if prompt[0] == 'system':
                # Insert the summaries after the first system prompt
                new_prompt_filenames.insert(i + 1, summaries)

                # insert the context-aware prompts after the summaries
                #   we start with historical data
                new_prompt_filenames.insert(i + 2, context_history)
                #   then add related info
                new_prompt_filenames.insert(i + 3, context_related)
                # and finally add the key user focus
                new_prompt_filenames.insert(i + 4, context_userFocus)
                break

        # make sure we have a main prompt
        if not any(prompt[0] == 'main' for prompt in new_prompt_filenames):
            raise ValueError("Main prompt was not specified for analysis.")

        self.prompt_filenames = new_prompt_filenames

        self.default_params = default_params.copy()

        self.numbered_prompt_keys = []

        # We aren't using Assistant/User reply to train on the client's guidelines yet, since better results come
        #     from being in the user-prompt alone
        # self.numbered_prompt_keys.append(['response', 'guidelines'])
        self.numbered_prompt_keys.extend(numbered_prompt_keys if numbered_prompt_keys is not None else [])

        print(f"{self.__class__.__name__}_api_version: ", self.api_version)

        # early load the prompts to catch issues as soon as possible
        self.prompts = None
        self.load_prompts()

    def load_prompts(self):

        # if prompts already loaded and file timestamps have not changed, do nothing
        if self.prompts is not None and not self.check_prompt_files_changed():
            print(f"{self.__class__.__name__}: Prompts already loaded and files have not changed; skipping refresh of prompts")
            return

        # otherwise load the prompts
        promptdir = os.path.join(os.path.abspath(os.path.curdir), PROMPT_DIR)
        prompts = []

        # load prompts specified in 'prompt_filenames'
        for prompt_filename in self.prompt_filenames:
            with open(os.path.join(promptdir, prompt_filename[1]), 'r') as f:
                prompts.append([prompt_filename, f.read()])

        # load numbered prompts
        for prompt_key in self.numbered_prompt_keys if self.numbered_prompt_keys is not None else []:
            # if the definition is a prompt & response pairing, load both files and process in order
            if prompt_key[0] == 'response':
                for file in sorted(glob.glob(os.path.join(promptdir, f"{prompt_key[1]}-user-*.prompt"))):
                    # Get the filename from the full path
                    response_user_prompt_filename = os.path.basename(file)

                    # response has a user prompt....
                    with open(file, 'r') as f:
                        prompts.append([["user", response_user_prompt_filename], f.read()])

                    # construct the corresponding assistant file name
                    assistant_file = file.replace("-user-", "-assistant-")
                    response_assistant_prompt_filename = os.path.basename(assistant_file)

                    # Open assistant file, if it exists
                    if os.path.isfile(assistant_file):
                        with open(assistant_file, 'r') as f:
                            prompts.append([["assistant", response_assistant_prompt_filename], f.read()])
                    else:
                        raise FileNotFoundError(f"Assistant file {assistant_file} not found for {file}")
            else:
                file_list = sorted(glob.glob(os.path.join(promptdir, f"{prompt_key[1]}-{prompt_key[0]}-*.prompt")))

                for file in file_list:
                    dynamic_filename = os.path.basename(file)
                    with open(file, 'r') as f:
                        prompts.append([[prompt_key[0], dynamic_filename], f.read()])

        self.prompts = prompts

        # Store the last modification timestamps in the cache
        self.cache_prompt_files_timestamps()

    def check_prompt_files_changed(self):
        # Compare the current timestamps with the cached timestamps
        promptdir = os.path.join(os.path.abspath(os.path.curdir), PROMPT_DIR)
        files_changed = False
        for prompt_filename in self.prompt_filenames:
            file_path = os.path.join(promptdir, prompt_filename[1])
            current_timestamp = os.path.getmtime(file_path)
            if file_path not in self.prompt_files_timestamps:
                files_changed = True
                print(f"File '{prompt_filename[1]}' has changed. New timestamp: {time.strftime('%Y-%m-%d %H:%M', time.localtime(current_timestamp))}")
            elif self.prompt_files_timestamps[file_path] != current_timestamp:
                files_changed = True
                old_timestamp = self.prompt_files_timestamps[file_path]
                time_difference = (current_timestamp - old_timestamp) / 60  # Difference in minutes
                print(f"File '{prompt_filename[1]}' has changed. New timestamp: {time.strftime('%Y-%m-%d %H:%M', time.localtime(current_timestamp))}. Time difference: {time_difference:.2f} minutes.")
            # Update the timestamp in the cache
            self.prompt_files_timestamps[file_path] = current_timestamp

        return files_changed

    def cache_prompt_files_timestamps(self):
        # Store the last modification timestamps in the cache
        promptdir = os.path.join(os.path.abspath(os.path.curdir), PROMPT_DIR)
        self.prompt_files_timestamps = {}
        for prompt_filename in self.prompt_filenames:
            file_path = os.path.join(promptdir, prompt_filename[1])
            self.prompt_files_timestamps[file_path] = os.path.getmtime(file_path)

    def optimize_content(self, this_messages: List[Dict[str, Any]], data) -> Tuple[List[Dict[str, Any]], int]:
        def truncate_system_message(sys_message, total_system_buffer, total_system_tokens):
            sys_token_count, sys_tokens = num_tokens_from_string(sys_message['content'], data.get('model'))
            proportion = sys_token_count / total_system_tokens
            min_quota = max(min_token_quota, int(total_system_buffer * min_quota_percent))
            retained_tokens = int(min(max_quota, max(min_quota, int(total_system_buffer * proportion))))

            if sys_token_count > retained_tokens:
                sys_message['content'] = decode_string_from_input(sys_tokens[:retained_tokens], data.get('model'))
                truncated = sys_token_count - retained_tokens
                discard_percent = retained_tokens / sys_token_count
                print(f"{self.__class__.__name__}:Truncation:"
                      f"System message quota: {proportion * 100:.1f}% of {total_system_buffer} tokens,"
                      f" max per quota {max_quota}, discarded {truncated} of {sys_token_count}: {discard_percent * 100:.1f}% retained")
                return True, truncated
            return False, 0

        total_system_tokens = sum(num_tokens_from_string(message['content'], data.get('model'))[0]
                                  for message in this_messages if 'content' in message and message['role'] == 'system')

        system_messages = [message for message in this_messages if 'content' in message and message['role'] == 'system']

        total_system_buffer = self.calculate_system_message_token_buffer(data.get('max_tokens', max_tokens_for_model(data.get('model'))))

        # if there are less than 5 system messages, we're going to use minimum quotas to
        #   ensure even large messages have some minimum quota
        min_quota_threshold_for_message_count = 5
        min_quota_percent = 1 / min_quota_threshold_for_message_count
        min_token_quota = 250
        max_quota = total_system_buffer / len(system_messages) if len(system_messages) > 0 else 0

        # but if we have a large number of system messages, don't enforce a minimum quota
        if len(system_messages) > min_quota_threshold_for_message_count:
            min_quota_percent = 0
            min_token_quota = 0

        new_messages = []
        in_sequence_system_messages = []
        non_system_messages_between = 0
        truncated_system_messages = 0
        total_truncated = 0

        for message in this_messages:
            if 'content' not in message or message['content'] == '':
                continue

            if message in [this_messages[0], this_messages[-1]] or message['role'] != 'system':
                if in_sequence_system_messages:
                    in_sequence_system_messages.sort(key=lambda x: len(x.get('content', '')))

                    for sys_message in in_sequence_system_messages:
                        was_truncated, truncated = truncate_system_message(sys_message, total_system_buffer, total_system_tokens)
                        truncated_system_messages += was_truncated
                        total_truncated += truncated
                        new_messages.append(sys_message)

                    in_sequence_system_messages = []
                    non_system_messages_between = 0

                new_messages.append(message)
                if message['role'] != 'system':
                    non_system_messages_between += 1

            else:
                in_sequence_system_messages.append(message)

        if truncated_system_messages > 0:
            print(f"{self.__class__.__name__}:Truncation:"
                  f"Truncated {truncated_system_messages} out of {len(system_messages)} system messages"
                  f" to meet total system token quota: {total_system_buffer}")

        discarded_messages = len(this_messages) - len(new_messages)
        if discarded_messages > 0:
            print(f"{self.__class__.__name__}:Truncation:"
                  f"Discarded {discarded_messages} messages with no content")

        return new_messages, total_truncated

    def chunk_input_based_on_token_limit(self,
                                         data,
                                         prompt_format_args,
                                         input_token_buffer,
                                         extra_non_message_content_size,
                                         ) -> Tuple[List[Tuple[List[dict[str, any]], int]], int]:

        truncation = 0
        # get the ideal full prompt - then we'll figure out if we need to break it up further
        this_messages = self.generate_messages(data, prompt_format_args)
        this_messages, this_truncation = self.optimize_content(this_messages, data)
        truncation += this_truncation
        full_message_content_tokens_count = 0
        for message in this_messages:
            if 'content' in message:
                full_message_content_tokens_count += num_tokens_from_string(message["content"], data.get('model'))[0]

        # if we can fit the chunk into one token buffer, we'll process and be done
        max_tokens = max_tokens_for_model(data.get('model'))
        tuned_max_tokens = max_tokens - full_message_content_tokens_count
        tuned_output = self.calculate_output_token_buffer(full_message_content_tokens_count, tuned_max_tokens, max_tokens)
        if (full_message_content_tokens_count < input_token_buffer):
            return [(this_messages, tuned_output)], truncation

        # otherwise, we'll need to break the chunk into smaller chunks
        # we're going to extract ONLY the bit of user-content (not the prompt wrapper) that we can try and break up
        chunkable_input = prompt_format_args[self.get_chunkable_input()]
        is_chunked_list = isinstance(data[self.get_chunkable_input()], list)
        chunkable_user_content_token_count, chunkable_user_content_tokens = num_tokens_from_string(
            chunkable_input, data.get('model'))

        # let's figure out how big the non-user content is... since we'll create user chunks that can accomodate the non-user content added back
        non_user_content_token_count = full_message_content_tokens_count - chunkable_user_content_token_count

        # if the fixed non-user content (e.g. other parts of prompt messages) are beyond the buffer size, then
        # we won't be able to process the user content at all, so raise an error and give up
        if non_user_content_token_count > input_token_buffer:
            print(
                f"ChunkingInputFailed: InputBuffer size={input_token_buffer}, "
                f"Fixed non-User content size={non_user_content_token_count}, "
                f"User content size={chunkable_user_content_token_count} ")
            raise UnprocessableEntityError("Background context for analysis is too large to process. Please try again with less context.")

        remaining_buffer = input_token_buffer - non_user_content_token_count - extra_non_message_content_size

        # Since the chunking process requires re-encoding subsets of the larger input, each encoded chunk
        #   may end up larger (e.g. if the chunk token boundaries change). We'll assume a 15% buffer around
        #   the tokenization boundaries
        token_boundary_deviation_variance = 0.15
        safe_remaining_buffer = round(remaining_buffer * (1 - token_boundary_deviation_variance))

        full_buffer_chunks = chunkable_user_content_token_count // safe_remaining_buffer  # How many full buffer chunks you can make
        remainder = chunkable_user_content_token_count % safe_remaining_buffer  # What remains after consuming full buffers

        # If the remainder is less than 20% of the full remaining buffer, switch to equal size chunks
        if remainder < (safe_remaining_buffer * 0.2):
            n_chunks = math.ceil(chunkable_user_content_token_count / (safe_remaining_buffer + 1))
            chunk_size = math.ceil(chunkable_user_content_token_count / n_chunks)
        else:
            n_chunks = full_buffer_chunks + 1  # The full buffer chunks plus the remainder
            chunk_size = safe_remaining_buffer  # Except for the last chunk, the chunks are the size of the full buffer

        this_messages_chunked = []

        i = 0
        # process all the tokens in the user content to create the chunks
        while i < len(chunkable_user_content_tokens):
            # determine end index for this chunk
            end_idx = i + chunk_size

            # ensure if we are processing a remainder (partial chunk), we don't go over the end of the user content
            if end_idx >= len(chunkable_user_content_tokens):
                end_idx = len(chunkable_user_content_tokens)

            # if we're using a list as input, then break on newlines
            # if we're not at the end of the tokens, adjust end_idx based on the decoding result
            # note the last token may not be a newline
            if is_chunked_list and end_idx != len(chunkable_user_content_tokens):
                decoded_token = decode_string_from_input([chunkable_user_content_tokens[end_idx - 1]], data.get('model'))

                # move the boundary backward until we hit a token that decodes to a newline or the beginning of the chunk
                while end_idx > i and '\n' not in decoded_token:
                    end_idx -= 1
                    decoded_token = decode_string_from_input([chunkable_user_content_tokens[end_idx - 1]], data.get('model'))

                # If the token has text followed by a newline, then we should include that token in the current chunk
                # and start the next chunk after it.
                if decoded_token.endswith('\n'):
                    end_idx += 1

            # decode this smaller chunk of the original user content
            user_chunk_tokens = chunkable_user_content_tokens[i:end_idx]
            user_chunk_text = decode_string_from_input(user_chunk_tokens, data.get('model'))

            # we use the unbuffered count of the actual tokens (e.g. excluding the tokenization variance buffer)
            these_tokens_count = len(num_tokens_from_string(user_chunk_text, data.get('model'))[1])
            chunk_decoded_size_change = these_tokens_count - (end_idx - i)
            # if the increase is larger than our boundary deviation, we're going to fail
            if chunk_decoded_size_change / (end_idx - i) > token_boundary_deviation_variance:
                print(f"ChunkingInputFailed: Chunk size={these_tokens_count}, "
                      f"Re-decoded chunk size={end_idx - i}, "
                      f"Chunk size change={chunk_decoded_size_change}")
                raise UnprocessableEntityError("Chunking input failed due to unexpectedly large deviation in tokenization. Please try again with less input.")

            # rebuild the prompt with the smaller user input chunk
            data_copy = data.copy()
            data_copy[self.get_chunkable_input()] = user_chunk_text
            prompt_format_args_copy = prompt_format_args.copy()
            prompt_format_args_copy[self.get_chunkable_input()] = user_chunk_text
            this_messages = self.generate_messages(data_copy, prompt_format_args_copy)
            this_messages, this_truncation = self.optimize_content(this_messages, data_copy)
            truncation += this_truncation

            these_tokens_count = 0
            for message in this_messages:
                if 'content' in message:
                    these_tokens_count += num_tokens_from_string(message["content"], data.get('model'))[0]

            if these_tokens_count > remaining_buffer:
                message_regeneration_variance = (these_tokens_count - remaining_buffer) / these_tokens_count
                print(f"ChunkingInputFailed: Exceeded Input Buffer size={input_token_buffer}, "
                      f"Chunk size={these_tokens_count}, "
                      f"Splitting Variance={message_regeneration_variance}, ")
                raise UnprocessableEntityError("Input is too large to process. Please try again with less input.")

            # need to add the function content size to the token count to ensure we
            #   calculate the output buffer size correctly
            these_tokens_count += extra_non_message_content_size

            # get the new remaining max tokens we can accommodate with output
            max_tokens = max_tokens_for_model(data.get('model'))
            tuned_max_tokens = max_tokens - these_tokens_count
            tuned_output = self.calculate_output_token_buffer(these_tokens_count, tuned_max_tokens, max_tokens)

            # store the updated message to be processed
            this_messages_chunked.append((this_messages, tuned_output))

            # Move the index to the next chunk starting point
            i = end_idx

        return this_messages_chunked, truncation

    def calculate_input_token_buffer(self, total_max) -> int:
        return math.floor(total_max * 0.5)

    # we're only going to use 25% of our input buffer for system messages (e.g. background info)
    def calculate_system_message_token_buffer(self, total_max) -> int:
        return math.floor(self.calculate_input_token_buffer(total_max) * 0.25)

    def get_default_max_tokens(self) -> int:
        return max_tokens_for_model(self.default_params.get('model'))

    def calculate_output_token_buffer(self, input_buffer_size, output_buffer_size, total_max) -> int:

        # if the input is larger than our output buffer already, we'll just allow the entire output buffer to be used
        if input_buffer_size > output_buffer_size:
            return output_buffer_size

        # otherwise, we'll calculate the remaining buffer size
        remainingBuffer = total_max - input_buffer_size

        # at least 10% of total max if it fits in remainingBuffer
        ten_percent_total = total_max * 0.1
        minimum_buffer = int(min(remainingBuffer, ten_percent_total))

        # the lesser of the remainingBuffer or 2x the input_buffer (for very tiny inputs)
        buffer_size = int(min(remainingBuffer, math.floor(input_buffer_size * 2)))

        return max(buffer_size, minimum_buffer)

    def truncate_user_messages(self, messages: List[dict[str, any]], input_token_buffer, data):
        truncated_token_count = 0
        discarded_token_count = 0
        discard_future_messages = False  # Flag to indicate if further messages should be discarded
        discarded_messages = 0

        for message in messages:
            if message['role'] != 'user':
                continue

            if 'content' not in message:
                continue

            if discard_future_messages:
                discarded_token_count += num_tokens_from_string(message["content"], data.get('model'))[0]
                discarded_messages += 1
                message['content'] = ""
                continue

            token_count, user_tokens = num_tokens_from_string(message["content"], data.get('model'))

            if truncated_token_count + token_count > input_token_buffer:
                remaining_tokens = input_token_buffer - truncated_token_count
                truncated_token_count += remaining_tokens
                message['content'] = decode_string_from_input(user_tokens[:remaining_tokens], data.get('model'))
                discarded_token_count += token_count - remaining_tokens
                discard_future_messages = True  # Set the flag to discard further messages
            else:
                truncated_token_count += token_count

        discard_percent = discarded_token_count / (truncated_token_count + discarded_token_count)
        print(f"Truncated {truncated_token_count} tokens, "
              f"Discarded {discarded_token_count} tokens - "
              f"{discard_percent}% of {truncated_token_count + discarded_token_count} tokens, "
              f"{discarded_messages} messages discarded")

        return messages, discarded_token_count

    # returns true if truncation was done
    # also returns a list of prompts to process - where each prompt includes the prompt text, and the max output tokens for that prompt
    def build_prompts_from_input(self, data, params, prompt_format_args, function_name) -> Tuple[int, List[Tuple[List[dict[str, any]], int]], int]:

        # allow the caller to override max_tokens, or just use default max for the chosen model
        max_tokens = data.get('max_tokens') if 'max_tokens' in data else max_tokens_for_model(data.get('model'))
        # get the max input buffer for this function if we are tuning tokens
        if max_tokens != 0:
            input_token_buffer = self.calculate_input_token_buffer(max_tokens)
        # otherwise, just send it all to the OpenAI endpoint, and ignore limits
        else:
            input_token_buffer = 0

        truncated = 0

        # calculate the size of the function-related content for input buffer usage
        function_content_size = 0
        for key in ['function_call', 'functions']:
            if key in params:
                # note that the function-related params are stored as dictionaries, unlike other user content
                function_content_size += num_tokens_from_string(json.dumps(params[key]), data.get('model'))[0]

        # if single input, build the prompt to test length
        if 'chunks' not in prompt_format_args:
            this_messages = self.generate_messages(data, prompt_format_args)
            this_messages, _ = self.optimize_content(this_messages, data)
            these_tokens_count = 0
            for message in this_messages:
                if 'content' in message:
                    these_tokens_count += num_tokens_from_string(message["content"], data.get('model'))[0]

            # reduce the input_token_buffer by the size of the function input content, since its fixed
            #   content that we can't reduce (even with chunking or other optimization)
            input_token_buffer -= function_content_size if input_token_buffer > 0 else 0

            if input_token_buffer == 0:
                prompts_set = [(this_messages, 0)]

            elif these_tokens_count < input_token_buffer:
                tuned_max_tokens = max_tokens - these_tokens_count
                tuned_output = self.calculate_output_token_buffer(
                    these_tokens_count, tuned_max_tokens, max_tokens,)
                prompts_set = [(this_messages, tuned_output)]

            else:  # this single input has blown the input buffer, so we'll need to chunk or truncate it

                # if the processor supports chunkable input, then we'll go that route
                if self.get_chunkable_input():
                    # If we are over the token limit, we're going to need to split it into chunks to process in parallel and then reassemble
                    # enough buffer to get a useful result - say 20% - 50% of the original input
                    prompts_set, unused_truncation = self.chunk_input_based_on_token_limit(
                        data, prompt_format_args, input_token_buffer, function_content_size)
                    # we'll ignore this truncation since we're chunking it anyway

                # otherwise, we'll just truncate the last user message
                else:
                    this_messages, truncated_tokens_count = self.truncate_user_messages(this_messages, input_token_buffer, data)

                    # emsure we include any function input content size before we calculate remaining output buffer
                    truncated_tokens_count += function_content_size

                    tuned_max_tokens = max_tokens - truncated_tokens_count
                    tuned_output = self.calculate_output_token_buffer(truncated_tokens_count, tuned_max_tokens, max_tokens)

                    truncated += truncated_tokens_count
                    prompts_set = [(this_messages, tuned_output)]

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
                each_chunk_prompt_set, _, _ = self.build_prompts_from_input(data, params, cloned_prompt_format_args, function_name)

                # add the newly build prompt and max tokens into the list
                prompts_set.extend(each_chunk_prompt_set)

        user_prompts_size = 0
        for prompt, _ in prompts_set:
            for message in prompt:
                if 'content' in message and message["role"] == "user":
                    user_prompts_size += len(message["content"])

        return prompts_set, user_prompts_size, truncated

    def get_chunkable_input(self) -> str:
        raise NotImplementedError

    def safe_format(self, string, **kwargs):
        class SafeDict(dict):
            def __missing__(self, key):
                return ''

        safe_dict = SafeDict(kwargs)
        return string.format_map(safe_dict)

    def safe_dict(self, d):
        return {k: v if v is not None else '' for k, v in d.items()}

    def generate_messages(self, _, prompt_format_args) -> List[Dict[str, Any]]:
        prompt_format_args = self.safe_dict(prompt_format_args)

        # handle variable replacements safely
        this_messages = []

        # Generate messages for all roles
        for prompt in self.prompts:
            if prompt[0][0] == 'main':  # we handle 'main' last
                main_prompt = prompt[1]
                continue

            # context prompts are special - they are only included if the tags are present
            #   and they can replicate depending on number of context inputs
            if prompt[0][1].startswith('context-'):
                if any(tag not in prompt_format_args for tag in re.findall(r'\{(.+?)\}', prompt[1])):
                    print(f"Skipping {prompt[0][0]} prompt {prompt[0][1]} due to missing tags")
                    continue

            # Check if this prompt text contains a '{tag}' that exists in our reformatting args
            for tag in re.findall(r'\{(.+?)\}', prompt[1]):
                if tag not in prompt_format_args:
                    continue

                if not isinstance(prompt_format_args.get(tag), list):
                    continue

                role, content_list = prompt_format_args[tag]
                for content in content_list:
                    # inject each piece of custom content into the prompt
                    this_prompt_format_args = prompt_format_args.copy()
                    this_prompt_format_args[tag] = content
                    formatted_content = self.safe_format(prompt[1], **this_prompt_format_args)

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
                print(f"Skipping empty {prompt[0][0]} prompt {prompt[0][1]}")
                continue

            this_messages.append({
                "role": prompt[0][0],
                "content": content
            })

        # Check if main prompt contains a '{tag}' that exists in data
        for tag in re.findall(r'\{(.+?)\}', main_prompt):
            if isinstance(prompt_format_args.get(tag), list):
                new_format_arg = ""
                _, content_list = prompt_format_args[tag]
                for content in content_list:
                    new_format_arg = f"{new_format_arg}\n{content}"

                # inject the combined content into the args for prompt injection
                prompt_format_args[tag] = new_format_arg

        # 'main' is always the last message and it's always from the 'user'
        this_messages.append({
            "role": "user",
            "content": self.safe_format(main_prompt, **prompt_format_args)
        })

        return this_messages

    def makeOpenAICall(self, account, function_name, correlation_id, attempt, timeBufferRemaining, params) -> dict:
        print(f"{function_name}:{account['email']}:{correlation_id}:Starting OpenAI API call (Attempt {attempt + 1})")

        start_time = time.time()
        try:
            response = openai.ChatCompletion.create(**params, timeout=timeBufferRemaining, request_timeout=timeBufferRemaining)

            print(f"{function_name}:{account['email']}:{correlation_id}:SUCCESS:Finished OpenAI API call (Attempt {attempt + 1} in {mins_and_secs(time.time() - start_time)})")

            return response

        except Exception as e:
            print(f"{function_name}:{account['email']}:{correlation_id}:ERROR({str(e)}):Finished OpenAI API call (Attempt {attempt + 1} in {mins_and_secs(time.time() - start_time)})")
            raise

    def runAnalysis(self, params, account, function_name, correlation_id) -> dict:

        secondsInAMinute = 60

        # Lambda calls must be done in 15 mins or less
        #   We'll give ourselves a little buffer in case other operations
        #   than OpenAI take 30-90 seconds (including stripe or GitHub calls)
        totalAnalysisTimeBuffer = int(13.50 * secondsInAMinute)  # 13 minutes 30 seconds

        MaxTimeoutSecondsForAllOpenAICalls = int(12 * secondsInAMinute)  # 12 minutes

        MaxTimeoutSecondsForSingleOpenAICall = int(6 * secondsInAMinute)  # 6 minutes

        max_retries = 3
        start_time = time.time()

        # we're going to retry on intermittent network issues
        # e.g. throttling, connection issues, service down, etc..
        # Note that with RateLimit error, we could actually make it worse...
        #    So for rate limit we wait a lot longer to retry (e.g. 30-60 seconds)
        # https://platform.openai.com/docs/guides/error-codes/python-library-error-types
        for attempt in range(max_retries + 1):

            try:
                timeBufferRemaining = round(totalAnalysisTimeBuffer - (time.time() - start_time), 2)

                if timeBufferRemaining < 0:
                    raise Exception(f"Timeout exceeded for OpenAI call: {mins_and_secs(totalAnalysisTimeBuffer)}")

                openAICallTimeBufferRemaining = round(MaxTimeoutSecondsForAllOpenAICalls - (time.time() - start_time), 2)

                # we'll let the OpenAI call take at most the per-call max, or what's remaining
                #       of the total calls buffer
                allotedTimeBufferForThisOpenAPICall = round(min(
                    openAICallTimeBufferRemaining,
                    MaxTimeoutSecondsForSingleOpenAICall), 2)

                print(f"OpenAI Timeout Settings for this call: totalAnalysisTimeBuffer:{mins_and_secs(totalAnalysisTimeBuffer)}, "
                      f"allotedTimeBufferForThisOpenAPICall:{mins_and_secs(allotedTimeBufferForThisOpenAPICall)}, "
                      f"openAICallTimeBufferRemaining:{mins_and_secs(openAICallTimeBufferRemaining)}, "
                      f"timeBufferRemaining:{mins_and_secs(timeBufferRemaining)}")

                response = self.makeOpenAICall(
                    account,
                    function_name,
                    correlation_id,
                    attempt,
                    allotedTimeBufferForThisOpenAPICall,
                    params)

                if attempt > 0:
                    print(f"{function_name}:{account['email']}:{correlation_id}:Succeeded after {attempt} retries")

                return dict(
                    message=response.choices[0].message,
                    response=response.choices[0].message.content,
                    finish=response.choices[0].finish_reason,
                    input_tokens=response.usage.prompt_tokens,
                    output_tokens=response.usage.completion_tokens)

            except (openai.error.Timeout, requests.exceptions.Timeout) as e:
                error = e
                error_msg = str(e)
                error_type = "Timeout"

            except (openai.error.ServiceUnavailableError) as e:
                error = e
                error_msg = str(e)
                error_type = "Service Unavailable"

            except (openai.error.APIConnectionError, openai.error.APIError) as e:
                error = e
                error_msg = str(e)
                error_type = "API"

            except openai.error.RateLimitError as e:
                error = e

                error_msg = str(e)
                error_type = "Rate Limit"

                if "40000 / min" in error_msg:
                    randomSleep = random.uniform(30, 60)
                else:
                    randomSleep = random.uniform(5, 15)

                print(f"{function_name}:{correlation_id}:RateLimitError, sleeping for {mins_and_secs(randomSleep)} before retry")

                # if we hit the rate limit, send a cloudwatch alert and raise the error
                capture_metric(
                    account['customer'], account['email'], function_name, correlation_id,
                    {"name": InfoMetrics.OPENAI_RATE_LIMIT, "value": 1, "unit": "None"})

                timeBufferRemaining = totalAnalysisTimeBuffer - (time.time() - start_time)

                if timeBufferRemaining < 0:
                    raise Exception(f"Timeout exceeded for OpenAI call: {mins_and_secs(totalAnalysisTimeBuffer)}")

                time.sleep(randomSleep)

            if error_type != "Timeout" and attempt < max_retries and (time.time() - start_time + random.uniform(2, 5)) < totalAnalysisTimeBuffer:

                timeBufferRemaining = totalAnalysisTimeBuffer - (time.time() - start_time)

                if timeBufferRemaining < 0:
                    raise Exception(f"Timeout exceeded for OpenAI call: {mins_and_secs(totalAnalysisTimeBuffer)}")

                randomSleep = random.uniform(2, 5)
                print(f"{function_name}:{account['email']}:{correlation_id}:Retrying in {mins_and_secs(randomSleep)} after {error_type}: {error_msg}")
                time.sleep(randomSleep)
            else:
                print(f"{function_name}:{account['email']}:{correlation_id}:FAILED after {attempt} retries:Error: {error_type}: {error_msg}")
                raise error

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
                  f"SUCCESS processing chunked prompt {i} in {mins_and_secs(end_time - start_time)}:"
                  f"Finish:{result['finish'] if result['finish'] is not None else 'Incomplete'}")
            return result
        except Exception as e:
            end_time = time.monotonic()
            print(f"{function_name}:{account['email']}:{correlation_id}:Thread-{threading.current_thread().ident}:"
                  f"Error processing chunked prompt {i} after {mins_and_secs(end_time - start_time)}:"
                  f"Finish:{result['finish'] if result is not None and 'finish' in result and result['finish'] is not None else 'Incomplete'}::error:{str(e)}")
            raise

    def initialize_from_data(self, log, data, account, function_name, correlation_id, prompt_format_args, params) -> Tuple[dict, dict]:

        # enable user to override the model to gpt-3 or gpt-4
        if 'model' in data:
            params["model"] = data['model']

        if "model" in params:
            log(f"Using model {params['model']}")
            data['model'] = params['model']

        # https://community.openai.com/t/cheat-sheet-mastering-temperature-and-top-p-in-chatgpt-api-a-few-tips-and-tricks-on-controlling-the-creativity-deterministic-output-of-prompt-responses/172683
        if 'top_p' in data:
            params["top_p"] = float(data['top_p'])
        elif 'temperature' in data:
            params["temperature"] = float(data['temperature'])

        if 'guidelines' not in data:
            prompt_format_args['guidelines'] = "This software project has no additional special architectural guidelines or constraints."
        else:
            # get the JSON object out of the data payload
            # older clients sent the structure as an embedded JSON string
            # newer clients send the data as a normal object
            guidelines_data = data['guidelines'] if not isinstance(data['guidelines'], str) else json.loads(data['guidelines'])
            guidelines_data = guidelines_data[1]  # the first element is the 'system' role of guidelines
            guidelines = ""
            for guideline in guidelines_data:
                guidelines = f"{guidelines}\n\n {guideline}"
            prompt_format_args['guidelines'] = guidelines

        if 'system_identity' not in data:
            prompt_format_args['system_identity'] = "I am a software and architecture analysis bot named Sara."
        else:
            prompt_format_args['system_identity'] = data['system_identity']

        self.inject_context(data, prompt_format_args)

        # use the client's requested output format, or the default
        outputFormat = self.default_output_format if 'outputFormat' not in data else data['outputFormat']
        # if the requested format is prose, do nothing
        if outputFormat is not AnalysisOutputFormat.prose:

            outputExample = ""

            if outputFormat not in self.supported_output_formats:
                log(f"Unsupported output format {outputFormat.upper} for {function_name}; default to {self.default_output_format}")
            elif outputFormat is not self.default_output_format:
                log(f"Using non-default output format {outputFormat.upper} for {function_name}; default was {self.default_output_format}")
            elif outputFormat is AnalysisOutputFormat.json:
                log(f"Using JSON output format for {function_name}")

            if outputFormat is AnalysisOutputFormat.bulletedList:
                outputExample = "Please describe results in structured bulleted list like the following\n" \
                                "* First issue\n" \
                                "* Second issue\n" \
                                "..." \
                                "* Third issue\n"

            elif outputFormat is AnalysisOutputFormat.numberedList:
                outputExample = "Please describe results in structured numbered list in markdown like the following\n" \
                                "1. an issue\n" \
                                "2. an issue\n" \
                                "..." \
                                "n. an issue\n"

            elif outputFormat is AnalysisOutputFormat.rankedList:
                outputExample = "Please describe results in ranked numbered list in markdown, with the most important issue listed first, and the least important issue listed last, like the following\n" \
                                "1. Most important issue\n" \
                                "2. Next most important issue\n" \
                                "..." \
                                "n. Least important issue\n"

            if outputExample != "":
                prompt_format_args['outputFormat'] = outputExample

        return params, prompt_format_args

    def inject_context(self, data, prompt_format_args):
        if 'summaries' not in data and 'context' not in data:
            prompt_format_args['summaries_type'] = 'general'
            prompt_format_args['summaries_data'] = 'This software project should be well designed and bug-free.'
            return

        # for backward compatibility - old clients pass array with first element the 'system' role
        if 'summaries' in data:
            # get the JSON object out of the data payload
            # older clients sent the structure as an embedded JSON string
            # newer clients send the data as a normal object
            summaries_data = data['summaries'] if not isinstance(data['summaries'], str) else json.loads(data['summaries'])
            summaries_data = summaries_data[1]  # the first element is the 'system' role of summaries
            summaries = ""

            for summary in summaries_data:
                summaries = f"{summaries}\n\n {summary}"
            prompt_format_args['summaries_type'] = 'general'
            prompt_format_args['summaries_data'] = summaries

            return

        # get the JSON object out of the data payload
        context_json = data['context']
        context_names = ""
        context_data = ""
        for context in context_json:
            if 'data' not in context:
                print(f"Skipping context {context['name']} due to missing data")
                continue

            # store contextual project summary data for use in prompts
            if context['type'] == AnalysisContextType.projectSummary:
                context_names = f"{context_names}, {context['name']}" if context_names != "" else f"{context['name']}"
                context_data = f"{context['data']}\n\n {context_data}" if context_data != "" else f"{context['data']}"

                prompt_format_args['summaries_type'] = context_names
                prompt_format_args['summaries_data'] = context_data

            # for related and historical data, we send mulitple messages for each entry to managed and truncated
            elif context['type'] in [AnalysisContextType.history, AnalysisContextType.related]:
                if f"context_{context['type']}" not in prompt_format_args:
                    prompt_format_args[f"context_{context['type']}"] = ['system', [context['data']]]
                else:
                    prompt_format_args[f"context_{context['type']}"][1].append(context['data'])

            # for user focus, we send one system prompt so analysis sees all user-focus in one message
            elif context['type'] == AnalysisContextType.userFocus:
                prompt_format_args['context_userFocus'] = ['system', [context['data']]] if 'context_userFocus' not in prompt_format_args else ['system', [f"{prompt_format_args['context_userFocus'][1][0]}\n\n {context['data']}"]]

            else:
                print(f"Unsupported context type {context['type']} - discarding data for {context['name']}")

    def process_input(self, data, account, function_name, correlation_id, prompt_format_args) -> dict:

        self.load_prompts()

        email = account['email']
        # {"customer": customer, "subscription": subscription, "subscription_item": subscription_item, "email": email}
        customer = account['customer']

        def log(message, use_thread=False, show_customer=False):
            if show_customer:
                message = f"{customer['name']}:{customer['id']}:{message}"

            if use_thread:
                print(f"{function_name}:{email}:{correlation_id}:{threading.current_thread().ident}:{message}")
            else:
                print(f"{function_name}:{email}:{correlation_id}:{message}")

        params = self.default_params.copy()  # Create a copy of the defaults so derived classes can make changes per input call
        params, prompt_format_args = self.initialize_from_data(log, data, account, function_name, correlation_id, prompt_format_args, params)

        prompt_set: List[Tuple[str, int]] = []

        prompt_set, prompts_size, truncated = self.build_prompts_from_input(data, params, prompt_format_args, function_name)
        chunked = len(prompt_set) > 1

        success = False
        try:
            results = None
            result = None
            # if chunked, we're going to run all chunks in parallel and then concatenate the results at end
            if chunked:
                log(f"Chunked user input - {len(prompt_set)} chunks")

                totalChunks = len(prompt_set)
                tokensPerChunk = OpenAIDefaults.rate_limit_tokens_per_minute / totalChunks

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

                    log(f"Thread-{threading.current_thread().ident} Summary {index} delaying for {mins_and_secs(delay)}")

                    time.sleep(delay)  # Delay based on the number of words in the prompt

                    if delay > 5:  # If delay is more than 5 seconds, log it
                        log(f"Summary {index} delayed for {mins_and_secs(delay)}", True)

                    return self.runAnalysisForPrompt(index, prompt[0], prompt[1], params, account, function_name, correlation_id)

                # launch all the parallel threads to run analysis with the unique chunked prompt for each
                # Throttling the rate of file processing
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    results = list(executor.map(runAnalysisForPromptThrottled, enumerate(prompt_set)))
            # otherwise, run once
            else:
                # if truncated user input, report it out, and update the OpenAI input with the truncated input
                if truncated:
                    log(f"Truncated user input, discarded {truncated} tokens")

                # run the analysis with single input
                singleIndex = 0
                results = [self.runAnalysisForPrompt(singleIndex, prompt_set[singleIndex][0],
                                                     prompt_set[singleIndex][1], params, account, function_name, correlation_id)]
                result = results[0]['response']

            def reassemble_function_results(results):
                if 'function_call' not in results[0]['message']:
                    return False, None

                items = []
                # if we get here, we have a function call in the results array.  loop through each of the results and add the array of arguments to the bugs array
                # result['results'][0]['message']['function_call']['arguments'] is a JSON formatted string. parse it into a JSON object.  it may be corrupt, so ignore
                # any errors
                for r in results:
                    json_items = json.loads(r['message']['function_call']['arguments'])
                    items.extend(json_items)

                return True, items

            isFunction, items = reassemble_function_results(results)
            if isFunction:
                # this isn't a very useful representation, but it allows us to correctly calculate cost of the function call
                result = json.dumps(items)

            # otherwise, we need to update the result with the truncation warning to user
            elif truncated:
                truncation = markdown_emphasize(
                    f"Truncated input, discarded ~{truncated} symbols or words\n\n")
                result = f"{truncation}{results[0]['response']}"

            # or if chunked, we're going to reassemble all the chunks
            elif chunked:
                result = "\n\n".join([r['response'] for r in results])  # by concatenating all results into a single string

            success = True

        # tracing repro for invalid max tokens
        except openai.error.InvalidRequestError as e:
            if "maximum context length" in str(e):
                if 'contextMetadata' in data:
                    contextMetadata = json.loads(data['contextMetadata'])
                    sourceFile = contextMetadata['sourceFile'] if 'sourceFile' in contextMetadata else ''
                if 'inputMetadata' in data:
                    inputMetadata = json.loads(data['inputMetadata'])
                    cellId = inputMetadata['id'] if 'id' in inputMetadata else ''

                log(f"InvalidRequestError:MaxTokens error: sourceFile:{sourceFile}, cellId:{cellId}: {str(e)}")
            raise

        finally:

            try:
                user_input = self.collate_all_user_input(prompt_format_args)
                user_input_size = len(user_input)
                openai_customerinput_tokens, openai_customerinput_cost = get_openai_usage_per_string(user_input, True, data.get('model'))
                openai_input_tokens, openai_input_cost = get_openai_usage_per_token(
                    sum([r['input_tokens'] for r in results]), True, data.get('model')) if results is not None else (0, 0)

                # Get the cost of the outputs and prior inputs - so we have visibiity into our cost per user API
                output_size = len(result) if result is not None else 0

                boost_cost = get_boost_cost(user_input_size + output_size)

                openai_output_tokens, openai_output_cost = get_openai_usage_per_token(
                    sum([r['output_tokens'] for r in results]), False, data.get('model')) if results is not None else (0, 0)
                openai_tokens = openai_input_tokens + openai_output_tokens
                openai_cost = openai_input_cost + openai_output_cost

                try:
                    if success:
                        # update the billing usage for this analysis (charge for input + output) as long as analysis is successful
                        update_usage_for_text(account, user_input_size + output_size, function_name)
                except Exception:
                    success = False
                    exception_info = traceback.format_exc().replace('\n', ' ')
                    log(f"UPDATE_USAGE_FAILURE:"
                        f"Error updating ~${boost_cost} usage: {exception_info}", False, True)
                    capture_metric(customer, email, function_name, correlation_id,
                                   {"name": InfoMetrics.BILLING_USAGE_FAILURE, "value": round(boost_cost, 5), "unit": "None"})

                    pass  # Don't fail if we can't update usage / but that means we may have lost revenue

                capture_metric(customer, email, function_name, correlation_id,
                               {'name': CostMetrics.PROMPT_SIZE, 'value': prompts_size, 'unit': 'Count'},
                               {'name': CostMetrics.RESPONSE_SIZE, 'value': output_size, 'unit': 'Count'},
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
                log(f"Error capturing metrics: {exception_info}", False, True)
                pass  # Don't fail if we can't capture metrics

        return {
            "results": results,
            "output": result,
            "truncated": bool(truncated > 0),
            "chunked": chunked
        }

    def get_excluded_input_keys(self) -> list[str]:
        openai_config_params = [
            'model',
            'top_p',
            'temperature'
        ]
        processor_params = [
            'chunking',
        ]
        system_context_params = [
            'system_identity']

        # large_system_context_params = [
        #     'guidelines',
        #     'summaries_type',
        #     'summaries_data']

        # context_data = [
        #    'context_userFocus',
        #    'context_history',
        #    'context_related',
        #    'context_projectSummary']

        return openai_config_params + processor_params + system_context_params

    def flatten_and_join(self, lst):
        result = []
        for i in lst:
            if isinstance(i, list):
                result.extend(self.flatten_and_join(i))
            else:
                result.append(str(i))
        return ' '.join(result)

    def collate_all_user_input(self, prompt_format_args):
        # remove any keys used for control of the processing, so we only charge for user input
        excluded_keys = self.get_excluded_input_keys()

        # Use lambda function to handle list of strings
        input_list = map(
            lambda key: self.flatten_and_join(prompt_format_args[key]) if isinstance(prompt_format_args[key], (list, tuple)) else str(prompt_format_args[key]),
            [key for key in prompt_format_args if key not in excluded_keys]
        )

        return ' '.join(input_list)
