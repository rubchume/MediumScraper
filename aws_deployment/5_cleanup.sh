#!/bin/bash
source aws_configuration

set -eo pipefail
echo "Deleting stack $STACK"

FUNCTION=$(aws cloudformation describe-stack-resource --stack-name $STACK --logical-resource-id function --query 'StackResourceDetail.PhysicalResourceId' --output text --profile $PROFILE)
aws cloudformation delete-stack --stack-name $STACK --profile $PROFILE
echo "Deleted $STACK stack."

while true; do
    read -p "Delete deployment artifacts and bucket ($BUCKET)? (y/n)" response
    case $response in
        [Yy]* ) aws s3 rb --force s3://$BUCKET --profile $PROFILE; break;;
        [Nn]* ) break;;
        * ) echo "Response must start with y or n.";;
    esac
done

while true; do
    read -p "Delete function log group (/aws/lambda/$FUNCTION)? (y/n)" response
    case $response in
        [Yy]* ) MSYS_NO_PATHCONV=1 aws logs delete-log-group --log-group-name /aws/lambda/$FUNCTION --profile $PROFILE; break;;
        [Nn]* ) break;;
        * ) echo "Response must start with y or n.";;
    esac
done

rm -f cloudformation_template.packaged.yml out.json function/*.pyc
rm -rf package function/__pycache__
