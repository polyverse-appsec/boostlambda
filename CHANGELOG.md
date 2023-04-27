Polyverse Boost Cloud Service
======================

# Release Notes

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