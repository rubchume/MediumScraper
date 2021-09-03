import hashlib
import logging
import os
from pathlib import Path

import boto3
import paramiko
from dotenv import dotenv_values
from ruamel.yaml import YAML
from scp import SCPClient

from log import configure_logging


AWS_DEPLOYMENT_DIRECTORY = Path(__file__).parent
ROOT_DIRECTORY = AWS_DEPLOYMENT_DIRECTORY.parent

DEFAULT_CONFIGURATION_PATH = str(AWS_DEPLOYMENT_DIRECTORY / "aws_configuration")

REQUIREMENTS_PATH = str(ROOT_DIRECTORY / "requirements.txt")
REQUIREMENTS_HASH_PATH = AWS_DEPLOYMENT_DIRECTORY / "requirements_hash.txt"
KEY_PAIR_PATH = AWS_DEPLOYMENT_DIRECTORY / "ec2-keypair.pem"

PACKAGE_RELATIVE_PATH = Path("package.zip")
PACKAGE_PATH = AWS_DEPLOYMENT_DIRECTORY / PACKAGE_RELATIVE_PATH

CLOUDFORMATION_TEMPLATE_PATH = AWS_DEPLOYMENT_DIRECTORY / "cloudformation_template.yml"
CLOUDFORMATION_TEMPLATE_PACKAGED_PATH = AWS_DEPLOYMENT_DIRECTORY / f"cloudformation_template.packaged.yml"

configure_logging()
logger = logging.getLogger("general_logger")


