from chalicelib.genericprocessor import GenericProcessor
from chalicelib.version import API_VERSION
import re


class FlowDiagramProcessor(GenericProcessor):
    def __init__(self):
        super().__init__(API_VERSION, {
            'main': 'flowdiagram.prompt',
            'role_system': 'flowdiagram-role-system.prompt'
        })

    def flowdiagram_code(self, data, account, function_name, correlation_id):
        result = self.process_input(data, account, function_name, correlation_id, {'code': data})
        cleanedResult = sanitize_mermaid_code(result)

        return {"analysis": cleanedResult}


def sanitize_mermaid_code(markdownCode):
    # only clean mermaid code
    regex = r"```([\s\S]*?)```"

    # clean out inner brackets - replaced with spaces
    # due to regex limitation with variable width lookbehind, we will perform the transform outside of the tick marks
    cleanedMarkdown = markdownCode
    cleanedMarkdown = re.sub(r'\[([^\[\]]*\[[^\[\]]*\][^\[\]]*)\]',
                             lambda match: '[ ' + match.group(1).replace('[', '').replace(']', '') + ' ]',
                             cleanedMarkdown, flags=re.DOTALL)

    # replace escaped quotes with leading space with square brackets
    cleanedMarkdown = re.sub(regex,
                             lambda match: "```" + re.sub(r" \\\"(.*)\\\"", "[\1]",
                                                          match.group(1)) + "```", cleanedMarkdown, flags=re.DOTALL)

    # replace escaped quotes without leading space with spaces
    cleanedMarkdown = re.sub(regex,
                             lambda match: "```" + re.sub(r"\\\"(.*)\\\"", " \1 ",
                                                          match.group(1)) + "```", cleanedMarkdown, flags=re.DOTALL)

    # replace unescaped quotes with nothing
    cleanedMarkdown = re.sub(regex,
                             lambda match: "```" + re.sub(r" \"(.*)\"", " \1",
                                                          match.group(1)) + "```", cleanedMarkdown, flags=re.DOTALL)

    # clean out parantheses, replaced with spaces
    cleanedMarkdown = re.sub(regex,
                             lambda match: "```" + re.sub(r"\((.*)\)]", " \1 ",
                                                          match.group(1)) + "```", cleanedMarkdown, flags=re.DOTALL)

    # replace end with ends - end is a reserved word in mermaid, or at least the mermaid renderer will fail
    cleanedMarkdown = re.sub(regex,
                             lambda match: "```" + re.sub(r'(?<=[^\s\w]|_)end(?=[^\s\w]|_|$)', 'ends',
                                                          match.group(1)) + "```", cleanedMarkdown, flags=re.DOTALL)

    # repair broken colors, due to openai generation issues - e.g. color codes like #fff are broken when missing the #
    cleanedMarkdown = re.sub(regex,
                             lambda match: "```" + re.sub(r'(fill:|stroke:)(\w)', r'\1#\2',
                                                          match.group(1)) + "```", cleanedMarkdown, flags=re.DOTALL)

    # repair broken equality, due to openai generation issues - e.g. === will not parse, but == will
    cleanedMarkdown = re.sub(regex,
                             lambda match: "```" + re.sub(r'===', r'==',
                                                          match.group(1)) + "```", cleanedMarkdown, flags=re.DOTALL)

    # if we changed the output from the original, print the original version for debugging errant changes
    if cleanedMarkdown != markdownCode:
        print("CLEANED Mermaid code:\n")
        print(markdownCode)

    return cleanedMarkdown
