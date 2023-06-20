Polyverse Boost Cloud Service
======================

# Release Notes

## Version 0.6.1: June 19, 2023

### New Features
- Support for very large input files - broken into chunks

# Enhancements
- Migrated all Boost services to generic processor for shared infrastructure
- Throttling for rate limited OpenAI network services
- Retry logic on recoverable network errors
- Improvements to flow chart rendering

# Bug Fixes
- Fixed manually entered credit cards

## Version 0.6.0: June 14, 2023

### New Features
- N/A

# Enhancements
- Migrated all Boost services to generic processor for shared infrastructure

# Bug Fixes
- Fix xray tracing on error cases for all Generic Processor-derived services
- Fix Blueprint Update prompt - wasn't including the original blueprint in the prompt
- Fix bug that prevented completed Trial licenses from blocking unpaid new usage without a credit cards

## Version 0.5.7: June 8, 2023

### New Features
- N/A

# Enhancements
- Add analysis type and label to Summary results (JSON)
- Add inbound request logging to all services

# Bug Fixes
- N/A

## Version 0.5.6: June 2, 2023

### New Features
- Added Summarize Service API - used for summarizing or compressing a series of text inputs

# Enhancements
- Enable Flow Diagrams to start with function name, and show calls to external libraries or functions

# Bug Fixes
- Fix issue with 'delinquent' / suspended accounts not providing customer portal link
- Fix missing usage reporting for flow diagram (generic processor missing usage reporting)

## Version 0.5.5: June 2, 2023

### New Features
- Enable model customization by passing 'model' parameter in API calls - default is GPT-4

# Enhancements
- N/A

# Bug Fixes
- N/A

## Version 0.5.4: May 30, 2023

### New Features
- N/A

# Enhancements
- Enabled Custom Processor to also customize raw OpenAI API messages prompts and system role

# Bug Fixes
- N/A


## Version 0.5.2: May 23, 2023

### New Features
- Add support for temperature and ranked probablities in OpenAI completions

# Enhancements
- Print Exception callstacks on one line in log messages - easier to search in AWS Console
- Simplify function_name passing through call chains
- Print original Mermaid code in server log; in case we errantly change a result - use term "CLEANED" for log searches
- Minor refactor of flow sanitization function for testing via unit test

# Bug Fixes
- Fixes for escaped and un-escaped quotes in generated Mermaid code
- Fix for Compliance API when running locally

## Version 0.5.1: May 19, 2023

### New Features
- N/A

# Enhancements
- Log User Organizations retrieved in User Organizations Service, and improved org logging
- Add server logging for Flow Diagram service
- Better org logging on failure conditions across services
- Enable customer portal to return account status structure on invalid accounts

# Bug Fixes
- Fix bug when no Org or GitHub account is found and we failed to write CloudWatch alert
- Enable services to work for personal organization - was failing with missing GitHub error

## Version 0.5.0: May 18, 2023

### New Features
- Flow Diagram Lambda service

# Enhancements
- Added TTL-based Cache for GitHub API calls (to avoid throttling) - email, orgs, username
- Add CloudWatch metric (alert-support) for OpenAI rate limiting errors

# Bug Fixes
- Fix FlowDiagram result/content body issue
- Fix email logging in customer_portal
- Add server logging for GitHub API failures (e.g. throttling, access, etc)

## Version 0.4.9: (Proposed) May 13, 2023

### New Features
- N/A

# Enhancements
- Support for client version in HTTP headers

# Bug Fixes
- N/A

## Version 0.4.8: May 8, 2023

### New Features
- Development-only release of Flow Diagram Lambda service

# Enhancements
- Removed duplicative account error paths
- Added account status in response headers and exceptions - trial, active, suspended, etc.
- Added API version string to customerportal and user_organizations
- Improved logging to show each successful and failed Customer Lambda function call

# Bug Fixes
- Fixed error handling for XRay exception reporting; was suppressing HTTP error codes

## Version 0.4.7: May 2, 2023

### Bug Fixes
- Fixed Analyze Service API - customer account parameter bug blocked analysis

### New Features
- Added Custom Process Lambda Service API - enabling custom prompts to be sent from the Boost client (Dev-Only)
- Added usage-based Metered billing for all Boost Cloud Service APIs
- Added support for reporting usage per customer input (charged on input only)
- Added support for using GitHub email/organization as customer identifier - for enterprise licensing/billing

### Enhancements
- Added Licensing analysis to Architectural Blueprint generation Service API

## Version 0.4.5: May 1, 2023

### Enhancements
- Default to max_tokens for any GPT model - set by 0 value, so model change change max_tokens automatically

### Bug Fixes
- Raised max_tokens to 8192 for gpt4 usage - was 4000 for gpt3.5

## Version 0.4.4: April 27, 2023
### Enhancements
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

### Enhancements
- Stripped out all AWS logging (print) of user code - to avoid accidental persisting of logs

### Bug Fixes
- N/A

## Version 0.4.2: April 25, 2023

### New Features
- Web resource links are now included for Vulnerability scan, Data/Privacy Compliance, and Test Case Generation
- Added version header to all responses - e.g. "X-API-Version: 0.4.2"
- set all HTTP error codes to 500 (instead of 400) unless otherwise specified
- fixed bug in Local Server that erased content headers in response

### Enhancements
- N/A

### Bug Fixes
- N/A

## Version 0.4.1: April 22, 2023

### New Features
- Added "prod" deployment stage (in addition to existing "dev" stage)

### Enhancements
- Separated OpenAI prompts from code in Architectural Blueprint generation Service API

### Bug Fixes

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

### Enhancements
- N/A

### Bug Fixes
- N/A