class AwsDeployer(object):
    def __init__(self):
        default_configuration = dotenv_values(DEFAULT_CONFIGURATION_PATH)
        self.profile = default_configuration["PROFILE"]
        self.bucket = default_configuration["BUCKET"]
        self.stack = default_configuration["STACK"]
        self.ssh_key_pair_name = default_configuration["SSH_KEY_PAIR_NAME"]
        self.ec2_instance = default_configuration["EC2_INSTANCE"]
        self.auxiliar_ec2_stack = default_configuration["AUXILIAR_STACK"]

        self.session = boto3.Session(profile_name=self.profile)

    def full_deploy(self):
        logger.info("Create bucket and build layer")
        self.create_bucket_and_build_layer()
        logger.info("Package")
        self.package()
        logger.info("Deploy stack")
        self.deploy()

    def cleanup(self):
        logger.info("Delete bucket")
        self.delete_bucket()
        logger.info("Delete stack")
        self.delete_stack()
        logger.info("Delete logs")
        self.delete_logs()
        logger.info("Delete temporary files")
        self.delete_temporary_files()

    def create_bucket_and_build_layer(self):
        def execute_command(ssh_client, command):
            stdin, stdout, stderr = ssh_client.exec_command(command)
            logger.info(stdout.read().decode("ascii"))

        if not self._requirements_has_changed_since_last_time():
            if self._bucket_exists() and self._package_is_in_bucket():
                logger.info("Layer was already built and uploaded")
                return

            if PACKAGE_PATH.exists():
                logger.info("Layer was already built but not uploaded")
                if not self._bucket_exists():
                    logger.info("Bucket does not exist. Creating.")
                    self._create_bucket()

                if not self._package_is_in_bucket():
                    logger.info("Uploading package to bucket")
                    self._update_package_to_bucket()

                return

            logger.info("Layer was already built but it is not uploaded and the package file has not been found locally either")

        self._remove_package_file()

        if not self._ssh_key_pair_exists():
            self._create_key_pair()

        if not self._ec2_instance_exists():
            self._deploy_auxiliar_stack()

        ssh_client = self._get_ssh_client()

        self._upload_requirements(ssh_client)

        execute_command(ssh_client, 'pip3 install --target package/python -r requirements.txt')
        execute_command(ssh_client, f"zip -r {PACKAGE_RELATIVE_PATH} package")
        execute_command(ssh_client, f"aws s3 cp {PACKAGE_RELATIVE_PATH} s3://{self.bucket}/{PACKAGE_RELATIVE_PATH}")

        self._download_packaged_python_distribution(ssh_client)

        ssh_client.close()

        with REQUIREMENTS_HASH_PATH.open("w") as file:
            requirements_hash = self._get_hash_of_file(REQUIREMENTS_PATH)
            file.write(requirements_hash)

        self._delete_auxiliar_stack()

        print("Layer was build successfully")

    def _bucket_exists(self):
        s3_client = self.session.client("s3")

        try:
            s3_client.head_bucket(Bucket=self.bucket)
        except s3_client.exceptions.ClientError:
            return False
        except s3_client.exceptions.NoSuchBucket:
            return False

        return True

    def _create_bucket(self):
        """Create an S3 bucket in a specified region"""
        s3_client = self.session.client('s3')
        s3_client.create_bucket(
            Bucket=self.bucket,
            CreateBucketConfiguration=dict(LocationConstraint=self.session.region_name)
        )

    def _package_is_in_bucket(self):
        s3_client = self.session.client("s3")

        try:
            s3_client.get_object(
                Bucket=self.bucket,
                Key=str(PACKAGE_RELATIVE_PATH),
            )
        except s3_client.exceptions.NoSuchKey:
            return False

        return True

    def _update_package_to_bucket(self):
        s3_client = self.session.client("s3")

        s3_client.upload_file(str(PACKAGE_PATH), self.bucket, str(PACKAGE_RELATIVE_PATH))

    @staticmethod
    def _requirements_has_changed_since_last_time():
        if not REQUIREMENTS_HASH_PATH.exists():
            return True

        with REQUIREMENTS_HASH_PATH.open("r") as file:
            old_requirements_hash = file.read()
            requirements_hash = AwsDeployer._get_hash_of_file(str(REQUIREMENTS_PATH))

            if requirements_hash == old_requirements_hash:
                return False

        return True

    @staticmethod
    def _get_hash_of_file(filename):
        with open(filename, "rb") as f:
            bytes = f.read()

        return hashlib.sha256(bytes).hexdigest()

    @staticmethod
    def _remove_package_file():
        if PACKAGE_PATH.exists():
            os.remove(str(PACKAGE_PATH))

    def _ssh_key_pair_exists(self):
        return self._ssh_key_pair_exists_locally() and self._ssh_key_pair_exists_in_aws()

    @classmethod
    def _ssh_key_pair_exists_locally(cls):
        return KEY_PAIR_PATH.exists()

    def _ssh_key_pair_exists_in_aws(self):
        ec2_client = self.session.client("ec2")
        key_pairs = ec2_client.describe_key_pairs()["KeyPairs"]
        for pair in key_pairs:
            if pair["KeyName"] == self.ssh_key_pair_name:
                return True

        return False

    def _create_key_pair(self):
        ec2_client = self.session.client("ec2")

        if self._ssh_key_pair_exists_in_aws():
            ec2_client.delete_key_pair(KeyName=self.ssh_key_pair_name)

        with open(KEY_PAIR_PATH, "w") as file:
            key_pair = ec2_client.create_key_pair(KeyName=self.ssh_key_pair_name)
            file.write(key_pair["KeyMaterial"])

    def _ec2_instance_exists(self):
        return self._get_ec2_instance() is not None

    def _get_ec2_instance(self):
        instances = self._get_ec2_not_terminated_instances()

        for instance in instances:
            if self._get_ec2_instance_name(instance) == self.ec2_instance:
                return instance

        return None

    def _get_ec2_not_terminated_instances(self):
        ec2_client = self.session.client("ec2")
        response = ec2_client.describe_instances(
            Filters=[
                dict(
                    Name="instance-state-name",
                    Values=["pending", "running", "stopping", "stopped"]
                )
            ]
        )

        return [
            instance
            for reservation in response["Reservations"]
            for instance in reservation["Instances"]
        ]

    @staticmethod
    def _get_ec2_instance_name(instance):
        if "Tags" not in instance:
            return None

        for tag in instance["Tags"]:
            if tag["Key"] == "Name":
                return tag["Value"]

        return None

    def _deploy_auxiliar_stack(self):
        auxiliar_ec2_template_path = AWS_DEPLOYMENT_DIRECTORY / "auxiliar_ec2_template.yml"

        os.system(
            "aws cloudformation deploy "
            f"--template-file {auxiliar_ec2_template_path} "
            f"--stack-name {self.auxiliar_ec2_stack} "
            "--capabilities CAPABILITY_NAMED_IAM "
            f"--profile {self.profile} "
            "--parameter-overrides "
            f"InstanceName={self.ec2_instance} "
            f"KeyPairName={self.ssh_key_pair_name} "
            f"BucketName={self.bucket}"
        )

    def _get_ssh_client(self):
        key = paramiko.RSAKey.from_private_key_file(str(AWS_DEPLOYMENT_DIRECTORY / f"{self.ssh_key_pair_name}.pem"))
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        ip_address = self._get_ec2_instance()["PublicIpAddress"]
        ssh_client.connect(hostname=ip_address, username="ec2-user", pkey=key)

        return ssh_client

    @staticmethod
    def _upload_requirements(ssh_client):
        scp_client = SCPClient(ssh_client.get_transport())
        scp_client.put([REQUIREMENTS_PATH], remote_path=".")

    @staticmethod
    def _download_packaged_python_distribution(ssh_client):
        scp_client = SCPClient(ssh_client.get_transport())
        scp_client.get(str(PACKAGE_RELATIVE_PATH), str(PACKAGE_PATH))

    def _delete_auxiliar_stack(self):
        cloudformation_client = self.session.client("cloudformation")
        cloudformation_client.delete_stack(StackName=self.auxiliar_ec2_stack)

    def package(self):
        os.system(
            f"aws cloudformation package "
            f"--template-file {str(CLOUDFORMATION_TEMPLATE_PATH)} "
            f"--s3-bucket {self.bucket} "
            f"--output-template-file {str(CLOUDFORMATION_TEMPLATE_PACKAGED_PATH)} "
            f"--profile {self.profile}"
        )

    def deploy(self):
        os.system(
            f"aws cloudformation deploy "
            f"--template-file {str(CLOUDFORMATION_TEMPLATE_PACKAGED_PATH)} "
            f"--stack-name {self.stack} "
            f"--capabilities CAPABILITY_NAMED_IAM "
            f"--profile {self.profile} "
            f"--parameter-overrides BucketName={self.bucket}"
        )

    def delete_bucket(self):
        os.system(f"aws s3 rb --force s3://{self.bucket} --profile {self.profile}")

    def delete_logs(self):
        yaml = YAML()

        data = yaml.load(Path("aws_deployment/cloudformation_template.yml"))

        function_name = data["Resources"]["function"]["Properties"]["FunctionName"]

        logs_client = self.session.client("logs")
        try:
            logs_client.delete_log_group(logGroupName=f"/aws/lambda/{function_name}")
        except logs_client.exceptions.ResourceNotFoundException:
            logger.info("Logs were not found")

    def delete_stack(self):
        cloudformation_client = self.session.client("cloudformation")
        cloudformation_client.delete_stack(StackName=self.stack)

    @classmethod
    def delete_temporary_files(cls):
        CLOUDFORMATION_TEMPLATE_PACKAGED_PATH.unlink(missing_ok=True)
