import io
import unittest
from unittest import mock

from botocore.response import StreamingBody

from aws_deployment.aws_lambda_manager import AwsLambdaManager


class AwsLambdaManagerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        patcher = mock.patch("aws_deployment.aws_lambda_manager.boto3.session.Session")
        mock_session_function = patcher.start()

        session = mock.MagicMock()
        mock_session_function.return_value = session

        client = mock.MagicMock()
        session.client.return_value = client
        cls.client = client

    def test_create_manager_saves_function_name_and_creates_client(self):
        # When
        aws_lambda_manager = AwsLambdaManager("function_name")
        # Then
        self.assertEqual("function_name", aws_lambda_manager.function_name)
        self.assertEqual(self.client, aws_lambda_manager.client)

    def test_invoke_lambda_function(self):
        # Given
        payload_encoded = "This is the body"

        self.client.invoke.return_value = dict(
            ResponseMetadata="some_value",
            StatusCode=200,
            LogResult="U1RBUlQgbG9nCltJTkZPXSAyMDIxLTA4LTI3VDExOjM2OjQwLjEzMlogICAgZmlyc3QgbWVzc2FnZSBvZiBsb2cgTWFyw61h",
            ExecutedVersion='$LATEST',
            Payload=StreamingBody(
                io.StringIO(payload_encoded),
                len(payload_encoded)
            )
        )

        aws_lambda_manager = AwsLambdaManager("function_name")
        payload = {"key1": "el breaking dance", "key2": "el crusaito", "key3": "el michael jackson"}
        # When
        response = aws_lambda_manager.invoke(payload)
        # Then
        self.client.invoke.assert_called_once_with(
            FunctionName="function_name",
            InvocationType='RequestResponse',
            LogType='Tail',
            Payload='{"key1": "el breaking dance", "key2": "el crusaito", "key3": "el michael jackson"}',
        )
        self.assertEqual(
            dict(
                ResponseMetadata="some_value",
                StatusCode=200,
                LogResult=(
                    "START log\n"
                    "[INFO] 2021-08-27T11:36:40.132Z    first message of log María"
                ),
                ExecutedVersion='$LATEST',
                Payload="This is the body"
            ),
            response
        )

    def test_initialize_function_to_default_value_from_cloudformation_template(self):
        # When
        aws_lambda_manager = AwsLambdaManager()
        # Then
        self.assertEqual("scrape-medium-articles", aws_lambda_manager.function_name)
