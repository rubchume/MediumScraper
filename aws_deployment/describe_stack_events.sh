#!/bin/bash
source aws_configuration

aws cloudformation describe-stack-events --stack-name $STACK --profile $PROFILE
