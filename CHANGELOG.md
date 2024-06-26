Polyverse Boost Cloud AI Service
======================

# Release Notes

## Version 1.6.4: April 15th, 2024

### New Features
- N/A

### Enhancements
- Disable all CloudWatch metrics by default (for cost controls) - re-enable via environment variable: CLOUD_WATCH_METRICS_ENABLED

### Bug Fixes
- N/A

## Version 1.6.3: April 9th, 2024

### New Features
- N/A

### Enhancements
- N/A

### Bug Fixes
- Improve verification that email and organization are included in signed header unpacking and account creation logic
- Ensure organizaion is set for Sara signed API calls, for billing and logging

## Version 1.6.2: February 8th, 2024

### New Features
- N/A

### Enhancements
- Improve handling of incorrect JSON payload in body of event handlers

### Bug Fixes
- Fix uninitialized client_version variable that blocked early exception logging

## Version 1.6.1: February 7th, 2024

### New Features
- N/A

### Enhancements
- Switch Draft Blueprint to use GPT-4.0 Turbo Preview model for better and faster results

### Bug Fixes
- N/A

## Version 1.6.0: January 18th, 2024

### New Features
- Enabled full support for Premium (and future Basic) Sara Subscription accounts - backed by Stripe billing

### Enhancements
- N/A

### Bug Fixes
- N/A

## Version 1.5.3: January 18th, 2024

### New Features
- N/A

### Enhancements
- Disable EMAIL notifications for new customers or first usage UNLESS EMAIL_NOTIFICATIONS env variable is set (not set by default)

### Bug Fixes
- Fix usage chargeback to only apply to Boost VSC users and skip Sara SaaS clients

## Version 1.5.2: January 17th, 2024

### New Features
- N/A

### Enhancements
- Enable Polyverse* related accounts Test and Dev to ignore Delinquent payment status checks

### Bug Fixes
- Fix missing crypto library for RS256 algorithm - blocking Boost REST API client access with signed headers

## Version 1.5.1: January 11th, 2024

### New Features
- N/A

### Enhancements
- N/A

### Bug Fixes
- Fix regression crash in header parsing for customer_portal API

## Version 1.5.0: January 11th, 2024

### New Features
- Support for Signed Authentication Headers (Sara SaaS clients)
- Support for Free/Trial, Paid/Premium Account Types
    - Customer Portal API returns SaaS/Sara and Plan status
    - User Organizations API only works with GitHub Session token
    - All other APIs succeed for all SaaS/Sara accounts

### Enhancements
- For API calls made by signed header callers, the operation expense will be returned in the account field

### Bug Fixes
- Fix CloudWatch metric logging crash - when no GitHub email can be determined during authentication
- Better handling for missing GitHub email scope in OAuth authentication
- Improved chances of Software Principles being included in AI generated Blueprint (AI sensitive to bullet ordering in lists)s

## Version 1.4.0: December 14th, 2023

### New Features
- Code Summarizer Service - quickly summarizes a code file into 500 tokens or less

### Enhancements
- N/A

### Bug Fixes
- Fix duplication of main prompt if there is no system prompt

## Version 1.3.1: November 17th, 2023

### New Features
- N/A

### Enhancements
- N/A

### Bug Fixes
- Fix prompt for code generation - was using language instead of targetLanguage for prompt paramater
- Fix issue failing local testing without headers - failed trying to generate CORS header

## Version 1.3.0: November 13th, 2023

### New Features
- New Function-based Test Generator - can generate tests in different languages, of all test types
- All Lambda services handle CORS requests - enabling direct browser access to all services
- Browser-based requests to Boost Cloud Service will return HTML unless JSON is requested

### Enhancements
- Return Unauthorized/401 if no session info passed to Service API
- Speed up User Service APIs (Portal and Orgs) and Error paths by lazy loading OpenAI encodings

### Bug Fixes
- Fix customer_portal API issue where account missing organization results in a failure

## Version 1.2.2: November 11th, 2023

### New Features
- N/A

### Enhancements
- Ensure Code generation / conversion doesn't generate empty stub functions for missing references (e.g. missing imports)
- Function processors can customize their data result validation
- Code conversion service will return success or failure if neither code or conversion issues are found
- Enable Test Generation to choose the best test Framework by default (instead of requiring pytest)
- Code Generation and Conversion/Advice will use existing programming language if not changed explicitly (instead of choosing Python)
- Ensure Service Timeout is set to 15 minutes by default during deployment - avoid unexpected early timeouts (e.g. previously 4 minutes)

