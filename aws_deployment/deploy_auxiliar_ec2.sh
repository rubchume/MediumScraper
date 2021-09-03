#!/bin/bash

source aws_configuration

sam.cmd deploy \
  --template-file auxiliar_ec2_template.yml \
  --stack-name medium-scraper-auxiliar-ec2-stack \
  --capabilities CAPABILITY_NAMED_IAM \
  --profile $PROFILE \
  --parameter-overrides InstanceName=$EC2_INSTANCE KeyPairName=$SSH_KEY_PAIR_NAME BucketName=$BUCKET
