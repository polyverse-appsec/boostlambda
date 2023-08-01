from chalicelib.processors.GenericProcessor import GenericProcessor, AnalysisOutputFormat
from chalicelib.version import API_VERSION
import re
from chalicelib.usage import OpenAIDefaults
from chalice import BadRequestError
import math


class FlowDiagramProcessor(GenericProcessor):
    def __init__(self):
        super().__init__(API_VERSION, [
            ['main', 'flowdiagram.prompt'],
            ['system', 'flowdiagram-role-system.prompt']],
            None,
            {'model': OpenAIDefaults.boost_model_gpt35_cheap_chat,
             'temperature': OpenAIDefaults.temperature_terse_and_accurate},
            AnalysisOutputFormat.prose)

    def get_chunkable_input(self) -> str:
        return 'code'

    def calculate_input_token_buffer(self, total_max) -> int:
        # we'll leave 90% of the buffer for the input, and 10% for the output, since the function call outputs are small
        # and we're much terser in output in this processor
        return math.floor(total_max * 0.9)

    def flowdiagram_code(self, data, account, function_name, correlation_id):
        code = data[self.get_chunkable_input()] if self.get_chunkable_input() in data else None
        if code is None:
            raise BadRequestError("Error: please provide the original code")

        result = self.process_input(data, account, function_name, correlation_id, {self.get_chunkable_input(): code})
        cleanedResult = sanitize_mermaid_code(result['output'])

        return {
            "analysis": cleanedResult,
            "truncated": result['truncated'],
            "chunked": result['chunked'],
        }


def sanitize_mermaid_code(markdownCode):
    # only clean mermaid code
    regex = r"```([\s\S]*?)```"

    # clean out inner brackets - replaced with spaces
    # due to regex limitation with variable width lookbehind, we will perform the transform outside of the tick marks
    cleanedMarkdown = markdownCode
    lastCleanedMarkdown = markdownCode
    cleanedMarkdown = re.sub(r'\[([^\[\]]*\[[^\[\]]*\][^\[\]]*)\]',
                             lambda match: '[ ' + match.group(1).replace('[', '').replace(']', '') + ' ]',
                             cleanedMarkdown, flags=re.DOTALL)
    if (cleanedMarkdown != lastCleanedMarkdown):
        print("CLEANED: Replaced inner brackets with spaces")
        lastCleanedMarkdown = cleanedMarkdown

    # replace escaped quotes with leading space with square brackets
    cleanedMarkdown = re.sub(regex,
                             lambda match: "```" + re.sub(r" \\\"(.*)\\\"", "[\1]",
                                                          match.group(1)) + "```", cleanedMarkdown, flags=re.DOTALL)
    if (cleanedMarkdown != lastCleanedMarkdown):
        print("CLEANED: Replaced escaped quotes with leading space with square brackets")
        lastCleanedMarkdown = cleanedMarkdown

    # replace escaped quotes without leading space with spaces
    cleanedMarkdown = re.sub(regex,
                             lambda match: "```" + re.sub(r"\\\"(.*)\\\"", " \1 ",
                                                          match.group(1)) + "```", cleanedMarkdown, flags=re.DOTALL)
    if (cleanedMarkdown != lastCleanedMarkdown):
        print("CLEANED: Replaced escaped quotes without leading space with spaces")
        lastCleanedMarkdown = cleanedMarkdown

    # replace unescaped quotes with nothing
    cleanedMarkdown = re.sub(regex,
                             lambda match: "```" + re.sub(r" \"(.*)\"", " \1",
                                                          match.group(1)) + "```", cleanedMarkdown, flags=re.DOTALL)
    if (cleanedMarkdown != lastCleanedMarkdown):
        print("CLEANED: Replace unescaped quotes with nothing")
        lastCleanedMarkdown = cleanedMarkdown

    # replace unescaped unicode \u0001 with nothing
    cleanedMarkdown = re.sub(regex,
                             lambda match: "```" + re.sub(u'\u0001', '',
                                                          match.group(1)) + "```", cleanedMarkdown, flags=re.DOTALL)
    if (cleanedMarkdown != lastCleanedMarkdown):
        print("CLEANED: Replace unescaped unicode \\u0001 with nothing")
        lastCleanedMarkdown = cleanedMarkdown

    # clean out parentheses, replaced with spaces
    cleanedMarkdown = re.sub(regex,
                             lambda match: "```" + re.sub(r"\((.*)\)", " \1 ",
                                                          match.group(1)) + "```", cleanedMarkdown, flags=re.DOTALL)
    if (cleanedMarkdown != lastCleanedMarkdown):
        print("CLEANED: Replaced parentheses with spaces")
        lastCleanedMarkdown = cleanedMarkdown

    # replace end with ends - end is a reserved word in mermaid, or at least the mermaid renderer will fail
    cleanedMarkdown = re.sub(regex,
                             lambda match: "```" + re.sub(r'(?<=[^\s\w]|_)end(?=[^\s\w]|_|$)', 'ends',
                                                          match.group(1)) + "```", cleanedMarkdown, flags=re.DOTALL)
    if (cleanedMarkdown != lastCleanedMarkdown):
        print("CLEANED: Replace end with ends - end is a reserved word in mermaid")
        lastCleanedMarkdown = cleanedMarkdown

    # repair broken colors, due to openai generation issues - e.g. color codes like #fff are broken when missing the #
    cleanedMarkdown = re.sub(regex,
                             lambda match: "```" + re.sub(r'(fill:|stroke:)(\w)', r'\1#\2',
                                                          match.group(1)) + "```", cleanedMarkdown, flags=re.DOTALL)
    if (cleanedMarkdown != lastCleanedMarkdown):
        print("CLEANED: Repair broken colors, due to openai generation issues - e.g. color codes like #fff are broken when missing the #")
        lastCleanedMarkdown = cleanedMarkdown

    # repair broken equality, due to openai generation issues - e.g. === will not parse, but == will
    cleanedMarkdown = re.sub(regex,
                             lambda match: "```" + re.sub(r'===', r'==',
                                                          match.group(1)) + "```", cleanedMarkdown, flags=re.DOTALL)
    if (cleanedMarkdown != lastCleanedMarkdown):
        print("CLEANED: Repair broken equality, due to openai generation issues - e.g. === will not parse, but == will")
        lastCleanedMarkdown = cleanedMarkdown

    # if we changed the output from the original, print the original version for debugging errant changes
    if cleanedMarkdown != markdownCode:
        print("ORIGINAL Mermaid code:\n")
        print(markdownCode)
        print("\n\n\n")
        print("CLEANED Mermaid code:\n")
        print(cleanedMarkdown)

    return cleanedMarkdown
