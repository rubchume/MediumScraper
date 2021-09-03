#!/bin/bash

source aws_configuration

set -eo pipefail

# Use 'sam' instead of 'sam.cmd' if you are on Linux. If it does not work (because it is not installed or something) use 'aws cloudformation'
sam.cmd deploy \
  --template-file cloudformation_template.packaged.yml \
  --stack-name $STACK \
  --capabilities CAPABILITY_NAMED_IAM \
  --profile $PROFILE \
  --parameter-overrides BucketName=$BUCKET
