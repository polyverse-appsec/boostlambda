# boostlambda

## Overview
Lambda functions for the back end of Boost - see more info on Lambda at bottom of this page

Boost Cloud Service is hosted in AWS - and implemented as an event-driven Lambda service
https://polyverse.awsapps.com/start#/ Polyverse portal on AWS

Implementation of Boost Service: https://github.com/polyverse-appsec/boostlambda

## Testing
to test this:
chalice local

## Dev Environment Setup
to setup the environment on MacOS, Python 3.9 is needed.

https://github.com/pyenv/pyenv#set-up-your-shell-environment-for-pyenv

Set up your shell environment for Pyenv

Upgrade note: The startup logic and instructions have been updated for simplicity in 2.3.0. The previous, more complicated configuration scheme for 2.0.0-2.2.5 still works.

Define environment variable PYENV_ROOT to point to the path where Pyenv will store its data. $HOME/.pyenv is the default. If you installed Pyenv via Git checkout, we recommend to set it to the same location as where you cloned it.
Add the pyenv executable to your PATH if it's not already there
run eval "$(pyenv init -)" to install pyenv into your shell as a shell function, enable shims and autocompletion
You may run eval "$(pyenv init --path)" instead to just enable shims, without shell integration
The below setup should work for the vast majority of users for common use cases. See Advanced configuration for details and more configuration options.

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

```pip install chalice```

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