### Bug Fixes
- Fix recommended file extension in code generation
- Fix issue in Code Generation (function-based) doesn't respect output language and uses implied or guessed language
- Fix indexing issue causing processing failures with some Chat training data
- Fix issue with check subscription always creating a new subscription - not reusing existing active
- Fix issue where a customer with multiple active Subscriptions (not a valid state) is not correctly billed for usage (charges are lost)
- Fix issue with generate code and explanation being treated as generic system messages instead of user/assistant training

## Version 1.2.1: November 3rd, 2023

### New Features
- N/A

### Enhancements
- N/A

### Bug Fixes
- Fix long-standing bug where last prompt was dropped and message never generated correctly

## Version 1.2.0: November 3rd, 2023

### New Features
- Added support for sending training data to any processor request - "training" context with data object of prompt+response

### Enhancements
- Added product docs covering generation of PDF, Markdown and HTML output
- Preserve original message order when performing truncation and optimization of OpenAI messages
- Update product docs with PDF/HTML/MD output

### Bug Fixes
- Changed token calculator to use 4% extra buffer (instead of 2.5%) to accomodate for 3.5 token size

## Version 1.1.1: October 27th, 2023

### New Features
- N/A

### Enhancements
- N/A

### Bug Fixes
- Revert to GPT4.0 model for chat - slightly slower, but 3.5 token context window limits causing issues in Chat completing successfully
- Enable Draft Blueprint to be run against tiny projects (e.g. 1 or a few files) - without failing to find recommended excluded files, etc.

## Version 1.1.0: October 25rd, 2023

### New Features
- N/A

### Enhancements
- Faster Chat responses (3.5 model, terse temperature)
- Split out prompt user and background message content sizes for telemetry reporting
- Update billed/charged usage to use user prompt messages, instead of raw input (e.g. avoid charging for truncated data or background data)
- Allow customization of billed/charged usage cost model per operation in each processor
- Charged Usage cost is reported to console and CloudWatch metrics
- Operational margin (for OpenAI) is reported to console and CloudWatch metrics
- Operational costs for AWS are recorded to console and CloudWatch
- Include context name (e.g. "analyzed files") in context prompts to improve chat relationship

### Bug Fixes
- Ensure API operation cost is returned in operations (bypassing account info cleaning)
- Fix duplicated context prompt - expansion of multiple related or history prompts added an extra raw source prompt

## Version 1.0.1: October 20th, 2023

### New Features
- N/A

### Enhancements
- Faster Lambda function initialization by excluding all other functions from initializing
- Less storage logging
- Return cost of the API call in account data:operation_cost

### Bug Fixes
- N/A

## Version 1.0.0: October 19th, 2023

### New Features
- N/A

### Enhancements
- Update to Storage wrapper file existence check to avoid triggering exceptiosn on non-existent files
- Enable storage logging on non-Production service stages only, unless LogLevel=DEBUG environment variable is set

### Bug Fixes
- Fix Chat failure with product documentation injection


## Version 0.9.9: October 15th, 2023

### New Features
- Product documentation for Boost dynamically injected into cloud service for Chat - to enable real-time documentation updates without client upgrades
- Added S3 Cloud and Local Storage wrapper interface for Services to retrieve live data - e.g. prompts and docs from S3 (supports various cloud stages and backup to local storage)

### Enhancements
- Enable legacy 'summaries' data to be passed along with new 'context' data - for testing
- Move all processors' prompts to S3 storage (static and dynamic prompts)

### Bug Fixes
- Fixed email address for production notifications
- Fix cache refresh miss for dynamic prompts
- Tweak Draft Blueprint prompt to ensure project files are included in results

## Version 0.9.8: October 11th, 2023

### New Features
- Added new Function-based Code Conversion service
- Added UI driver service to enable natural language queries to drive client UI
- Added new Chat Targeting Service to determine what kind of natural language request is being made by user
- Added internal email notification service
- Send email notification to Polyverse Support team when a customer account is first created
- Send email notification to Polyverse Support team when customer performs first billable action
- Added OpenAI call Throttler (based on Token bucket algorithm, OpenAI rate limits, and processing time heuristics)
- Enable OpenAI call throttler to be enabled dynamically at runtime via environment variable "useNewThrottler"
- Enable per-Processor customization of OpenAI call timeout and overall service timeout (e.g. end to end service call)

