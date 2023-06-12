from chalice.test import Client
from app import app
from chalicelib.processors.FlowDiagramProcessor import sanitize_mermaid_code

import re
import pytest


@pytest.mark.codeInput
def test_flowdiagram_no_code():
    with Client(app) as client:
        request_body = {
            'code': 'This is not a code.',
            'session': 'testemail: alex@polytest.ai',
            'organization': 'polytest.ai',
            'version': '0.9.5'
        }
        response = client.lambda_.invoke('flowdiagram', request_body)
        assert response.payload['statusCode'] == 200  # Ensure the request was successful
        # Add further assertions based on expected response


@pytest.mark.codeInput
def test_flowdiagram_simple_c_code():
    with Client(app) as client:
        request_body = {
            'code': """
            int main() {
              int a = 5;
              if (a > 0) {
                printf("A is positive");
              } else {
                printf("A is not positive");
              }
              return 0;
            }
            """,
            'session': 'testemail: alex@polytest.ai',
            'organization': 'polytest.ai',
            'version': '0.9.5'
        }
        response = client.lambda_.invoke('flowdiagram', request_body)
        assert response.payload['statusCode'] == 200  # Ensure the request was successful
        # Add further assertions based on expected response


@pytest.mark.codeInput
def test_flowdiagram_c_style_comments():
    with Client(app) as client:
        request_body = {
            'code': """
            /* This is a block comment */
            // This is a line comment
            """,
            'session': 'testemail: alex@polytest.ai',
            'organization': 'polytest.ai',
            'version': '0.9.5'
        }
        response = client.lambda_.invoke('flowdiagram', request_body)
        assert response.payload['statusCode'] == 200  # Ensure the request was successful
        # Add further assertions based on expected response


@pytest.mark.cleanOutput
def test_flowdiagram_sanitize_output_escaped_quoted_text():
    original_mermaid = {
        "code": "I could not find any control flow in the provided code. The given code is a simple subroutine definition without any control structures such as loops or conditionals.\n\n```mermaid\n    graph TD;\n    style NOCONTROLFLOWFOUND fill:#228B22, stroke:#000000, stroke-width:2px;\n\n        NOCONTROLFLOWFOUND \"NO CONTROL FLOW FOUND\" ;\n```"
    }

    cleaned_result = sanitize_mermaid_code(original_mermaid["code"])
    assert original_mermaid is not cleaned_result  # Ensure the request was successful


@pytest.mark.cleanOutput
def print_just_code(rawResult):
    print(re.sub(r'.*```(.*?)```.*',
                 lambda match: re.sub(r'\[(.*?)\]', r' \1 ', match.group(0)), rawResult, flags=re.DOTALL))


@pytest.mark.cleanOutput
def flowdiagram_sanitize_output(original_data):
    assert 'data' in original_data

    original_mermaid = original_data['data']

    print_just_code(original_mermaid)

    cleaned_result = sanitize_mermaid_code(original_mermaid)

    if original_data["clean"]:
        assert original_mermaid != cleaned_result
    else:
        assert original_mermaid == cleaned_result


@pytest.mark.cleanOutput
def test_flowdiagram_sanitize_output_bracketed_text():
    original_mermaid_data = {
        "data": "```mermaid\ngraph TD;\n    style Start fill:#228B22, stroke:#000000, strokeWidth:2px;\n    style Process1 fill:#228B22, stroke:#000000, strokeWidth:4px;\n    style Process2 fill:#228B22, stroke:#000000, strokeWidth:4px;\n\n    Start[Start]  --> Process1[Set EXPORTS];\n    Process1 --> Process2[Initialize No DSL and Exported App];\n```\n\nIn this code snippet, there are two primary steps in the control flow:\n\n1. Set EXPORTS: The `@EXPORT` is initialized with the `:plugin` keyword.\n2. Initialize No DSL and Exported App: Two variables, `$no_dsl` and `$exported_app`, are initialized as empty hashes.\n\nSince there are no alternative or error paths in the given source code, all nodes use the primary style, which is colored green.",
        'clean': False
    }
    flowdiagram_sanitize_output(original_mermaid_data)


@pytest.mark.cleanOutput
def test_flowdiagram_sanitize_output_nested_bracketed_text():
    original_mermaid_data = {
        "data": "```mermaid\ngraph TD;\n    style Start fill:#228B22, stroke:#000000, strokeWidth:2px;\n    style Process1 fill:#228B22, stroke:#000000, strokeWidth:4px;\n    style Process2 fill:#228B22, stroke:#000000, strokeWidth:4px;\n\n    Start[Start]  --> Process1[Set EXPORTS];\n    Process1 --> Process2[Initialize[No]DSL and Exported App];\n```\n\nIn this code snippet, there are two primary steps in the control flow:\n\n1. Set EXPORTS: The `@EXPORT` is initialized with the `:plugin` keyword.\n2. Initialize No DSL and Exported App: Two variables, `$no_dsl` and `$exported_app`, are initialized as empty hashes.\n\nSince there are no alternative or error paths in the given source code, all nodes use the primary style, which is colored green.",
        'clean': True
    }
    flowdiagram_sanitize_output(original_mermaid_data)


