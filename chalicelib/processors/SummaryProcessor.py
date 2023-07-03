import math

from chalicelib.processors.GenericProcessor import GenericProcessor, key_ChunkedInputs, key_ChunkPrefix, key_IsChunked, key_NumberOfChunks
from chalicelib.version import API_VERSION
from chalicelib.usage import OpenAIDefaults
from chalice import BadRequestError


class SummarizeProcessor(GenericProcessor):
    def __init__(self):
        super().__init__(API_VERSION,
                         [['main', 'summarize.prompt'],
                          ['system', 'summarize-role-system.prompt']],
                         None,
                         {'model': OpenAIDefaults.boost_default_gpt_model,
                          'temperature': OpenAIDefaults.temperature_medium_with_explanation})

    def calculate_input_token_buffer(self, total_max) -> int:
        # we'll leave 90% of the buffer for the input, and 10% for the output
        return math.floor(total_max * 0.9)

    def build_example_summary(self) -> str:
        return ''

    def update_example_summary(self, current_example: str, new_example: str) -> str:
        if len(new_example) > len(current_example):
            return new_example
        else:
            return current_example

    def get_excluded_input_keys(self) -> list[str]:
        excludedKeys = super().get_excluded_input_keys()
        excludedKeys.append(['analysis_type', 'analysis_label', 'chunks', 'chunk_prefix', 'summary_example'])
        return excludedKeys

    def get_chunkable_input(self) -> str:
        return 'inputs'

    def summarize_inputs(self, data, account, function_name, correlation_id):
        analysis_type = data['analysis_type'] if 'analysis_type' in data else None
        if analysis_type is None:
            raise BadRequestError('Analysis type not provided')

        analysis_label = data['analysis_label'] if 'analysis_label' in data else None
        if analysis_label is None:
            raise BadRequestError('Analysis label not provided')

        # older clients will have one larger input
        if self.get_chunkable_input() in data:
            inputs = data[self.get_chunkable_input()]
        # newer clients will send each input in a separate chunk
        else:
            numChunks = data[key_NumberOfChunks] if key_NumberOfChunks in data else None
            if numChunks is None:
                raise BadRequestError('Number of chunks not provided')
            chunks = int(numChunks)

            chunk_prefix = data[key_ChunkPrefix] if key_ChunkPrefix in data else None
            if chunk_prefix is None:
                raise BadRequestError('Chunk prefix not provided')

            chunked_inputs = []
            inputs = None

            # we'll store the largest example (in length) as the example to follow in the summary
            # this is a rough heuristic for now, but the prompt should also shorten the final summary length
            example_summary = self.build_example_summary()

            # collect all the chunks into an array for parallel processing
            for i in range(0, chunks):
                thisChunk = data[chunk_prefix + str(i)] if chunk_prefix + str(i) in data else None
                if thisChunk is None:
                    raise BadRequestError(f'Chunk {i} not provided')

                chunked_inputs.append(thisChunk)

                example_summary = self.update_example_summary(example_summary, thisChunk)

            # disabling this code for now, as we want chunks to be processed on chunk boundaries, if possible
            # combine the entire set of inputs into a large input (which will be chunked by the model)
            # inputs = '\n\n'.join(chunked_inputs)

        print(f'SUMMARY:{correlation_id}:Processing {len(chunked_inputs) if inputs is None else 1} {analysis_type} inputs')

        try:
            result = self.process_input(data, account, function_name, correlation_id,
                                        {
                                            self.get_chunkable_input(): inputs if inputs is not None else None,
                                            'analysis_type': analysis_type,
                                            'analysis_label': analysis_label,

                                            **({key_NumberOfChunks: chunks,
                                                key_ChunkPrefix: chunk_prefix,
                                                'summary_example': example_summary,
                                                key_ChunkedInputs: chunked_inputs
                                                } if inputs is None else {})
                                        })
        except Exception as e:
            print(f'SUMMARY:{correlation_id}:Error processing {len(chunked_inputs) if inputs is None else 1} {analysis_type} inputs')
            raise e
        finally:
            print(f'SUMMARY:{correlation_id}:Completed processing {len(chunked_inputs) if inputs is None else 1} {analysis_type} inputs')

        return {"analysis": result['output'],
                "truncated": result['truncated'],
                key_IsChunked: result[key_IsChunked],
                "analysis_type": analysis_type,
                "analysis_label": analysis_label}