### Enhancements
- Enable Function-based Processors to return partial results if any results are received (instead of failing the entire call on a partial timeout)
- Upgraded 3rd Party Packages: OpenAI, TikToken (token management), Stripe, AWS SDK, etc.
- Enable Compliance, Security and Performance scans of large code blocks (using chunking) to report all bugs found (not just last chunk)
- Enable smart merging of results from multiple chunked function calls (e.g. arrays are merged instead of overwritten) - customizable per processor
- Enable large input processing with chunking and large prompt training data
- Added Test / Quality analysis to the Blueprint service
- Added validation to GenericProcessor for required main prompt
- Enable access to max_tokens on GenericProcessor
- Validate the function schema on construction to ensure it fits in token buffers
- Improve function-based Security scan to focus on high-confidence issues
- Improve Quick Blueprint handling of exclusion and prioritization lists
- Ensure chunking of list inputs breaks on newlines (e.g. to avoid mangling lists of filenames)
- Print all Metrics to Log (local console and AWS) and CloudWatch (AWS only)
- Tweak Draft Blueprint prompt and function schema to ensure full file paths are returned
- Always the any lost data to console log and AWS metrics (if under AWS) even if call succeeded
- Detect successful OpenAI calls with incomplete response data and report to service caller and log
- Logging of all Token Buffer sizes reported for all calls - including buffer length, input tokens, output tokens and function calls
- Improved accuracy of function token calculation to allow for more user input and output

### Bug Fixes
- Fix max-tokens overflow issue when processing a large single chunk of function-based analysis
- Fix potential issue causing Boost usage reporting to fail - incorrect parameter for Stripe usage reporting API
- Balance input and output buffer size for large file lists in DraftBlueprintProcessor - better success rate
- Fix bug in input buffer calculation that didn't account for function input size (for chunking and truncation)
- Add variance to chunk length counting to accomodate for reduced tokenization efficiency
- Fix issue in Generic Processor where list input was incorrectly handled
- Restore code explanation data in code conversion service input
- Enable Customer status lookup to handle manual invoice objects (with no metadata)
- Fix OpenAI response size metric reporting (was reporting input size)
- Discard invalid JSON data from incomplete OpenAI function calls to avoid JSON parsing errors

## Version 0.9.7: September 29th, 2023

### New Features
- N/A

### Enhancements
- Introduce backoff and retry logic for handling Stripe Rate Limit Errors

### Bug Fixes
- N/A

## Version 0.9.6: September 22nd, 2023

### New Features
- N/A

### Enhancements
- N/A

### Bug Fixes
- Fix for broken prompts using lists of injected content (e.g. chat with multiple user contexts)

## Version 0.9.5: September 15th, 2023

### New Features
- N/A

### Enhancements
- Ensure OpenAI calls stay within the 15 minute Lambda timeout window (e.g. no more than 6 mins per call)
- Improved quick summary reports for single files
- Improved compliance code scan to be more stringent and less false-positives

### Bug Fixes
- Fix JSON conversion in guidelines, summaries in context
- Fix User Context injection into all services

## Version 0.9.4: August 29th, 2023

### New Features
- Added Chat/Query Cloud Service - processes arbitrary prompts across summaries and analysis and code
- Add context injection into all services - including current user focus, related info, historical data, and project summary info

### Enhancements
- Expand custom processor input buffer to 90%
- Tiny (10-100 tokens) reduction in customer input from boost usage calculation (exclude system identity)

### Bug Fixes
- Fix unpacking of JSON guidelines and summaries

## Version 0.9.3: August 14th, 2023

### New Features
- Return account status on all analysis API calls - to reduce extra calls to check account status

### Enhancements
- Improvements to auth handling for non-validated email accounts (not found in GitHub)

### Bug Fixes
- N/A

## Version 0.9.2: August 9th, 2023

### New Features
- Added custom code scan service - enabling clients to get line numbers of issues identified by a custom analysis

### Enhancements
- Blueprint will report what programming languages are found in the project

### Bug Fixes
- Change CloudWatch metric storage resolution from 5 minutes (invalid unsupported) to 1 minute (regular resolution maximum)

## Version 0.9.1: August 2nd, 2023

### New Features
- Processors can reload prompts at runtime - enabling dynamic prompt updates

