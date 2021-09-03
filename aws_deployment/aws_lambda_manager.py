import base64
import json
from pathlib import Path

import boto3
from dotenv import dotenv_values
import yaml


AWS_DEPLOYMENT_DIRECTORY = Path(__file__).parent
DEFAULT_CONFIGURATION_FILE = str(AWS_DEPLOYMENT_DIRECTORY.joinpath("aws_configuration"))


class AwsLambdaManager(object):
    def __init__(self, function_name=None):
        profile_name = dotenv_values(DEFAULT_CONFIGURATION_FILE)["PROFILE"]
        session = boto3.session.Session(profile_name=profile_name)
        self.client = session.client('lambda')

        self.function_name = function_name or self._get_function_name_from_cloudformation_template()

    def invoke(self, payload):
        response = self.client.invoke(
            FunctionName=self.function_name,
            InvocationType='RequestResponse',
            LogType='Tail',
            Payload=json.dumps(payload),
        )

        response["Payload"] = response["Payload"].read()
        response["LogResult"] = self._base_64_decode(response["LogResult"])

        return response

    @staticmethod
    def _get_function_name_from_cloudformation_template():
        yaml.add_constructor(u'!Ref', lambda loader, node: None)
        yaml.add_constructor(u'!Sub', lambda loader, node: None)

        with open("aws_deployment/cloudformation_template.yml") as file:
            data = yaml.load(file, Loader=yaml.FullLoader)

        return data["Resources"]["function"]["Properties"]["FunctionName"]

    @staticmethod
    def _base_64_decode(string_b64):
        bytes = string_b64.encode("ascii")
        decoded_bytes = base64.b64decode(bytes)
        decoded_string = decoded_bytes.decode("utf-8")
        return decoded_string
