#!/bin/bash
source aws_configuration

set -eo pipefail
FUNCTION=$(aws cloudformation describe-stack-resource --stack-name $STACK --logical-resource-id function --query 'StackResourceDetail.PhysicalResourceId' --output text --profile $PROFILE)

aws lambda invoke --function-name $FUNCTION --payload file://event.json out.json --cli-binary-format raw-in-base64-out --profile $PROFILE
cat out.json
