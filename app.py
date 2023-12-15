from chalice import Chalice

from chalicelib.telemetry import xray_recorder
from chalicelib.app_utils import process_request

from chalicelib.customer_portal import customer_portal_handler
from chalicelib.user_organizations import user_organizations_handler

from chalicelib.processors.FlowDiagramProcessor import FlowDiagramProcessor
from chalicelib.processors.SummaryProcessor import SummarizeProcessor
from chalicelib.processors.CodeSummarizerProcessor import CodeSummarizerProcessor
from chalicelib.processors.ExplainProcessor import ExplainProcessor
from chalicelib.processors.CustomProcessor import CustomProcessor
from chalicelib.processors.GenerateProcessor import GenerateProcessor
from chalicelib.processors.ConvertCodeFunctionProcessor import ConvertCodeFunctionProcessor
from chalicelib.processors.TestGeneratorProcessor import TestGeneratorProcessor
from chalicelib.processors.TestGeneratorFunctionProcessor import TestGeneratorFunctionProcessor
from chalicelib.processors.AnalyzeProcessor import AnalyzeProcessor
from chalicelib.processors.ComplianceProcessor import ComplianceProcessor
from chalicelib.processors.CodingGuidelinesProcessor import CodingGuidelinesProcessor
from chalicelib.processors.BlueprintProcessor import BlueprintProcessor
from chalicelib.processors.SecurityFunctionProcessor import SecurityFunctionProcessor
from chalicelib.processors.ComplianceFunctionProcessor import ComplianceFunctionProcessor
from chalicelib.processors.CompareCodeProcessor import CompareCodeProcessor
from chalicelib.processors.PerformanceProcessor import PerformanceProcessor
from chalicelib.processors.PerformanceFunctionProcessor import PerformanceFunctionProcessor
from chalicelib.processors.QuickBlueprintProcessor import QuickBlueprintProcessor
from chalicelib.processors.DraftBlueprintFunctionProcessor import DraftBlueprintFunctionProcessor
from chalicelib.processors.QuickSummaryProcessor import QuickSummaryProcessor
from chalicelib.processors.CustomScanFunctionProcessor import CustomScanFunctionProcessor
from chalicelib.processors.ChatProcessor import ChatProcessor
from chalicelib.processors.ChatDriver_FunctionProcessor import ChatDriverFunctionProcessor
from chalicelib.processors.UIDriver_FunctionProcessor import UIDriverFunctionProcessor


app = Chalice(app_name='boost')

# For future logging purposes, we can use the following:
# https://aws.github.io/chalice/topics/logging.html
# Default logging level is logging.ERROR
# app.log.setLevel(logging.DEBUG)
# app.log.debug("This is a debug statement")
# app.log.error("This is an error statement")


@app.lambda_function(name='flowdiagram')
def flowdiagram(event, _):
    flowDiagramProcessor = FlowDiagramProcessor()
    return process_request(event, flowDiagramProcessor.flowdiagram_code, flowDiagramProcessor.api_version)


@app.lambda_function(name='summarize')
def summarize(event, _):
    summarizeProcessor = SummarizeProcessor()
    return process_request(event, summarizeProcessor.summarize_inputs, summarizeProcessor.api_version)


@app.lambda_function(name='codesummarizer')
def codesummarizer(event, _):
    codeSummarizerProcessor = CodeSummarizerProcessor()
    return process_request(event, codeSummarizerProcessor.summarize_code, codeSummarizerProcessor.api_version)


@app.lambda_function(name='explain')
def explain(event, _):
    explainProcessor = ExplainProcessor()
    return process_request(event, explainProcessor.explain_code, explainProcessor.api_version)


@app.lambda_function(name='generate')
def generate(event, _):
    generateProcessor = GenerateProcessor()
    return process_request(event, generateProcessor.convert_code, generateProcessor.api_version)


@app.lambda_function(name='convert_code')
def convert_code(event, context):
    convertCodeFunctionProcessor = ConvertCodeFunctionProcessor()
    return process_request(event, convertCodeFunctionProcessor.convert_code, convertCodeFunctionProcessor.api_version)


@app.lambda_function(name='compare_code')
def compare_code(event, _):
    compareCodeProcessor = CompareCodeProcessor()
    return process_request(event, compareCodeProcessor.compare_code, compareCodeProcessor.api_version)


@app.lambda_function(name='testgen')
def testgen(event, _):
    testGeneratorProcessor = TestGeneratorProcessor()
    return process_request(event, testGeneratorProcessor.testgen_code, testGeneratorProcessor.api_version)


