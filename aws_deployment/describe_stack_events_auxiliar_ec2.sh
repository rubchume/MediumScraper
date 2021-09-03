#!/bin/bash
source aws_configuration

aws cloudformation describe-stack-events --stack-name $AUXILIAR_STACK --profile $PROFILE
