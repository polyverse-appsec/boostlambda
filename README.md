# boostlambda

## Overview
Lambda functions for the back end of Boost - see more info on Lambda at bottom of this page

Boost Cloud Service is hosted in AWS - and implemented as an event-driven Lambda service
https://polyverse.awsapps.com/start#/ Polyverse portal on AWS

Implementation of Boost Service: https://github.com/polyverse-appsec/boostlambda

## Testing
to test this, first start the Local Lambda Server
```
Go to Run & Debug tab and select "Local Lambda Server" to run locally.
NOTE: chalice local is not going to run the server correctly, do not use chalice local to run the server
```

Then go into the tests directory and run the tests
```
pytest
```

You can also run the pytests directly from inside Visual Studio Code in the Tests tab.

### Tutorials on Lambda Testing
[Testing Chalice Local and Lambda Functions](https://makimo.pl/blog/testing-triggered-lambdas-locally-with-aws-chalice-and-localstack/)

[AWS Testing of Lambda Functions with Chalice](https://aws.amazon.com/blogs/developer/introducing-the-new-test-client-for-aws-chalice/)

## Dev Environment Setup
to setup the environment on MacOS, Python 3.9 is needed.
Note that newer installs of Python3 - may install 3.11 or higher, which are not supported in Lambda (or may not work correctly)

https://github.com/pyenv/pyenv#set-up-your-shell-environment-for-pyenv

### Set up your shell environment for Pyenv

Upgrade note: The startup logic and instructions have been updated for simplicity in 2.3.0. The previous, more complicated configuration scheme for 2.0.0-2.2.5 still works.

Define environment variable PYENV_ROOT to point to the path where Pyenv will store its data. $HOME/.pyenv is the default. If you installed Pyenv via Git checkout, we recommend to set it to the same location as where you cloned it.
Add the pyenv executable to your PATH if it's not already there
run eval "$(pyenv init -)" to install pyenv into your shell as a shell function, enable shims and autocompletion
You may run eval "$(pyenv init --path)" instead to just enable shims, without shell integration
The below setup should work for the vast majority of users for common use cases. See Advanced configuration for details and more configuration options.

### Visual Studio Code integration
Install the AWS Toolkit for Visual Studio Code

Enter the Authentication Code, Secret Key, and Region in the AWS Toolkit for Visual Studio Code

## Test Environment Setup

You can use the "Local Lambda Server" Launch settings in Visual Studio Code to run the local server.
This should also provide debugging inside the Visual Studio Code python debugger.

In the tests directory, you can run 
```
python3 server.py
```
to run a local server that will run the lambda functions locally.  This is useful for debugging and rapid development.

Note that this is NOT using "Chalice Local" which doesn't directly work with Lambda function entrypoints.

# lambda manual config

for right now, the lambda function urls must be set manually for each api. this is what it is currently set to.

explain
https://jorsb57zbzwcxcjzl2xwvah45i0mjuxs.lambda-url.us-west-2.on.aws/

analyze
https://iyn66vkb6lmlcb4log6d3ah7d40axgqu.lambda-url.us-west-2.on.aws/

testgen
https://gylbelpkobvont6vpxp4ihw5fm0iwnto.lambda-url.us-west-2.on.aws/

generate:
https://ukkqda6zl22nd752blcqlv3rum0ziwnq.lambda-url.us-west-2.on.aws/

compliance:
https://q57gtrfpkuzquelgqtnncpjwta0nngfx.lambda-url.us-west-2.on.aws/

codeguidelines:
https://4govp5ze7uyio3kjehtarpv24u0nabhw.lambda-url.us-west-2.on.aws/

Also, ensure that the IAM permissions are set to allow access to secrets manager:

Follow these steps to update the IAM role:

Go to the AWS Management Console and navigate to the IAM service.
Click on "Roles" in the left sidebar.
Find and click on the role associated with your Lambda function. In your case, it seems to be boost-dev.
Click on "Add inline policy" on the right side of the page.
Choose the "Secrets Manager" service.

#Background Material

## AWS Lambda
__*ChatGPT Prompt to generate following:* "describe AWS Lambda, provide links to more information about it, and a tutorial for a new Lambda developer"__

AWS Lambda is a serverless computing service provided by Amazon Web Services (AWS) that allows you to run your code in response to events and automatically manages the compute resources required to run that code.

With Lambda, you can run code in response to various events such as changes to data in an Amazon S3 bucket, updates to a DynamoDB table, or incoming API requests to an API Gateway endpoint. You can also use Lambda to build custom backend logic for mobile and web applications or automate infrastructure tasks.

Lambda supports a variety of programming languages including Node.js, Python, Java, Go, Ruby, and .NET Core, allowing you to write your code in the language you're most comfortable with.

Here are some resources to learn more about AWS Lambda:

- AWS Lambda Product Page: https://aws.amazon.com/lambda/
- AWS Lambda Developer Guide: https://docs.aws.amazon.com/lambda/latest/dg/welcome.html
- AWS Lambda FAQs: https://aws.amazon.com/lambda/faqs/
- Getting Started with AWS Lambda: https://aws.amazon.com/getting-started/hands-on/run-serverless-code/

If you're a new Lambda developer, I recommend going through the Getting Started with AWS Lambda tutorial which will guide you through creating your first Lambda function, configuring its triggers, and testing it. The tutorial is available in multiple programming languages including Node.js, Python, and Java.

## Chalice Setup and Usage

To run Chalice on your macOS laptop, you can follow these general steps:

### Running Chalice on a macOS Laptop

Chalice is a Python microframework for building serverless applications on AWS Lambda and Amazon API Gateway. It simplifies the process of building and deploying serverless applications by allowing you to focus on writing your application code rather than dealing with infrastructure and deployment concerns.

Here's how you can run Chalice on your macOS laptop:

1. Install Python: Chalice requires Python 3.6 or later. You can download and install the latest version of Python from the official website: https://www.python.org/downloads/

2. Install the AWS CLI: Chalice uses the AWS CLI to interact with AWS services. You can install the AWS CLI by following the instructions on the AWS documentation page: https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2-mac.html

3. Install Chalice: You can install Chalice using pip, the Python package manager. Open a terminal window and run the following command:

``` pip install chalice ```

4. Configure AWS credentials: Chalice needs AWS credentials to access AWS services. You can configure your AWS credentials by running the following command and following the prompts:

``` aws configure ```

This will prompt you to enter your AWS Access Key ID and Secret Access Key, as well as your default region and output format.
Create a new Chalice project: You can create a new Chalice project by running the following command:
``` chalice new-project myapp ```

This will create a new Chalice project in a directory named myapp.
Run the Chalice application: You can run the Chalice application by navigating to the project directory and running the following command:
``` chalice local ```

This will start a local development server on your laptop that you can use to test your Chalice application.
Once you have your Chalice application running, you can modify the app.py file in your project directory to define your application logic. You can also deploy your application to AWS Lambda and Amazon API Gateway by running the chalice deploy command.

### Deploying new Lambda APIs / Functions to AWS
Use the "Chalice: Deploy" Launch settings in Visual Studio Code to deploy the local server to AWS.

The configuration for the Chalice App (with Lambda functions) is in the config.json file
NOTE: An example of the full available schema for config.json is also available in sample-config.json

The default deployment is to the "dev" stage. To deploy to a different stage, use the "chalice deploy --stage prod" or "chalice deploy --stage dev" commands.

The full list of Service Deployment stages:
- Local: Local service deployment running on local dev laptop, localhost services, uses live OpenAI service
- Dev: Development stage, uses live OpenAI service, for individual developer testing - on top of AWS
- Test: Test stage, uses live OpenAI service, for integration testing - on top of AWS, just prior to publishing or promoting to Staging or Production
- (_Not Implemented Yet: Same as Prod today_) Staging: Staging stage, uses live OpenAI service on top of AWS, for performance, scale and resiliency testing, just prior to publishing or promoting to Production
- Prod: Production stage, uses live OpenAI service, for production use - on top of AWS, the default for customers, running only the most stable services

## Troubleshooting Tips

__ Missing Dependencies: openai, boto3 __
Error message will look something like this:

```
Exception in thread Thread-1:
Traceback (most recent call last):
  File "/Applications/Xcode.app/Contents/Developer/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/threading.py", line 973, in _bootstrap_inner
    self.run()
  File "/Users/stephenfisher/Library/Python/3.9/lib/python/site-packages/chalice/local.py", line 730, in run
    self._server = self._server_factory()
  File "/Users/stephenfisher/Library/Python/3.9/lib/python/site-packages/chalice/cli/__init__.py", line 144, in create_local_server
    app_obj = config.chalice_app
  File "/Users/stephenfisher/Library/Python/3.9/lib/python/site-packages/chalice/config.py", line 136, in chalice_app
    app = v()
  File "/Users/stephenfisher/Library/Python/3.9/lib/python/site-packages/chalice/cli/factory.py", line 314, in load_chalice_app
    app = importlib.import_module('app')
  File "/Applications/Xcode.app/Contents/Developer/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/importlib/__init__.py", line 127, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
  File "<frozen importlib._bootstrap>", line 1030, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1007, in _find_and_load
  File "<frozen importlib._bootstrap>", line 986, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 680, in _load_unlocked
  File "<frozen importlib._bootstrap_external>", line 850, in exec_module
  File "<frozen importlib._bootstrap>", line 228, in _call_with_frames_removed
  File "/Users/stephenfisher/development/github-vs-boost/boostlambda/app.py", line 2, in <module>
    from chalicelib.convert import *
  File "/Users/stephenfisher/development/github-vs-boost/boostlambda/chalicelib/convert.py", line 1, in <module>
    import openai
```
Fix is to:
```
pip install boto3
```
and
```pip install openai```

__ Missing AWS Credentials ___

```
Exception in thread Thread-1:
Traceback (most recent call last):
  File "/Applications/Xcode.app/Contents/Developer/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/threading.py", line 973, in _bootstrap_inner
    self.run()
  File "/Users/stephenfisher/Library/Python/3.9/lib/python/site-packages/chalice/local.py", line 730, in run
    self._server = self._server_factory()
  File "/Users/stephenfisher/Library/Python/3.9/lib/python/site-packages/chalice/cli/__init__.py", line 144, in create_local_server
    app_obj = config.chalice_app
  File "/Users/stephenfisher/Library/Python/3.9/lib/python/site-packages/chalice/config.py", line 136, in chalice_app
    app = v()
  File "/Users/stephenfisher/Library/Python/3.9/lib/python/site-packages/chalice/cli/factory.py", line 314, in load_chalice_app
    app = importlib.import_module('app')
  File "/Applications/Xcode.app/Contents/Developer/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/importlib/__init__.py", line 127, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
  File "<frozen importlib._bootstrap>", line 1030, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1007, in _find_and_load
  File "<frozen importlib._bootstrap>", line 986, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 680, in _load_unlocked
  File "<frozen importlib._bootstrap_external>", line 850, in exec_module
  File "<frozen importlib._bootstrap>", line 228, in _call_with_frames_removed
  File "/Users/stephenfisher/development/github-vs-boost/boostlambda/app.py", line 2, in <module>
    from chalicelib.convert import *
  File "/Users/stephenfisher/development/github-vs-boost/boostlambda/chalicelib/convert.py", line 4, in <module>
    secret_json = pvsecret.get_secrets()
  File "/Users/stephenfisher/development/github-vs-boost/boostlambda/chalicelib/pvsecret.py", line 23, in get_secrets
    get_secret_value_response = client.get_secret_value(
  File "/Users/stephenfisher/Library/Python/3.9/lib/python/site-packages/botocore/client.py", line 530, in _api_call
    return self._make_api_call(operation_name, kwargs)
  File "/Users/stephenfisher/Library/Python/3.9/lib/python/site-packages/botocore/client.py", line 943, in _make_api_call
    http, parsed_response = self._make_request(
  File "/Users/stephenfisher/Library/Python/3.9/lib/python/site-packages/botocore/client.py", line 966, in _make_request
    return self._endpoint.make_request(operation_model, request_dict)
  File "/Users/stephenfisher/Library/Python/3.9/lib/python/site-packages/botocore/endpoint.py", line 119, in make_request
    return self._send_request(request_dict, operation_model)
  File "/Users/stephenfisher/Library/Python/3.9/lib/python/site-packages/botocore/endpoint.py", line 198, in _send_request
    request = self.create_request(request_dict, operation_model)
  File "/Users/stephenfisher/Library/Python/3.9/lib/python/site-packages/botocore/endpoint.py", line 134, in create_request
    self._event_emitter.emit(
  File "/Users/stephenfisher/Library/Python/3.9/lib/python/site-packages/botocore/hooks.py", line 412, in emit
    return self._emitter.emit(aliased_event_name, **kwargs)
  File "/Users/stephenfisher/Library/Python/3.9/lib/python/site-packages/botocore/hooks.py", line 256, in emit
    return self._emit(event_name, kwargs)
  File "/Users/stephenfisher/Library/Python/3.9/lib/python/site-packages/botocore/hooks.py", line 239, in _emit
    response = handler(**kwargs)
  File "/Users/stephenfisher/Library/Python/3.9/lib/python/site-packages/botocore/signers.py", line 105, in handler
    return self.sign(operation_name, request)
  File "/Users/stephenfisher/Library/Python/3.9/lib/python/site-packages/botocore/signers.py", line 189, in sign
    auth.add_auth(request)
  File "/Users/stephenfisher/Library/Python/3.9/lib/python/site-packages/botocore/auth.py", line 418, in add_auth
    raise NoCredentialsError()
botocore.exceptions.NoCredentialsError: Unable to locate credentials
```

Resolution - suggested by OpenAI, prompted from "how do I store credentials":
This error occurs when the code is unable to locate valid AWS credentials to access the resource being requested. AWS credentials can be stored in various ways, such as in environment variables, configuration files, or IAM roles. To store your credentials, you can follow these steps:

Create an IAM user in the AWS console with the required permissions for your application.
Store the access key ID and secret access key for the IAM user in a secure location.
Set environment variables for the access key ID and secret access key, or create a credentials file in the default location (~/.aws/credentials on Linux and macOS, %USERPROFILE%.aws\credentials on Windows) and store the access key ID and secret access key in the file.
For example, to set environment variables in Linux or macOS, you can run the following commands:

```
export AWS_ACCESS_KEY_ID=<your_access_key_id>
export AWS_SECRET_ACCESS_KEY=<your_secret_access_key>
```
Alternatively, you can create a credentials file at the default location and store the access key ID and secret access key in the file, like so:

```
[default]
aws_access_key_id=<your_access_key_id>
aws_secret_access_key=<your_secret_access_key>
```
Be sure to replace <your_access_key_id> and <your_secret_access_key> with your actual access key ID and secret access key.

### How to get Access Keys/Tokens and Configure AWS access
In Polyverse - you'll need access keys and access id generate (from the AWS admin mgmt console)

Once obtained, you can run
```
aws configure
```
You'll want to answer prompts with something like this:
```
 ~ % aws configure
AWS Access Key ID [****************5V3M]: 
AWS Secret Access Key [****************J7Tk]: 
Default region name [us-west-2]: 
Default output format [None]: 
```
NOTE: Polyverse uses us-west-2 (Oregon) datacenter currently

Once completed, running _chalice Local_ should work

Chalice local example local console
```
boostlambda % chalice local
Found credentials in shared credentials file: ~/.aws/credentials
openai key  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
openai key  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
openai key  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
Serving on http://127.0.0.1:8000
```

## AWS Services and Debugging
Since Chalice is only an event-driven framework to host Python code/scriptlets - and the AWS services (e.g. Dynamo, S3, etc.) are all running in the cloud, care should be taken to debug the current app.py code via the local Chalice environment. But know that live production data is being used.

In the future, publishing code, and the endpoints for AWS services may be separated into stages for dev, test, production

Today's AWS environment is 'dev' only

## API Timeouts and AWS API Gateway

The current Boost Web Service API does NOT use an API gateway (e.g. load balancer for API calls to multiple regions, or masking API endpoints behind FQDNs). This is for short-term expediency in development.
And most importantly - the timeout on the AWS API Gateway is maximum 1 minute.
The Lambda maximum timeout is 5 minutes
The OpenAI analysis API generally takes between 5 seconds and 90 seconds - beyond the API gateway timeout.

Future revisions will need to be done to the Boost API endpoint to either:
* use a larger max timeout on default AWS API Gateway
* use a different asynchronous API pattern, e.g. tasks, callbacks, etc - from within the Boost API
* upgrade to a newer, faster OpenAI API endpoint that can process in <60 seconds guaranteed

## Stripe API and integration

To debug with Stripe, install the STripe CLI
```
brew install stripe/stripe-cli/stripe
```
Then run the CLI
``` 
stripe login
```

then install the Stripe Visual Studio Code extension
```
code --install-extension stripe.stripe-vscode
```