### Enhancements
- Customer Status API (customer_portal) returns full current account info (balance, credit remaining, etc.)
- Ensure only Account Owners can access the account billing portal (e.g. to change or access credit card info)
- Improvements to Performance and Security analysis including online links and better vulnerability categorization.
- Provide regression test cases to help reproduce suspected customer security or code bugs.
- Significant expansion of Test Case generation - including fuzzing, performance, test, regression, platform, etc.
- Change Flow Diagram to be terse (in temperature), use 3.5 Turbo model for improved speed (less rate limit errors) and allow 90% of token buffer for input
- Rewrote and enhanced tokenizer encoding/decoding for higher precision and more accurate mapping to GPT models (fix more Max Token errors)

### Bug Fixes
- Fix max token calculation for non-default non-4.0 GPT models

## Version 0.9.0: July 27th, 2023

### New Features
- New Quick Summary service builds an executive report based on partial diagnostics data

### Enhancements
- Draft Blueprint service returns a prioritized list of the files to analyze
- Speed up Draft Blueprint service by using 3.5 Turbo model
- Added Sara identity to all system prompts, using prompt injection at runtime - overridable by client using 'system_identity' data parameter
- Change CloudWatch metric resolution from 1 second to 5 minutes (e.g. 60 * 5) - to reduce costs. Data should not be lost, but aggregate data will be lower resolution

### Bug Fixes
- N/A

## Version 0.8.1: July 21st, 2023

### New Features
- N/A

### Enhancements
- N/A

### Bug Fixes
- Fix customer_portal when a customer has an 'expired' account status
- Fix for suspended accounts who have no active subscriptions - return status suspended instead of error
- Fix off-by-one error in source line numbers

## Version 0.8.0: July 20th, 2023

### New Features
- N/A

### Enhancements
- Added support for truncating user messages - if allowed by processor (e.g. chunking disabled)
- Added support for coupons with accounts - enabling Trial extensions by manual coupon

### Bug Fixes
- Quick blueprint better resilience to empty projects, or no exclusions recmommended

## Version 0.7.4: July 18th, 2023

### New Features
- N/A

### Enhancements
- Treat all polyverse.com accounts as 'paid' regardless of credit card status
- Added File Exclusion recommendation for Draft Blueprint Service

### Bug Fixes
- Fix bug causing Draft-Blueprint service to return the recommended project file with the sample source code filename

## Version 0.7.3: July 12th, 2023

### New Features
- N/A

### Enhancements
- N/A

### Bug Fixes
- Fix wireformat handling of blueprint file lists - double JSON encoded

## Version 0.7.2: July 5th, 2023

### New Features
- Added new code comparison service - that looks for critical differences in two chunks of code (ignoring language, syntax and comments)
- Added new support for selecting output format from client per service
- All services now have a default output format - prose, ranked list, bulleted list, numbered list (JSON is only supported for Security and Compliance and Performance)
- Improved default output formatting of Analyze, Data Compliance, Coding Guidelines
- Added Performance service for reporting issues in structured JSON
- Added Performance Function service for finding source line-level issues
- Add Quick-Blueprint generator, which builds on draft Blueprint builder

### Enhancements
- Add automatic retry (one time) for all GitHub server requests to increase network resilience
- Ensure the Blueprint / Summary info is sent as training AFTER the initial system prompt
- Enable polytest.ai as a "paid" Organization account for testing (e.g. AWS monitors and unit tests)
- Added source/cell tracing for errors exceeding max token limit

### Bug Fixes
- Fixed bug where Functions reporting bugs when none were found
- Fixed bug where large sourcce files fail to process when using Function source level analysis (e.g. chunking and JSON results)
- Fixed bug with analyzing older Notebooks without source line info

## Version 0.7.1: July 3rd, 2023

### New Features
- N/A

### Enhancements
- More resilient error handling and error messages for missing parameters
- Ensure truncation and chunking are reported for code guidelines and flowDiagram services

### Bug Fixes
- Fix logging and processing for single input Summary processing
- Add local variable unreferenced to special service logging
- Fix failure info disclosure during prod and staging
- Ensure local debugging reports full exception info
- Fix non-Chat customProcessor service use case - was failing to generate messages

## Version 0.7.0: June 27, 2023

### New Features
- Add support for submitting lists of architectural guidelines to any prompt engineering paths
- Blueprints are now integrated into system prompts for background for all analysis
- System quotas are now enforced and analyzed with improved tuning for different sized prompts and background

