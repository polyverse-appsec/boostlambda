# boostlambda
Lambda functions for the back end of Boost

to test this:
chalice local


to setup the environment on MacOS, Python 3.9 is needed.

https://github.com/pyenv/pyenv#set-up-your-shell-environment-for-pyenv

Set up your shell environment for Pyenv

Upgrade note: The startup logic and instructions have been updated for simplicity in 2.3.0. The previous, more complicated configuration scheme for 2.0.0-2.2.5 still works.

Define environment variable PYENV_ROOT to point to the path where Pyenv will store its data. $HOME/.pyenv is the default. If you installed Pyenv via Git checkout, we recommend to set it to the same location as where you cloned it.
Add the pyenv executable to your PATH if it's not already there
run eval "$(pyenv init -)" to install pyenv into your shell as a shell function, enable shims and autocompletion
You may run eval "$(pyenv init --path)" instead to just enable shims, without shell integration
The below setup should work for the vast majority of users for common use cases. See Advanced configuration for details and more configuration options.

#lambda manual config

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