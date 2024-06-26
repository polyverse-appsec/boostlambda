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
import re
import datetime
from collections import namedtuple

from chalice import UnprocessableEntityError

from .. import pvsecret

from chalicelib.markdown import markdown_emphasize
from chalicelib.telemetry import capture_metric, InfoMetrics, CostMetrics
from chalicelib.usage import (
    get_openai_usage_per_token,
    get_openai_usage_per_string,
    max_tokens_for_model,
    OpenAIDefaults,
    num_tokens_from_string,
    decode_string_from_input,
    tokens_from_function)
from chalicelib.storage import (
    get_file,
    get_file_time,
    search_storage
)
from chalicelib.payments import update_usage_for_text
from chalicelib.log import mins_and_secs
from chalicelib.openai_throttler import (
    Throttler,
    max_timeout_seconds_for_all_openai_calls_default,
    max_timeout_seconds_for_single_openai_call_default,
    total_analysis_time_buffer_default,
)

from chalicelib.aws import get_current_lambda_cost

key_ChunkedInputs = 'chunked_inputs'
key_ChunkPrefix = 'chunk_prefix'
key_NumberOfChunks = 'chunks'
key_IsChunked = 'chunked'
key_ChunkingPrompt = 'chunking'

# Define the directory where prompt files are stored
PROMPT_DIR = "prompts"

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
    training = "training"


