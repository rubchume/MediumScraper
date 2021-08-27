#!/bin/bash
# This is intentded to be called since the this directory, not the root directory
# This is because the requirements.txt file is found with a relative path
# If you want to change this behaviour and call the script from the root directory, you can get the relative directory
# in which this file is located with respect to the directory from which this script has been called with:
# BASEDIR=$(dirname "$0")
#
# You can then use it like
# rm -rf $BASEDIR/package
# for example

set -eo pipefail
rm -rf package
pip install --target package/python -r ../requirements.txt