@app.lambda_function(name='generate_tests')
def generate_tests(event, _):
    testGeneratorFunctionProcessor = TestGeneratorFunctionProcessor()
    return process_request(event, testGeneratorFunctionProcessor.generate_tests, testGeneratorFunctionProcessor.api_version)


@app.lambda_function(name='analyze')
def analyze(event, _):
    analyzeProcessor = AnalyzeProcessor()
    return process_request(event, analyzeProcessor.analyze_code, analyzeProcessor.api_version)


@app.lambda_function(name='analyze_function')
def analyze_function(event, _):
    securityFunctionProcessor = SecurityFunctionProcessor()
    return process_request(event, securityFunctionProcessor.secure_code, securityFunctionProcessor.api_version)


@app.lambda_function(name='compliance')
def compliance(event, context):
    complianceProcessor = ComplianceProcessor()
    return process_request(event, complianceProcessor.compliance_code, complianceProcessor.api_version)


@app.lambda_function(name='compliance_function')
def compliance_function(event, _):
    complianceFunctionProcessor = ComplianceFunctionProcessor()
    return process_request(event, complianceFunctionProcessor.check_compliance, complianceFunctionProcessor.api_version)


@app.lambda_function(name='codeguidelines')
def codeguidelines(event, context):
    codeguidelinesProcessor = CodingGuidelinesProcessor()
    return process_request(event, codeguidelinesProcessor.checkguidelines_code, codeguidelinesProcessor.api_version)


@app.lambda_function(name='performance')
def performance(event, context):
    performanceProcessor = PerformanceProcessor()
    return process_request(event, performanceProcessor.check_performance, performanceProcessor.api_version)


@app.lambda_function(name='performance_function')
def performance_function(event, context):
    performanceFunctionProcessor = PerformanceFunctionProcessor()
    return process_request(event, performanceFunctionProcessor.check_performance, performanceFunctionProcessor.api_version)


@app.lambda_function(name='customscan_function')
def customscan_function(event, context):
    customScanFunctionProcessor = CustomScanFunctionProcessor()
    return process_request(event, customScanFunctionProcessor.custom_scan, customScanFunctionProcessor.api_version)


@app.lambda_function(name='blueprint')
def blueprint(event, context):
    blueprintProcessor = BlueprintProcessor()
    return process_request(event, blueprintProcessor.blueprint_code, blueprintProcessor.api_version)


@app.lambda_function(name='quick-blueprint')
def quick_blueprint(event, context):
    quickBlueprintProcessor = QuickBlueprintProcessor()
    return process_request(event, quickBlueprintProcessor.quick_blueprint, quickBlueprintProcessor.api_version)


@app.lambda_function(name='quick-summary')
def quick_summary(event, context):
    quickSummaryProcessor = QuickSummaryProcessor()
    return process_request(event, quickSummaryProcessor.quick_summary, quickSummaryProcessor.api_version)


@app.lambda_function(name='draft-blueprint')
def draft_blueprint(event, context):
    draftBlueprintFunctionProcessor = DraftBlueprintFunctionProcessor()
    return process_request(event, draftBlueprintFunctionProcessor.draft_blueprint, draftBlueprintFunctionProcessor.api_version)


@app.lambda_function(name='chat')
def chat(event, _):
    chatProcessor = ChatProcessor()
    return process_request(event, chatProcessor.process_chat, chatProcessor.api_version)


@app.lambda_function(name='chat_driver')
def chat_driver(event, _):
    chatDriverFunctionProcessor = ChatDriverFunctionProcessor()
    return process_request(event, chatDriverFunctionProcessor.chat_driver, chatDriverFunctionProcessor.api_version)


@app.lambda_function(name='ui_driver')
def ui_driver(event, _):
    uiDriverFunctionProcessor = UIDriverFunctionProcessor()
    return process_request(event, uiDriverFunctionProcessor.ui_driver, uiDriverFunctionProcessor.api_version)


@app.lambda_function(name='customprocess')
def customprocess(event, _):
    customProcessor = CustomProcessor()
    return process_request(event, customProcessor.customprocess_code, customProcessor.api_version)


@xray_recorder.capture('customer_portal')
@app.lambda_function(name='customer_portal')
def customer_portal(event, context):
    return customer_portal_handler(event, context)


@xray_recorder.capture('user_organizations')
@app.lambda_function(name='user_organizations')
def user_organizations(event, context):
    return user_organizations_handler(event, context)
