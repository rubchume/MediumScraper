#!/bin/bash

source aws_configuration

set -eo pipefail

aws cloudformation package --template-file cloudformation_template.yml --s3-bucket $BUCKET --output-template-file cloudformation_template.packaged.yml --profile $PROFILE
