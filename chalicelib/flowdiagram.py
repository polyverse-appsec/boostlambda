from chalicelib.genericprocessor import GenericProcessor
from chalicelib.version import API_VERSION
import re


class FlowDiagramProcessor(GenericProcessor):
    def __init__(self):
        super().__init__(API_VERSION, {
            'main': 'flowdiagram.prompt',
            'role_system': 'flowdiagram-role-system.prompt'
        })

    def flowdiagram_code(self, code, account, context, correlation_id):
        result = self.process_code(code, account, context, correlation_id, {'code': code})
        result = self.sanitize_mermaid_code(result)
        return result

    def sanitize_mermaid_code(self, markdownCode):
        # only clean mermaid code
        regex = r"```([\s\S]*?)```"

        cleanedMarkdown = markdownCode

        # clean out special characters
        cleanedMarkdown = re.sub(regex,
                                 lambda match: "```" + re.sub(r"[^\w\s=>,\[\]\(\)\{\}\+\-\*\/\|:\.]", "",
                                                              match.group(1)) + "```", cleanedMarkdown, flags=re.DOTALL)

        # replace end with ends - end is a reserved word in mermaid, or at least the mermaid renderer will fail
        cleanedMarkdown = re.sub(regex,
                                 lambda match: "```" + re.sub(r'(?<=[^\s\w]|_)end(?=[^\s\w]|_|$)', 'ends',
                                                              match.group(1)) + "```", cleanedMarkdown, flags=re.DOTALL)

        # repair broken colors, due to openai generation issues - e.g. color codes like #fff are broken when missing the #
        cleanedMarkdown = re.sub(regex,
                                 lambda match: "```" + re.sub(r'(fill:|stroke:)(\w)', r'\1#\2',
                                                              match.group(1)) + "```", cleanedMarkdown, flags=re.DOTALL)

        return cleanedMarkdown