# changes pascal and camel cased strings into space delimited strings
def spacify(input):
    return ' '.join(re.findall(r'[A-Z]?[a-z]+|[A-Z]+(?=[A-Z]|$)', input))


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
        context_training_prompt = ['user', 'context-training-user.prompt']
        context_training_response = ['assistant', 'context-training-assistant.prompt']

        # If prompt_filenames is not None, create a copy, otherwise initialize an empty list
        new_prompt_filenames = prompt_filenames.copy() if prompt_filenames is not None else []

        # Iterate over the new_prompt_filenames
        for i, prompt in enumerate(new_prompt_filenames):
            # Check if the prompt type is 'system'
            if prompt[0] != 'system':
                continue

            # Insert the summaries after the first system prompt
            new_prompt_filenames.insert(i + 1, summaries)

            # insert the context-aware prompts after the summaries
            #   we start with historical data
            new_prompt_filenames.insert(i + 2, context_history)
            #   then add related info
            new_prompt_filenames.insert(i + 3, context_related)
            #   then add the key user focus
            new_prompt_filenames.insert(i + 4, context_userFocus)

            # finally add training
            new_prompt_filenames.insert(i + 5, context_training_prompt)
            new_prompt_filenames.insert(i + 6, context_training_response)

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

        self.prompts = None
        self.load_prompts()

    def load_prompt(self, prompt_filename) -> str:
        return get_file(os.path.join(PROMPT_DIR, prompt_filename))

    def load_prompts(self):

        # if prompts already loaded and file timestamps have not changed, do nothing
        if self.prompts is not None and not self.check_prompt_files_changed():
            print(f"{self.__class__.__name__}: Prompts already loaded and files have not changed; skipping refresh of prompts")
            return

        # otherwise load the prompts
        prompts = []

        # load prompts specified in 'prompt_filenames'
        for prompt_filename in self.prompt_filenames:
            prompts.append([prompt_filename, self.load_prompt(prompt_filename[1])])

        # load numbered prompts
        for prompt_key in self.numbered_prompt_keys if self.numbered_prompt_keys is not None else []:
            # if the definition is a prompt & response pairing, load both files and process in order
            if prompt_key[0] == 'response':
                for file in search_storage(PROMPT_DIR, f"{prompt_key[1]}-user-*.prompt"):

                    response_user_prompt_filename = os.path.basename(file)

                    # response has a user prompt....
                    prompts.append([["user", response_user_prompt_filename], get_file(file)])

                    # construct the corresponding assistant file name
                    assistant_file = file.replace("-user-", "-assistant-")
                    response_assistant_prompt_filename = os.path.basename(assistant_file)

                    prompts.append([["assistant", response_assistant_prompt_filename], get_file(assistant_file)])
            else:
                file_list = search_storage(PROMPT_DIR, f"{prompt_key[1]}-{prompt_key[0]}-*.prompt")

                for file in file_list:
                    dynamic_filename = os.path.basename(file)
                    prompts.append([[prompt_key[0], dynamic_filename], get_file(file)])

        self.prompts = prompts

        # Store the last modification timestamps in the cache
        self.cache_prompt_files_timestamps()

    def check_prompt_files_changed(self):
        # since prompts contains dynamic prompts, we'll build a temporary list
        #   of static and dynamic prompt filenames to check for changes
        prompts_to_check = self.prompt_filenames.copy()

        # make sure all dynamic prompts and prompt pairs are added to the prompt_filenames list
        #   so we can effectively check their timestamps
        for prompt in self.prompts:
            if prompt[0][1] not in [prompt_file[1] for prompt_file in self.prompt_filenames]:
                prompts_to_check.append([prompt[0][0], prompt[0][1]])

        # Compare the current timestamps with the cached timestamps
        files_changed = False
        for prompt_filename in prompts_to_check:
            file_path = os.path.join(PROMPT_DIR, prompt_filename[1])
            current_timestamp = get_file_time(file_path)

            # file not in cache, it's new; update timestamp
            if file_path not in self.prompt_files_timestamps:
                files_changed = True
                print(f"File '{prompt_filename[1]}' has changed. New timestamp: {time.strftime('%Y-%m-%d %H:%M', time.localtime(current_timestamp))}")

            # timestamp doesn't match, file has changed
            elif self.prompt_files_timestamps[file_path] != current_timestamp:
                files_changed = True
                old_timestamp = self.prompt_files_timestamps[file_path]
                time_difference = (current_timestamp - old_timestamp) / 60  # Difference in minutes
                print(f"File '{prompt_filename[1]}' has changed. New timestamp: {time.strftime('%Y-%m-%d %H:%M', time.localtime(current_timestamp))}. Time difference: {time_difference:.2f} minutes.")

            # timestamp matches, just move on
            else:
                continue

            # Update the timestamp in the cache
            self.prompt_files_timestamps[file_path] = current_timestamp

        return files_changed

    def cache_prompt_files_timestamps(self):
        # Store the last modification timestamps in the cache
        self.prompt_files_timestamps = {}
        for prompt_filename in self.prompt_filenames:
            file_path = os.path.join(PROMPT_DIR, prompt_filename[1])
            self.prompt_files_timestamps[file_path] = get_file_time(file_path)

    def insert_context(self, data, newContext):
        if 'context' in data:
            for index, contextData in enumerate(data['context']):
                if contextData['name'] == 'productDocumentation':
                    data['context'].pop(index)
        else:
            data['context'] = []

        data['context'].append(newContext)

    def optimize_content(self, this_messages: List[Dict[str, Any]], data) -> Tuple[List[Dict[str, Any]], int]:
        def truncate_system_message(sys_message, index, total_system_buffer, total_system_tokens):
            sys_token_count, sys_tokens = num_tokens_from_string(sys_message['content'], data.get('model'))
            proportion = sys_token_count / total_system_tokens
            min_quota = max(min_token_quota, int(total_system_buffer * min_quota_percent))
            retained_tokens = int(min(max_quota, max(min_quota, int(total_system_buffer * proportion))))

            if sys_token_count > retained_tokens:
                sys_message['content'] = decode_string_from_input(sys_tokens[:retained_tokens], data.get('model'))
                truncated = sys_token_count - retained_tokens
                discard_percent = retained_tokens / sys_token_count
                print(f"{self.__class__.__name__}:Truncation:"
                      f"System message {index} quota: {proportion * 100:.1f}% of {total_system_buffer} tokens,"
                      f" max per quota {max_quota}, discarded {truncated} of {sys_token_count}: {discard_percent * 100:.1f}% retained")
                return True, truncated
            return False, 0

        # collect all system and training messages excluding the first and last messages
        system_messages = [message for message in this_messages if 'content' in message and message != this_messages[0] and message != this_messages[-1]]
        training_messages = [message for message in system_messages if message['role'] != 'system']

        # count total token length in all non-empty messages excluding the first and last messages
        total_system_tokens = sum(num_tokens_from_string(message['content'], data.get('model'))[0]
                                  for message in this_messages)
        total_training_tokens = sum(num_tokens_from_string(message['content'], data.get('model'))[0]
                                    for message in this_messages if message['role'] != 'system')

        total_system_buffer = self.calculate_system_message_token_buffer(data.get('max_tokens', self.get_default_max_tokens(data)))

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
        truncated_system_messages_count = 0
        truncated_training_messages_count = 0
        system_truncated_token_count = 0
        training_truncated_token_count = 0
        total_truncated_token_count = 0

        """Compute combined length of assistant and user messages."""
        def combined_length(assistant_msg, user_msg):
            return len(assistant_msg.get('content', '')) + len(user_msg.get('content', ''))

        message_sequences = []  # To store sequences of messages and their types

        # get the sorting sequence for all messages except the first and last
        index = 1
        while index < len(this_messages) - 1:
            message = this_messages[index]
            # If it's a system message and not the first or last message
            if message['role'] == 'system':
                message_sequences.append((index, 'system', len(message.get('content', ''))))
                index += 1
            # If it's a user (training) prompt followed by an assistant (training) response
            elif message['role'] == 'user' and index + 1 < len(this_messages) and this_messages[index + 1]['role'] == 'assistant':
                length = combined_length(message, this_messages[index + 1])
                message_sequences.append((index, 'user_assistant', length))
                index += 2
            else:
                print(f"Unexpected message type in system message sequence: {message['role']}")
                message_sequences.append((index, 'system', len(message.get('content', ''))))
                index += 1

        # Sort sequences based on their lengths
        sorted_sequences = sorted(message_sequences, key=lambda x: x[2])

        # Create a dictionary to store the modified content of the messages
        modified_content_dict = {}

        # Add the first message
        new_messages.append(this_messages[0])

        # Add all other system messages based on optimized length and order
        for idx, message_type, _ in sorted_sequences:
            if message_type == 'system':
                was_truncated, truncated = truncate_system_message(this_messages[idx], idx, total_system_buffer, total_system_tokens)
                truncated_system_messages_count += was_truncated
                total_truncated_token_count += truncated
                system_truncated_token_count += truncated
                modified_content_dict[idx] = this_messages[idx]['content']
            elif message_type == 'user_assistant':
                was_truncated, truncated = truncate_system_message(this_messages[idx], idx, total_system_buffer, total_system_tokens)
                truncated_training_messages_count += was_truncated
                total_truncated_token_count += truncated
                training_truncated_token_count += truncated
                modified_content_dict[idx] = this_messages[idx]['content']
                modified_content_dict[idx + 1] = this_messages[idx + 1]['content']

        # Now, using the original order of the messages, append them to new_messages after modification
        for idx, message_type, _ in message_sequences:
            if idx in modified_content_dict:
                this_messages[idx]['content'] = modified_content_dict[idx]
            new_messages.append(this_messages[idx])
            if message_type == 'user_assistant':
                if idx + 1 in modified_content_dict:
                    this_messages[idx + 1]['content'] = modified_content_dict[idx + 1]
                new_messages.append(this_messages[idx + 1])

        # add the last message (as long as we have multiple messages)
        if len(this_messages) > 1:
            new_messages.append(this_messages[-1])

        if truncated_system_messages_count > 0:
            print(f"{self.__class__.__name__}:Content-Optimization:"
                  f"Truncated {truncated_system_messages_count}/{len(system_messages)} system messages, "
                  f" {round(system_truncated_token_count/total_system_tokens * 100, 1)}% ({system_truncated_token_count}/{total_system_tokens}) tokens, "
                  f" to meet total system token quota: {total_system_buffer}")

        if truncated_training_messages_count > 0:
            print(f"{self.__class__.__name__}:Content-Optimization:"
                  f"Truncated {truncated_training_messages_count}/{len(training_messages)} training messages, "
                  f" {round(training_truncated_token_count/total_training_tokens * 100, 1)}% ({training_truncated_token_count}/{total_training_tokens}) tokens, "
                  f" to meet total system token quota: {total_system_buffer}")

        discarded_messages = len(this_messages) - len(new_messages)
        if discarded_messages > 0:
            print(f"{self.__class__.__name__}:Content-Optimization:"
                  f"Discarded {discarded_messages} messages with no content")

        return new_messages, total_truncated_token_count

    def chunk_input_based_on_token_limit(self,
                                         data,
                                         prompt_format_args,
                                         input_token_buffer,
                                         extra_non_message_content_size,
                                         ) -> Tuple[List[Tuple[List[dict[str, any]], int, int]], int]:

        truncation = 0
        # get the ideal full prompt - then we'll figure out if we need to break it up further
        this_messages = self.generate_messages(data, prompt_format_args)
        this_messages, this_truncation = self.optimize_content(this_messages, data)
        truncation += this_truncation

        full_message_content_tokens_count = sum(
            num_tokens_from_string(message["content"], data.get('model'))[0] for message in this_messages)

        # if we can fit the chunk into one token buffer, we'll process and be done
        max_tokens = self.get_default_max_tokens(data)
        tuned_max_tokens = max_tokens - full_message_content_tokens_count - extra_non_message_content_size
        tuned_output = self.calculate_output_token_buffer(data, full_message_content_tokens_count, tuned_max_tokens, max_tokens, False)
        input_token_count = full_message_content_tokens_count + extra_non_message_content_size

        # calling function already excluded the function content size from the input buffer, so we don't need to add it here
        if (full_message_content_tokens_count < input_token_buffer):

            if input_token_count + tuned_output > max_tokens:
                print(f"Overall Analysis Buffer of {max_tokens} tokens exceeded for Single Chunk Processing: Input={input_token_count}, Output={tuned_output}, Function={extra_non_message_content_size}")
                raise UnprocessableEntityError("Input is too large to process. Please try again with less input.")
            else:
                print(f"Overall Analysis Buffer of {max_tokens} used for Single Chunk Processing Chunk Processing: Input={input_token_count}, Output={tuned_output}, Function={extra_non_message_content_size}")

            return [(this_messages, tuned_output, input_token_count, extra_non_message_content_size)], truncation

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

            these_tokens_count = sum(
                num_tokens_from_string(message["content"], data.get('model'))[0] for message in this_messages)

            if these_tokens_count > input_token_buffer:
                message_regeneration_variance = (these_tokens_count - input_token_buffer) / input_token_buffer
                print(f"ChunkingInputFailed: Exceeded Input Buffer size={input_token_buffer}, "
                      f"Chunk size={these_tokens_count}, "
                      f"Splitting Variance={message_regeneration_variance}, ")
                raise UnprocessableEntityError("Input is too large to process. Please try again with less input.")

            # need to add the function content size to the token count to ensure we
            #   calculate the output buffer size correctly
            these_tokens_count += extra_non_message_content_size

            # get the new remaining max tokens we can accommodate with output
            max_tokens = self.get_default_max_tokens(data)
            tuned_max_tokens = max_tokens - these_tokens_count
            tuned_output = self.calculate_output_token_buffer(data, these_tokens_count, tuned_max_tokens, max_tokens, False)

            if these_tokens_count + tuned_output > max_tokens:
                print(f"Overall Analysis Buffer of {max_tokens} tokens exceeded for Chunk {len(this_messages_chunked)} Processing: Input={these_tokens_count}, Output={tuned_output}, Function={extra_non_message_content_size}")
                raise UnprocessableEntityError("Input is too large to process. Please try again with less input.")
            else:
                print(f"Overall Analysis Buffer of {max_tokens} used for Chunk {len(this_messages_chunked)} Processing: Input={these_tokens_count}, Output={tuned_output}, Function={extra_non_message_content_size}")

            # store the updated message to be processed
            this_messages_chunked.append((this_messages, tuned_output, these_tokens_count, extra_non_message_content_size))

            # Move the index to the next chunk starting point
            i = end_idx

        return this_messages_chunked, truncation

    def calculate_input_token_buffer(self, total_max) -> int:
        return math.floor(total_max * 0.5)

    # we're only going to use 25% of our input buffer for system messages (e.g. background info)
    def calculate_system_message_token_buffer(self, total_max) -> int:
        return math.floor(self.calculate_input_token_buffer(total_max) * 0.25)

    def get_default_max_tokens(self, data=None) -> int:
        if data is None:
            return max_tokens_for_model(self.default_params.get('model'))
        else:
            return max_tokens_for_model(data.get('model'))

    def calculate_output_token_buffer(self, data, input_buffer_size, output_buffer_size, total_max, enforce_max=True) -> int:

        def ensure_max_output_token_limit(data, output_buffer_size):
            if data.get('model') == OpenAIDefaults.boost_model_gpt4_turbo:
                if output_buffer_size > OpenAIDefaults.boost_max_tokens_gpt_4_turbo_output:
                    output_buffer_size = OpenAIDefaults.boost_max_tokens_gpt_4_turbo_output
            return output_buffer_size

        # if the input is larger than our output buffer already, we'll just allow the entire output buffer to be used
        if input_buffer_size > output_buffer_size:
            if enforce_max and input_buffer_size + output_buffer_size > total_max:
                print(f"Unable to calculate output token capacity - Overall Capacity ({total_max}) Exceeded (Default Size): Input={input_buffer_size}, Output={output_buffer_size}")
                raise UnprocessableEntityError("Input is too large to process. Please try again with less input.")

            return ensure_max_output_token_limit(data, output_buffer_size)

        # otherwise, we'll calculate the remaining buffer size
        remainingBuffer = total_max - input_buffer_size

        # at least 10% of total max if it fits in remainingBuffer
        ten_percent_total = total_max * 0.1
        minimum_buffer = int(min(remainingBuffer, ten_percent_total))

        # the lesser of the remainingBuffer or 2x the input_buffer (for very tiny inputs)
        buffer_size = int(min(remainingBuffer, math.floor(input_buffer_size * 2)))

        desired_output_size = max(buffer_size, minimum_buffer)
        if enforce_max and input_buffer_size + desired_output_size > total_max:
            print(f"Unable to calculate output token capacity - Overall Capacity ({total_max}) Exceeded (Optimized Size): Input={input_buffer_size}, Output={desired_output_size}")
            raise UnprocessableEntityError("Input is too large to process. Please try again with less input.")

        return ensure_max_output_token_limit(data, desired_output_size)

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
    def build_prompts_from_input(self, data, params, prompt_format_args, function_name) -> Tuple[List[Tuple[List[dict[str, any]], int]], int, int]:

        # allow the caller to override max_tokens, or just use default max for the chosen model
        max_tokens = data.get('max_tokens') if 'max_tokens' in data else self.get_default_max_tokens(data)
        # get the max input buffer for this function if we are tuning tokens
        if max_tokens != 0:
            input_token_buffer = self.calculate_input_token_buffer(max_tokens)
        # otherwise, just send it all to the OpenAI endpoint, and ignore limits
        else:
            input_token_buffer = 0

        truncated = 0

        # calculate the size of the function-related content for input buffer usage
        function_content_size = tokens_from_function(params, data.get('model'))

        model_max_tokens = self.get_default_max_tokens(data)

        # if single input, build the prompt to test length
        if 'chunks' not in prompt_format_args:
            this_messages = self.generate_messages(data, prompt_format_args)
            this_messages = self.optimize_content(this_messages, data)[0]

            input_tokens_count = sum(num_tokens_from_string(
                message["content"], data.get('model'))[0] for message in this_messages if 'content' in message)

            # reduce the input_token_buffer by the size of the function input content, since its fixed
            #   content that we can't reduce (even with chunking or other optimization)
            input_token_buffer -= function_content_size if input_token_buffer > 0 else 0

            if input_token_buffer == 0:
                tuned_input = input_tokens_count + function_content_size

                prompts_set = [(this_messages, int(0), tuned_input, function_content_size)]

            elif input_tokens_count < input_token_buffer:
                tuned_max_tokens = max_tokens - input_tokens_count - function_content_size
                tuned_output = self.calculate_output_token_buffer(
                    data, input_tokens_count + function_content_size, tuned_max_tokens, max_tokens, False)
                tuned_input = input_tokens_count + function_content_size

                if tuned_input + tuned_output > model_max_tokens:
                    print(f"Overall Analysis Buffer of {model_max_tokens} tokens exceeded for Single-Input: Input={tuned_input}, Output={tuned_output}, Function={function_content_size}")
                    raise UnprocessableEntityError("Input is too large to process. Please try again with less input.")
                else:
                    print(f"Overall Analysis Buffer of {model_max_tokens} used for Single-Input: Input={tuned_input}, Output={tuned_output}, Function={function_content_size}")

                prompts_set = [(this_messages, tuned_output, tuned_input, function_content_size)]

            else:  # this single input has blown the input buffer, so we'll need to chunk or truncate it

                # if the processor supports chunkable input, then we'll go that route
                if self.get_chunkable_input():
                    # If we are over the token limit, we're going to need to split it into chunks to process in parallel and then reassemble
                    # enough buffer to get a useful result - say 20% - 50% of the original input
                    prompts_set = self.chunk_input_based_on_token_limit(
                        data, prompt_format_args, input_token_buffer, function_content_size)[0]
                    # we'll ignore this truncation since we're chunking it anyway

                # otherwise, we'll just truncate the last user message
                else:
                    this_messages, truncated_tokens_count = self.truncate_user_messages(this_messages, input_token_buffer, data)

                    # emsure we include any function input content size before we calculate remaining output buffer
                    truncated_tokens_count += function_content_size

                    tuned_max_tokens = max_tokens - truncated_tokens_count
                    tuned_output = self.calculate_output_token_buffer(data, truncated_tokens_count, tuned_max_tokens, max_tokens, False)

                    input_tokens_count = sum(len(message["content"]) for message in this_messages if 'content' in message)

                    truncated += truncated_tokens_count
                    tuned_input = input_tokens_count + function_content_size

                    if tuned_input + tuned_output > model_max_tokens:
                        print(f"Overall Analysis Buffer of {model_max_tokens} tokens exceeded for Single-Input Truncated Processing: Input={tuned_input}, Output={tuned_output}, Function={function_content_size}")
                        raise UnprocessableEntityError("Input is too large to process. Please try again with less input.")
                    else:
                        print(f"Overall Analysis Buffer of {model_max_tokens} used for Single-Input Truncated Processing: Input={tuned_input}, Output={tuned_output}, Function={function_content_size}")

                    prompts_set = [(this_messages, tuned_output, tuned_input, function_content_size)]

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
                each_chunk_prompt_set = self.build_prompts_from_input(data, params, cloned_prompt_format_args, function_name)[0]

                # add the newly build prompt and max tokens into the list
                prompts_set.extend(each_chunk_prompt_set)

        user_message_size = 0
        background_message_size = 0
        for prompt, *_ in prompts_set:
            # get last message in prompt
            user_message_size += len(prompt[-1]["content"])

            # get all messages except the last one
            for message in prompt[0:-1]:
                background_message_size += len(message["content"])

        return prompts_set, user_message_size, background_message_size, truncated

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

        main_prompt = None  # we must have a user prompt - but we'll check again after message generation

        # Generate messages for all roles
        i = 0
        while i < len(self.prompts):

            prompt = self.prompts[i]
            next_prompt = self.prompts[i + 1] if i + 1 < len(self.prompts) else None

            i += 1  # Increment the prompt counter at the start of the loop to ensure progress each iteration.

            if prompt[0][0] == 'main':  # we handle 'main' last
                main_prompt = prompt[1]
                continue

            # context prompts are special - they are only included if the tags are present
            #   and they can replicate depending on number of context inputs
            if prompt[0][1].startswith('context-'):
                if any(tag not in prompt_format_args for tag in re.findall(r'\{(.+?)\}', prompt[1])):
                    print(f"Skipping {prompt[0][0]} prompt {prompt[0][1]} due to missing tags")
                    continue

            expandedList = 0
            # Check if this prompt text contains a '{tag}' that exists in our reformatting args
            for tag in re.findall(r'\{(.+?)\}', prompt[1]):
                if tag not in prompt_format_args:
                    continue

                if not isinstance(prompt_format_args.get(tag), list):
                    continue

                expandedList += 1
                role, content_list = prompt_format_args[tag]
                for content in content_list:

                    def expand_prompt_content(raw_prompt, prompt_format_args, role, content):
                        # inject each piece of custom content into the prompt
                        this_prompt_format_args = prompt_format_args.copy()

                        this_prompt_format_args[tag] = content
                        formatted_content = self.safe_format(raw_prompt, **this_prompt_format_args)

                        if str.isspace(formatted_content):
                            print(f"Skipping empty prompt for role {role}")
                            return

                        this_messages.append({
                            "role": role,
                            "content": formatted_content
                        })

                    # we're going to special case training prompt data, since these will be injected raw
                    #   without formatting or customization - these will be used to train the AI on good
                    #   answers
                    if role == 'user_assistant':
                        if 'prompt' not in content or 'response' not in content:
                            print(f"Skipping Training Data due to missing prompt or response in data: {content}")
                            continue

                        expand_prompt_content(prompt[1], prompt_format_args, "user", content['prompt'])
                        expand_prompt_content(next_prompt[1], prompt_format_args, "assistant", content['response'])

                    # otherwise, just expand this into one message
                    else:
                        expand_prompt_content(prompt[1], prompt_format_args, role, content)

                # if we have a training prompt, then we'll skip the next prompt since it's the response
                if role == 'user_assistant':
                    i += 1

                # finished with this prompt
                continue

            # if we already expanded and inserted the messages based on a list tag, then move on to next prompt
            if expandedList > 0:
                if expandedList > 1:
                    raise ValueError(f"Prompt {prompt[0][1]} has more than one expansion list tag - only one is supported currently")

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

        # At this point, all prompts should have been processed.
        if main_prompt is None:
            raise ValueError("Main (User) prompt is required but not found")

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

    def makeOpenAICall(self, function_name, attempt, timeBufferRemaining, params) -> dict:

        due_time = datetime.datetime.now() + datetime.timedelta(seconds=timeBufferRemaining)

        print(f"Thread-{threading.current_thread().ident}-{function_name}:Starting OpenAI {params.get('model', 'unknown')} API call attempt {attempt + 1},Time Allotted {mins_and_secs(timeBufferRemaining)}, Due By {due_time})")

        start_time = time.time()
        try:
            response = openai.ChatCompletion.create(**params, timeout=timeBufferRemaining, request_timeout=timeBufferRemaining)

            print(f"Thread-{threading.current_thread().ident}-{function_name}:SUCCESS:Finished OpenAI {params.get('model', 'unknown')} API call (Attempt {attempt + 1} in {mins_and_secs(time.time() - start_time)})")

            return response

        except Exception as e:
            print(f"Thread-{threading.current_thread().ident}-{function_name}:ERROR({str(e)}):Finished OpenAI {params.get('model', 'unknown')} API call (Attempt {attempt + 1} in {mins_and_secs(time.time() - start_time)})")
            raise

    def runAnalysis(self, params, account, function_name, correlation_id) -> dict:

        def log(message):
            print(f"Thread-{threading.current_thread().ident}-{function_name}:RunAnalysis:{message}")

        max_retries = 3
        start_time = time.time()

        # we're going to retry on intermittent network issues
        # e.g. throttling, connection issues, service down, etc..
        # Note that with RateLimit error, we could actually make it worse...
        #    So for rate limit we wait a lot longer to retry (e.g. 30-60 seconds)
        # https://platform.openai.com/docs/guides/error-codes/python-library-error-types
        for attempt in range(max_retries + 1):

            try:
                singlecall_timeout, allcalls_timeout, service_timeout = self.get_call_timeout_settings(None)

                now = time.time()
                time_buffer_remaining = round(service_timeout - (now - start_time), 2)

                if time_buffer_remaining < 0:
                    raise TimeoutError(f"Timeout exceeded for all Service calls: {mins_and_secs(service_timeout)}")

                openai_calltime_buffer_remaining = round(allcalls_timeout - (now - start_time), 2)
                if openai_calltime_buffer_remaining < 0:
                    raise TimeoutError(f"Timeout exceeded for total OpenAI calls: {mins_and_secs(allcalls_timeout)}")

                # we'll let the OpenAI call take at most the per-call max, or what's remaining
                #       of the total calls buffer
                allotted_time_buffer_for_this_openai_call = round(min(
                    openai_calltime_buffer_remaining,
                    singlecall_timeout), 2)

                log(f"Time Settings: "
                    f"TotalAnalysisTimeBuffer:{mins_and_secs(service_timeout)}, "
                    f"OverallTimeRemaining:{mins_and_secs(time_buffer_remaining)}, "
                    f"AllottedOpenAICallTime:{mins_and_secs(allotted_time_buffer_for_this_openai_call)}, "
                    f"OpenAICallTimeRemaining:{mins_and_secs(openai_calltime_buffer_remaining)}")

                response = self.makeOpenAICall(
                    function_name,
                    attempt,
                    allotted_time_buffer_for_this_openai_call,
                    params)

                if attempt > 0:
                    log(f"Succeeded after {attempt} retries")

                return dict(
                    message=response.choices[0].message,
                    response=response.choices[0].message.content,
                    finish=response.choices[0].finish_reason,
                    input_tokens=response.usage.prompt_tokens,
                    output_tokens=response.usage.completion_tokens)

            except (openai.error.Timeout, requests.exceptions.Timeout, TimeoutError) as e:
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

                log(f"RateLimitError, sleeping for {mins_and_secs(randomSleep)} before retry")

                # if we hit the rate limit, send a cloudwatch alert and raise the error
                capture_metric(
                    account['customer'], account['email'], function_name, correlation_id,
                    {"name": InfoMetrics.OPENAI_RATE_LIMIT, "value": 1, "unit": "None"})

                timeBufferRemaining = service_timeout - (time.time() - start_time)

                if timeBufferRemaining < 0:
                    raise Exception(f"Timeout exceeded for OpenAI call: {mins_and_secs(service_timeout)}")

                time.sleep(randomSleep)

            if attempt < max_retries and (time.time() - start_time + random.uniform(2, 5)) < service_timeout:

                timeBufferRemaining = service_timeout - (time.time() - start_time)

                if timeBufferRemaining < 0:
                    raise TimeoutError(f"Timeout exceeded for OpenAI call: {mins_and_secs(service_timeout)}")

                randomSleep = random.uniform(2, 5)
                log(f"OpenAPI:Retrying in {mins_and_secs(randomSleep)} after {error_type}: {error_msg}")
                time.sleep(randomSleep)
            else:
                log(f"FAILED after {attempt} retries:Error: {error_type}: {error_msg}")
                raise error

    def handleFinalCallError(self, e, input_tokens, log):
        return None

    def runAnalysisForPrompt(self, i, this_messages, max_output_tokens, input_tokens,
                             params_template, account, function_name, correlation_id) -> dict:
        params = params_template.copy()  # Create a copy of the template to avoid side effects

        if max_output_tokens != 0:
            params["max_tokens"] = int(max_output_tokens)

        params['messages'] = this_messages

        def log(message):
            print(f"Thread-{threading.current_thread().ident}-{function_name}:runAnalysisForPrompt:Chunk {i}:{message}")

        start_time = time.monotonic()

        log("Starting processing")

        result = None
        error = ""
        try:
            result = self.runAnalysis(params, account, function_name, correlation_id)

        except Exception as e:
            result = self.handleFinalCallError(e, input_tokens, log)
            if result is None:
                error = f"::error:{str(e)}"
                raise
            else:
                pass
        finally:
            end_time = time.monotonic()

            finish = 'Incomplete' if (result is None or result['finish'] is None or result['finish'] == 'length'
                                      or result['finish'] == 'content_filter') else 'Complete'

            if result is None:
                log(f"Error processing after {mins_and_secs(end_time - start_time)}:"
                    f"Finish:{finish}{error}")
            else:
                log(f"SUCCESS processing in {mins_and_secs(end_time - start_time)}:"
                    f"Finish:{finish}{error}")

        return result

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

        # get the JSON object out of the data payload
        context_json = data['context'] if 'context' in data else []
        context_names = ""
        context_data = ""
        for context in context_json:
            if 'data' not in context:
                print(f"Skipping context {context['name']} due to missing data")
                continue

            contextTag = f"context_{context['type']}"
            userFriendContextName = spacify(context['name'])
            contextInsertion = f"{userFriendContextName}:\n{context['data']}"
            # store contextual project summary data for use in prompts
            if context['type'] == AnalysisContextType.projectSummary:
                context_names = f"{context_names}, {context['name']}" if context_names != "" else f"{context['name']}"
                context_data = f"{context['data']}\n\n {context_data}" if context_data != "" else f"{context['data']}"

                prompt_format_args['summaries_type'] = context_names
                prompt_format_args['summaries_data'] = context_data

            # for related and historical data, we send mulitple messages for each entry to managed and truncated
            elif context['type'] in [AnalysisContextType.history, AnalysisContextType.related]:
                if contextTag not in prompt_format_args:
                    prompt_format_args[contextTag] = ['system', [contextInsertion]]
                else:
                    prompt_format_args[contextTag][1].append(contextInsertion)

            # for training data, we send mulitple messages for each entry to managed and truncated
            elif context['type'] in [AnalysisContextType.training]:
                # for training data, we will generate a user message and an assistant message (reply)
                #   so we send the entire data object along to be unpacked into multiple messages later
                if contextTag not in prompt_format_args:
                    prompt_format_args[contextTag] = ['user_assistant', [context['data']]]
                else:
                    prompt_format_args[contextTag][1].append(context['data'])

            # for user focus, we send one system prompt so analysis sees all user-focus in one message
            elif context['type'] == AnalysisContextType.userFocus:
                if 'context_userFocus' not in prompt_format_args:
                    prompt_format_args[contextTag] = ['system', [contextInsertion]]
                else:
                    prompt_format_args[contextTag] = ['system', [f"{prompt_format_args['context_userFocus'][1][0]}\n\n\n {contextInsertion}"]]

            else:
                print(f"Unsupported context type {context['type']} - discarding data for {context['name']}")

    def get_call_timeout_settings(self, data) -> Tuple[float, float, float]:
        return max_timeout_seconds_for_single_openai_call_default, max_timeout_seconds_for_all_openai_calls_default, total_analysis_time_buffer_default

    BillingMetrics = namedtuple('BillingMetrics', [
        'user_input_size',
        'output_size',
        'user_messages_size',
        'openai_input_cost',
        'openai_output_cost',
        'boost_cost',
        'openai_input_tokens',
        'openai_customerinput_tokens',
        'openai_output_tokens',
        'openai_tokens'
    ])

    def report_usage_cost(self,
                          account, function_name,
                          success,
                          billing_metrics: BillingMetrics):

        return update_usage_for_text(account, billing_metrics.user_messages_size + billing_metrics.output_size, function_name, success)

    def process_input(self, data, account, function_name, correlation_id, prompt_format_args) -> dict:

        # enable new throttler by default unless disabled in environment variable
        useNewThrottler = False if "useNewThrottler" in os.environ and os.environ["useNewThrottler"] == "False" else True

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

        prompt_set, user_messages_size, background_messages_size, truncated = self.build_prompts_from_input(data, params, prompt_format_args, function_name)
        chunked = len(prompt_set) > 1

        success = False
        try:
            results = None
            result = None

            total_incompletions = 0

            # if chunked, we're going to run all chunks in parallel and then concatenate the results at end
            if chunked:
                log(f"Chunked user input - {len(prompt_set)} chunks")

                if useNewThrottler:
                    single_ai_call_timeout, all_ai_calls_timeout, whole_service_call_timeout = self.get_call_timeout_settings(data)

                    throttler = Throttler(None,
                                          single_ai_call_timeout,
                                          all_ai_calls_timeout,
                                          whole_service_call_timeout)

                    # Sort prompt set based on total tokens (input tokens + output tokens)
                    sorted_prompt_set = sorted(prompt_set, key=lambda p: p[1] + p[2]) if OpenAIDefaults.boost_max_tokens_default != 0 else prompt_set

                    def runAnalysisForPromptThrottled(prompt_iteration):

                        index, prompt = prompt_iteration

                        messages = prompt[0]
                        output_tokens = prompt[1]
                        input_tokens = prompt[2]
                        function_tokens = prompt[3]

                        log(f"Chunk {index} (input={input_tokens},output={output_tokens},function={function_tokens},total={input_tokens+output_tokens})")

                        try:
                            if OpenAIDefaults.boost_max_tokens_default == 0:
                                # if we have no defined max, then no delay and no throttling - since tuning is disabled

                                log(f"Chunk {index} Processing has no delay since tuning is disabled")
                            else:
                                total_tokens = output_tokens + input_tokens

                                first_wait = time.time()
                                while True:
                                    delay = throttler.get_wait_time(total_tokens, first_wait, input_tokens)

                                    # if we need to delay, then wait for the specified delay or until notified
                                    if delay > 0:
                                        due_time = datetime.datetime.now() + datetime.timedelta(seconds=delay)
                                        log(f"Chunk {index} Processing of (input={input_tokens},output={output_tokens},function={function_tokens},total={input_tokens+output_tokens}) delaying for {mins_and_secs(delay)} until {due_time}")
                                        started_waiting = time.time()
                                        with throttler.lock:
                                            throttler.lock.wait(timeout=float(delay))  # Wait for the specified delay or until notified

                                        ultimate_delay = time.time() - started_waiting
                                        if ultimate_delay < delay:  # If started early
                                            log(f"Chunk {index} Processing starting early with delay of {mins_and_secs(ultimate_delay)} instead of expected delay of {mins_and_secs(delay)}", True)
                                        else:
                                            log(f"Chunk {index} Processing delayed for {mins_and_secs(ultimate_delay)}", True)

                                    # bypassing rate limiting due to overall wait time exceeded or other throttling failure
                                    elif delay < 0:
                                        log(f"Chunk {index} Processing of (input={input_tokens},output={output_tokens},function={function_tokens},total={input_tokens+output_tokens}) delaying for {mins_and_secs(delay)} due to throttling", True)

                                        break  # run the analysis immediately due to throttling failure or timeout

                                    # no delay due to priority (input, output, total)
                                    else:
                                        log(f"Chunk {index} Processing with No Delay (input={input_tokens},output={output_tokens},function={function_tokens},total={input_tokens+output_tokens})", True)

                                        break  # run analysis immediately as we've been unblocked by bucket availability

                            analysisResult = self.runAnalysisForPrompt(index, messages, output_tokens, input_tokens, params, account, function_name, correlation_id)

                        # need to ensure we re-fill in case of an error
                        finally:
                            # only refill if we used the throttler and didn't bypass rate limiting
                            if OpenAIDefaults.boost_max_tokens_default != 0 and delay >= 0:
                                # After each prompt completion, refill the bucket based on elapsed time
                                throttler.refill(output_tokens + input_tokens)

                        return analysisResult
                else:
                    sorted_prompt_set = prompt_set

                    totalChunks = len(prompt_set)
                    tokensPerChunk = OpenAIDefaults.rate_limit_tokens_per_minute / totalChunks

                    def runAnalysisForPromptThrottled(prompt_iteration):

                        index, prompt = prompt_iteration
                        model_max_tokens = self.get_default_max_tokens(data)
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

                        log(f"Chunk {index} delaying for {mins_and_secs(delay)}")

                        time.sleep(delay)  # Delay based on the number of words in the prompt

                        if delay > 5:  # If delay is more than 5 seconds, log it
                            log(f"Chunk {index} delayed for {mins_and_secs(delay)}", True)

                        return self.runAnalysisForPrompt(index, prompt[0], prompt[1], prompt[2], params, account, function_name, correlation_id)

                # launch all the parallel threads to run analysis with the unique chunked prompt for each
                # Throttling the rate of file processing
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    results = list(executor.map(runAnalysisForPromptThrottled, enumerate(sorted_prompt_set)))

            # otherwise, run once
            else:
                # if truncated user input, report it out, and update the OpenAI input with the truncated input
                if truncated:
                    log(f"Truncated user input, discarded {truncated} tokens")

                # run the analysis with single input
                singleIndex = 0
                results = [self.runAnalysisForPrompt(singleIndex, prompt_set[singleIndex][0], prompt_set[singleIndex][1],
                                                     prompt_set[singleIndex][2], params, account, function_name, correlation_id)]

                result = results[0]['response']

            def reassemble_function_results(results):
                incomplete_responses = []

                # from https://platform.openai.com/docs/guides/gpt/chat-completions-api
                def did_complete(r):
                    # Every response will include a finish_reason. The possible values for finish_reason are:

                    # stop: API returned complete message, or a message terminated by one of the stop sequences provided via the stop parameter
                    # length: Incomplete model output due to max_tokens parameter or token limit
                    # function_call: The model decided to call a function
                    # content_filter: Omitted content due to a flag from our content filters
                    # null: API response still in progress or incomplete
                    if 'finish' not in r:
                        return False
                    elif 'length' == r['finish']:
                        return False
                    elif 'stop' == r['finish']:
                        return True
                    elif 'function_call' == r['finish']:
                        return True
                    elif 'content_filter' == r['finish']:
                        return False
                    elif not r['finish']:
                        return False
                    else:  # anything unexpected and we'll assume its complete
                        log(f"Unexpected finish reason {r['finish']}")
                        return True

                incomplete_responses = [0 if did_complete(r) else 1 for r in results]

                # calculate only the count of incompletions, not the total length of the incomplete responses
                total_incompletions = sum(incomplete_responses)

                if 'function_call' not in results[0]['message']:
                    return False, None, sum(incomplete_responses), None

                # if every call failed, then just throw an error, as we have no useful results
                if len(results) == total_incompletions:
                    raise TimeoutError(f"{function_name} failed with incomplete or empty results - retry your call")

                items = []
                reassembled_results = []

                for index, r in enumerate(results):
                    if incomplete_responses[index] == 0:
                        json_items = json.loads(r['message']['function_call']['arguments'])
                        for key, value in json_items.items():
                            items.append({key: value})

                        # keep the result since its complete
                        reassembled_results.append(r)
                    else:
                        if 'function_call' in r['message'] and r['message']['function_call'] is not None:
                            incomplete_responses[index] = len(r['message']['function_call']['arguments']) if 'arguments' in r['message']['function_call'] else incomplete_responses[index]

                        log(f"Chunk {index} incomplete Function data - discarded {incomplete_responses[index]} discarded JSON bytes")

                        # if the function result is incomplete, its likely malformed JSON, so let's just throw
                        #       it away

                # re-calculate the total incompletions based on the data lengths of the incomplete function results
                total_incompletions = sum(incomplete_responses)

                if total_incompletions == 0:
                    return True, None, 0, None
                else:
                    # if we have incomplete responses, then return the reassembled results
                    return True, items, total_incompletions, reassembled_results

            isFunction, items, total_incompletions, reassembled_results = reassemble_function_results(results)

            if reassembled_results is not None:
                print(f"Due to some incomplete Function results, {len(results) - len(reassembled_results)} results were discarded")
                results = reassembled_results

            if isFunction:
                # this isn't a very useful representation, but it allows us to correctly calculate cost of the function call
                result = json.dumps(items)

            # otherwise, we need to update the result with the truncation warning to user
            else:
                if truncated:
                    truncation = markdown_emphasize(
                        f"Truncated input, discarded ~{truncated} symbols or words\n\n")

                    result = f"{truncation}{results[0]['response']}"

                # or if chunked, we're going to reassemble all the chunks
                elif chunked:
                    result = "\n\n".join([r['response'] for r in results])  # by concatenating all results into a single string

            if total_incompletions:
                # wild guess on how much was lost... if less than 100 characters/tokens - we don't really know the extent
                estimate_lost = f" - at least {total_incompletions}" if total_incompletions > 100 else ""
                some_incompletions = markdown_emphasize(
                    f"WARNING: While processing a large input, some of the analysis response may have been lost{estimate_lost} due to network or service timeouts. Please retry your analysis request or try analyzing a smaller piece of data.\n\n")
                result = f"{some_incompletions}{result}"

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

                openai_output_tokens, openai_output_cost = get_openai_usage_per_token(
                    sum([r['output_tokens'] for r in results]), False, data.get('model')) if results is not None else (0, 0)
                openai_tokens = openai_input_tokens + openai_output_tokens
                openai_cost = openai_input_cost + openai_output_cost

                billed_cost = 0.0

                boostAiCostMargin = 0.0

                # current Boost operating costs are only calculated based on OpenAI + AWS compute costs
                #   This is somewhat misleading - as we have storage of CloudWatch, logs, etc.
                #  But this is a reasonable fixed cost approximation for now
                #   as storage, logs, etc can all be groomed or reduced later

                aws_cost = get_current_lambda_cost(correlation_id)

                boost_cost = openai_cost + aws_cost

                # default in case of billing failure
                boost_lost_cost = boost_cost

                try:
                    billing_metrics = self.BillingMetrics(
                        user_input_size=user_input_size,
                        output_size=output_size,                # charged to billing
                        user_messages_size=user_messages_size,  # charged to billing
                        openai_input_cost=openai_input_cost,
                        openai_output_cost=openai_output_cost,
                        boost_cost=boost_cost,
                        openai_input_tokens=openai_input_tokens,
                        openai_customerinput_tokens=openai_customerinput_tokens,
                        openai_output_tokens=openai_output_tokens,
                        openai_tokens=openai_tokens
                    )

                    # update the billing usage for this analysis (charge for input + output)
                    #
                    # We only charge for at least some successful analysis
                    #
                    # note that currently, if there is a partially successful analysis, we still charge for the full user
                    #     message input, since we don't know how much of the user input was actually used
                    #
                    # Also, the original user input potentially includes a large amount of training and background data, and we
                    #   may truncate, chunk, or transform the user input further - we're going to charge based on the actual user
                    #   message content (and the final output)
                    # Note that this excludes background message data - usually training and system data - some of which is built from
                    #   user input. But this is a reasonable tradeoff, since the core of the user action is the actual user message
                    #
                    # This can all be overridden per processor
                    billed_cost = self.report_usage_cost(account, function_name,
                                                         (not account.get('saas_client', False)) and success,
                                                         billing_metrics)

                    if account.get('saas_client', False):
                        account['operation_expense'] = boost_cost

                    boostAiCostMargin = -100.0  # negative 100% margin means complete loss

                    if not success:
                        boost_lost_cost = total_incompletions + (billed_cost if billed_cost > 0 else boost_cost)

                    else:

                        # if we charged user, record the margin
                        if billed_cost > 0:
                            boostAiCostMargin = (billed_cost - boost_cost) / boost_cost * 100.0
                            boost_lost_cost = total_incompletions

                        # if we didn't charge user, record it as lost revenue, and negative margin
                        else:
                            boost_lost_cost = boost_cost + total_incompletions

                except Exception:
                    success = False
                    exception_info = traceback.format_exc().replace('\n', ' ')
                    log(f"UPDATE_USAGE_FAILURE:"
                        f"Error updating ~${boost_cost} usage: {exception_info}", False, True)
                    capture_metric(customer, email, function_name, correlation_id,
                                   {"name": InfoMetrics.BILLING_USAGE_FAILURE, "value": round(boost_lost_cost, 5), "unit": "None"})

                    pass  # Don't fail if we can't update usage / but that means we may have lost revenue

                capture_metric(customer, email, function_name, correlation_id,
                               {'name': CostMetrics.USER_MESSAGE_SIZE, 'value': user_messages_size, 'unit': 'Count'},
                               {'name': CostMetrics.BACKGROUND_MESSAGE_SIZE, 'value': background_messages_size, 'unit': 'Count'},
                               {'name': CostMetrics.RESPONSE_SIZE, 'value': output_size, 'unit': 'Count'},
                               {'name': CostMetrics.OPENAI_INPUT_COST, 'value': round(openai_input_cost, 5), 'unit': 'None'},
                               {'name': CostMetrics.OPENAI_CUSTOMERINPUT_COST, 'value': round(openai_customerinput_cost, 5), 'unit': 'None'},
                               {'name': CostMetrics.OPENAI_OUTPUT_COST, 'value': round(openai_output_cost, 5), 'unit': 'None'},
                               {'name': CostMetrics.OPENAI_COST, 'value': round(openai_cost, 5), 'unit': 'None'},
                               {'name': CostMetrics.AWS_COST, 'value': round(aws_cost, 5), 'unit': 'None'},
                               {'name': CostMetrics.BOOST_COST, 'value': round(boost_cost, 5), 'unit': 'None'},
                               {'name': CostMetrics.BOOST_AI_COST_MARGIN, 'value': round(boostAiCostMargin, 5), 'unit': 'None'},
                               {'name': CostMetrics.BOOST_CHARGED_USAGE, 'value': round(billed_cost, 5), 'unit': 'None'},
                               {'name': CostMetrics.LOST_BOOST_COST, 'value': round(boost_lost_cost, 5), 'unit': 'None'},
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
            "incompletions": total_incompletions,
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