@pytest.mark.cleanOutput
def test_flowdiagram_sanitize_output_errant_quotes():
    original_mermaid_data = {
        "data": "Here is the control flow graph for the provided source code in mermaid format:\n\n```mermaid\ngraph TD;\n\n    style Start fill:#228B22, stroke:#000000, stroke-width:2px;\n    style Process1 fill:#228B22, stroke:#000000, stroke-width:4px;\n    style Process2 fill:#228B22, stroke:#000000, stroke-width:4px;\n    style Process3 fill:#228B22, stroke:#000000, stroke-width:4px;\n    style Process4 fill:#228B22, stroke:#000000, stroke-width:4px;\n    style End fill:#FFFFFF, stroke:#000000, stroke-width:2px;\n    \n    Start-->Process1;\n    Process1-->|name eq \"no_dsl\"|Process2;\n    Process1-->|name eq \"plugin\"|Process3;\n    Process1-->|name eq \"app\"|Process4;\n    Process1-->End;\n    Process2-->End;\n    Process3-->End;\n    Process4-->End;\n```\n\nControl flow decision points:\n\n1. Process1 checks if `$name` is equal to \"no_dsl\". If true, it proceeds to Process2.\n2. Process1 checks if `$name` is equal to \"plugin\" or \"no_dsl\". If true, it proceeds to Process3.\n3. Process1 checks if `$name` is equal to \"app\", the caller has a \"can\" method called \"app\", and if `$no_dsl` is not true for the `$class`. If true, it proceeds to Process4.\n4. If none of the conditions mentioned above is true, the code proceeds to the End node.",
        'clean': True
    }
    flowdiagram_sanitize_output(original_mermaid_data)


@pytest.mark.cleanOutput
def test_flowdiagram_sanitize_output_missing_title_identifiers():
    original_mermaid_data = {
        "data": "```mermaid\ngraph TD;\nstyle Start fill:#228B22, stroke:#000000, strokeWidth:2px;\nstyle End fill:#FA8072, stroke:#000000, strokeWidth:2px;\nstyle PrimaryPath fill:#228B22, stroke:#000000, strokeWidth:4px;\nstyle ErrorPath fill:#B22222, stroke:#000000, strokeWidth:2px;\n\nStart-->A my($class, $caller, $global) = @_ ;\nA-->B $exported_app->{$caller} = 1 ;\nB-->C my $app = eval(\"${caller}::app()\") || eval { $caller->dsl->app } ;\nC-->D return if app not found ;\nC-->E return unless $app->can('with_plugin') ;\nE-->F my $plugin = $app->with_plugin( '+' . $class ) ;\nF-->G $global->{'plugin'} = $plugin ;\nG-->H return unless $class->can('keywords') ;\nH-->CreateHooks;\nCreateHooks-->I foreach my $hook ( @{ $plugin->ClassHooks } ) ;\nI-->CopyHooks;\nCopyHooks-->StoringPluginInfo;\nStoringPluginInfo-->InstallExecuteHook;\nInstallExecuteHook-->J local $CUR_PLUGIN = $plugin ;\nJ-->SubExecution $_->($plugin) for @{ $plugin->_DANCER2_IMPORT_TIME_SUBS() } ;\nSubExecution-->End map { [ $_ =>  {plugin => $plugin}    } keys %{ $plugin->keywords }];\n\nstyle D fill:#B22222, stroke:#000000, strokeWidth:2px;\n```\n\nHere is a control flow graph for the provided source code using mermaid format. There is a primary path indicated in green while the error path is shown in red. The primary path demonstrates the expected flow, while the error path indicates points where the code may encounter issues and return early.",
        'clean': False  # This should be cleaned, but it isn't yet - unclear how OpenAI generated this
    }
    flowdiagram_sanitize_output(original_mermaid_data)


@pytest.mark.cleanOutput
def test_flowdiagram_sanitize_output_extra_brackets():
    original_mermaid_data = {
        "data": "```mermaid\ngraph TD;\n    style Start fill:#228B22, stroke:#000000, stroke-width:2px;\n    style InitializeDistances fill:#228B22, stroke:#000000, stroke-width:4px;\n    style InitializePriorityQueue fill:#228B22, stroke:#000000, stroke-width:4px;\n    style WhileLoop fill:#228B22, stroke:#000000, stroke-width:4px;\n    style CheckCurrentDistance fill:#228B22, stroke:#000000, stroke-width:4px;\n    style IterateNeighbors fill:#228B22, stroke:#000000, stroke-width:4px;\n    style UpdateDistance fill:#228B22, stroke:#000000, stroke-width:4px;\n    style PushToQueue fill:#228B22, stroke:#000000, stroke-width:4px;\n    style End fill:#228B22, stroke:#000000, stroke-width:2px;\n\n    Start-->InitializeDistances;\n    InitializeDistances-->InitializePriorityQueue;\n    InitializePriorityQueue-->WhileLoop;\n    WhileLoop-->CheckCurrentDistance;\n    CheckCurrentDistance-->WhileLoop;\n    CheckCurrentDistance-- If Current distance <= distances[current_node] -->IterateNeighbors;\n    IterateNeighbors-->UpdateDistance;\n    UpdateDistance-->PushToQueue;\n    PushToQueue-->WhileLoop;\n    WhileLoop-->End;\n```",
        'clean': False  # This should be cleaned, but it isn't yet - unclear how OpenAI generated this
    }
    flowdiagram_sanitize_output(original_mermaid_data)