### Enhancements
- All Kernel/Processors have been updated to integrate analysis of the guidelines in their analysis
- Inject line numbers into prompts for function processing - so identified source line numbers are accurate
- Better logging for tuning truncation and system message quotas

### Bug Fixes
- Fixes for guidelines processing impacting blueprint analysis

## Version 0.6.4: June 23, 2023

### New Features
- new Service: ComplianceFunction will analyze code and return issues in source files and lines structured as JSON results 

### Enhancements
- Reduce RateLimit errors: Added output buffer tuning based on input size - specifically, small inputs get small output buffers, with a multiplier for min output buffer

### Bug Fixes
- Update tokenizer to support gpt-4-613

## Version 0.6.3: June 23, 2023

### New Features
- AnalyzeFunction will analyze code and return issues in source files and lines structured as JSON results 

### Enhancements
- N/A

### Bug Fixes
- Improve Mermaid code markdown blocks in Summary blocks

## Version 0.6.2: June 22, 2023

### New Features
- GenericProcessor now supports customization of model and temperature per processor

### Enhancements
- All processors have now been tuned for temperature - with Security and Data Compliance using a lower temperature, for example

### Bug Fixes
- Fixed app_util import causing all service failures during app load
- Fixed token max calculation when using non-GPT4 models
- Fix regression in custom processor for custom prompts
- Fix regression in blueprint processor for custom seeds
- Fix issue with custom processor sending too many messages - truncate more than 60% of total token buffer
- Fix issue with missing content in custom processor messages
- Enable access to account portal and billing info for delinquent accounts

## Version 0.6.1: June 19, 2023

### New Features
- Support for very large input files - broken into chunks

### Enhancements
- Migrated all Boost services to generic processor for shared infrastructure
- Throttling for rate limited OpenAI network services
- Retry logic on recoverable network errors
- Improvements to flow chart rendering

### Bug Fixes
- Fixed manually entered credit cards

## Version 0.6.0: June 14, 2023

### New Features
- N/A

### Enhancements
- Migrated all Boost services to generic processor for shared infrastructure

### Bug Fixes
- Fix xray tracing on error cases for all Generic Processor-derived services
- Fix Blueprint Update prompt - wasn't including the original blueprint in the prompt
- Fix bug that prevented completed Trial licenses from blocking unpaid new usage without a credit cards

## Version 0.5.7: June 8, 2023

### New Features
- N/A

### Enhancements
- Add analysis type and label to Summary results (JSON)
- Add inbound request logging to all services

### Bug Fixes
- N/A

## Version 0.5.6: June 2, 2023

### New Features
- Added Summarize Service API - used for summarizing or compressing a series of text inputs

### Enhancements
- Enable Flow Diagrams to start with function name, and show calls to external libraries or functions

### Bug Fixes
- Fix issue with 'delinquent' / suspended accounts not providing customer portal link
- Fix missing usage reporting for flow diagram (generic processor missing usage reporting)

## Version 0.5.5: June 2, 2023

### New Features
- Enable model customization by passing 'model' parameter in API calls - default is GPT-4

### Enhancements
- N/A

### Bug Fixes
- N/A

## Version 0.5.4: May 30, 2023

### New Features
- N/A

### Enhancements
- Enabled Custom Processor to also customize raw OpenAI API messages prompts and system role

### Bug Fixes
- N/A


## Version 0.5.2: May 23, 2023

### New Features
- Add support for temperature and ranked probablities in OpenAI completions

### Enhancements
- Print Exception callstacks on one line in log messages - easier to search in AWS Console
- Simplify function_name passing through call chains
- Print original Mermaid code in server log; in case we errantly change a result - use term "CLEANED" for log searches
- Minor refactor of flow sanitization function for testing via unit test

### Bug Fixes
- Fixes for escaped and un-escaped quotes in generated Mermaid code
- Fix for Compliance API when running locally

## Version 0.5.1: May 19, 2023

### New Features
- N/A

### Enhancements
- Log User Organizations retrieved in User Organizations Service, and improved org logging
- Add server logging for Flow Diagram service
- Better org logging on failure conditions across services
- Enable customer portal to return account status structure on invalid accounts

### Bug Fixes
- Fix bug when no Org or GitHub account is found and we failed to write CloudWatch alert
- Enable services to work for personal organization - was failing with missing GitHub error

