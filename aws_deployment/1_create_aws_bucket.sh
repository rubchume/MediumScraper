#!/bin/bash

source aws_configuration

echo "Creating bucket with name $BUCKET using profile $PROFILE"

aws s3 mb s3://$BUCKET --profile $PROFILE