## Version 0.5.0: May 18, 2023

### New Features
- Flow Diagram Lambda service

### Enhancements
- Added TTL-based Cache for GitHub API calls (to avoid throttling) - email, orgs, username
- Add CloudWatch metric (alert-support) for OpenAI rate limiting errors

### Bug Fixes
- Fix FlowDiagram result/content body issue
- Fix email logging in customer_portal
- Add server logging for GitHub API failures (e.g. throttling, access, etc)

## Version 0.4.9: May 13, 2023

### New Features
- N/A

### Enhancements
- Support for client version in HTTP headers

### Bug Fixes
- N/A

## Version 0.4.8: May 8, 2023

### New Features
- Development-only release of Flow Diagram Lambda service

### Enhancements
- Removed duplicative account error paths
- Added account status in response headers and exceptions - trial, active, suspended, etc.
- Added API version string to customerportal and user_organizations
- Improved logging to show each successful and failed Customer Lambda function call

### Bug Fixes
- Fixed error handling for XRay exception reporting; was suppressing HTTP error codes

## Version 0.4.7: May 2, 2023

##### Bug Fixes
- Fixed Analyze Service API - customer account parameter bug blocked analysis

### New Features
- Added Custom Process Lambda Service API - enabling custom prompts to be sent from the Boost client (Dev-Only)
- Added usage-based Metered billing for all Boost Cloud Service APIs
- Added support for reporting usage per customer input (charged on input only)
- Added support for using GitHub email/organization as customer identifier - for enterprise licensing/billing

##### Enhancements
- Added Licensing analysis to Architectural Blueprint generation Service API

## Version 0.4.5: May 1, 2023

##### Enhancements
- Default to max_tokens for any GPT model - set by 0 value, so model change change max_tokens automatically

##### Bug Fixes
- Raised max_tokens to 8192 for gpt4 usage - was 4000 for gpt3.5

## Version 0.4.4: April 27, 2023
##### Enhancements
- Improved resolution of GitHub account missing alert from 60 seconds to 1 second (to minimize missing alerts)
- Set the max_tokens to 4000 (was implied) on completions
- Added CloudWatch metrics for all OpenAI and Boost costs on prompts, completions (OpenAI costs change on input, output and token counts)
- Added CloudWatch metrics to track token counts on inputs and outputs
- Added customer email to CloudWatch metric dimensions for searching
- Set Lambda functions to use 256mb of memory (was 128mb) to improve performance and avoid limit using OpenAI tokenizer/tiktoken

## Version 0.4.3: April 26, 2023

### New Features
- Added CloudWatch metrics for all Boost Cloud Service APIs of size of input and output
- Added X-Ray tracing for all Boost Cloud Service APIs, callouts to OpenAI, and callouts to Shopify/Stripe/GitHub
- Added CloudWatch metrics for exceptions thrown from public Lambda Services
- Added CloudWatch alerts when GitHub or Shopify accounts not found

##### Enhancements
- Stripped out all AWS logging (print) of user code - to avoid accidental persisting of logs

##### Bug Fixes
- N/A

## Version 0.4.2: April 25, 2023

### New Features
- Web resource links are now included for Vulnerability scan, Data/Privacy Compliance, and Test Case Generation
- Added version header to all responses - e.g. "X-API-Version: 0.4.2"
- set all HTTP error codes to 500 (instead of 400) unless otherwise specified
- fixed bug in Local Server that erased content headers in response

##### Enhancements
- N/A

##### Bug Fixes
- N/A

## Version 0.4.1: April 22, 2023

### New Features
- Added "prod" deployment stage (in addition to existing "dev" stage)

##### Enhancements
- Separated OpenAI prompts from code in Architectural Blueprint generation Service API

##### Bug Fixes

## Version 0.4.0: April 21, 2023

### New Features
- Added Architectural Blueprint generation Service API

## Version 0.3.0: April 19, 2023

### New Features
- Added Coding Guidelines evaluation Service API

## Version 0.2.0: April 19, 2023

### New Features
- Added Data/Privacy Compliance evaluation Service API

## Version 0.1.0: March 31, 2023

### New Features
- Enabled "dev" deployment stage - first version
- Added Boost Cloud Service APIs with explain, convert, analyze for bugs, and test generation

##### Enhancements
- N/A

##### Bug Fixes
- N/A