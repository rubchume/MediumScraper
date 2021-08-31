import hashlib
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path

import boto3
from dotenv import dotenv_values
from ruamel.yaml import YAML

from log import configure_logging

AWS_DEPLOYMENT_DIRECTORY = Path(__file__).parent
DEFAULT_CONFIGURATION_FILE = str(AWS_DEPLOYMENT_DIRECTORY.joinpath("aws_configuration"))
DEFAULT_CONFIGURATION = dotenv_values(DEFAULT_CONFIGURATION_FILE)


configure_logging()
logger = logging.getLogger("general_logger")


class AwsDeployer(object):
    SUFFIX_POLICY_RAW = "policy"
    SUFFIX_POLICY_BUCKET = "policy_bucket"
    SUFFIX_PACKAGED = "packaged"

    def __init__(self):
        self.profile = DEFAULT_CONFIGURATION["PROFILE"]
        self.bucket = DEFAULT_CONFIGURATION["BUCKET"]
        self.stack = DEFAULT_CONFIGURATION["STACK"]
        self.session = boto3.Session(profile_name=self.profile)

    def full_deploy(self):
        logger.info("Create bucket")
        self.create_bucket()
        logger.info("Build layer")
        self.build_layer()
        logger.info("Add policy")
        self.add_get_put_object_s3_policy()
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

    def create_bucket(self):
        """Create an S3 bucket in a specified region"""
        s3_client = self.session.client('s3')
        s3_client.create_bucket(
            Bucket=self.bucket,
            CreateBucketConfiguration=dict(LocationConstraint=self.session.region_name)
        )

    @staticmethod
    def build_layer():
        requirements_path = str(AWS_DEPLOYMENT_DIRECTORY.parent.joinpath("requirements.txt"))

        requirements_hash_path = (
            AWS_DEPLOYMENT_DIRECTORY
            .joinpath("package")
            .joinpath("requirements_hash.txt")
        )

        if requirements_hash_path.exists():
            requirements_hash = AwsDeployer._get_hash_of_file(requirements_path)

            with open(requirements_hash_path, "r") as file:
                old_requirements_hash = file.read()

            if requirements_hash == old_requirements_hash:
                logger.info("Layer was already built")
                return

        try:
            package_directory = AWS_DEPLOYMENT_DIRECTORY.joinpath("package")
            if package_directory.exists():
                shutil.rmtree(str(package_directory))
        except OSError as e:
            print("Error: %s - %s." % (e.filename, e.strerror))

        package_path = str(AWS_DEPLOYMENT_DIRECTORY.joinpath("package").joinpath("python"))

        subprocess.check_call([
            sys.executable,
            "-m",
            "pip",
            "install",
            "--target",
            package_path,
            "-r",
            requirements_path
        ])

        requirements_hash = AwsDeployer._get_hash_of_file(requirements_path)

        with open(requirements_hash_path, "w") as file:
            file.write(requirements_hash)

        print("Layer was build successfully")

    @staticmethod
    def _get_hash_of_file(filename):
        with open(filename, "rb") as f:
            bytes = f.read()

        return hashlib.sha256(bytes).hexdigest()

    def package(self):
        cloudformation_template_path = str(AWS_DEPLOYMENT_DIRECTORY / f"cloudformation_template.{self.SUFFIX_POLICY_BUCKET}.yml")
        cloudformation_template_packaged_path = str(
            AWS_DEPLOYMENT_DIRECTORY / f"cloudformation_template.{self.SUFFIX_PACKAGED}.yml"
        )

        os.system(
            f"aws cloudformation package "
            f"--template-file {cloudformation_template_path} "
            f"--s3-bucket {self.bucket} "
            f"--output-template-file {cloudformation_template_packaged_path} "
            f"--profile {self.profile}"
        )

    @classmethod
    def add_get_put_object_s3_policy(cls):
        yaml = YAML()
        yaml.preserve_quotes = True

        template = yaml.load(AWS_DEPLOYMENT_DIRECTORY / "cloudformation_template.yml")
        policy = yaml.load(AWS_DEPLOYMENT_DIRECTORY / "get_put_object_s3_policy.yml")

        template["Resources"]["function"]["Properties"]["Policies"].append(policy)

        yaml.dump(template, AWS_DEPLOYMENT_DIRECTORY / f"cloudformation_template.{cls.SUFFIX_POLICY_RAW}.yml")

        AwsDeployer._fill_bucket_variable_in_template()

    @classmethod
    def _fill_bucket_variable_in_template(cls):
        with open(AWS_DEPLOYMENT_DIRECTORY / f"cloudformation_template.{cls.SUFFIX_POLICY_RAW}.yml", "r") as file:
            template = file.read()

        bucket = dotenv_values(AWS_DEPLOYMENT_DIRECTORY / "aws_configuration")["BUCKET"]
        template_final = template.replace("{BUCKET}", bucket)

        with open(AWS_DEPLOYMENT_DIRECTORY / f"cloudformation_template.{cls.SUFFIX_POLICY_BUCKET}.yml", "w") as file:
            file.write(template_final)

    def deploy(self):
        cloudformation_template_packaged_path = str(
            AWS_DEPLOYMENT_DIRECTORY.joinpath("cloudformation_template.packaged.yml")
        )

        os.system(
            f"aws cloudformation deploy "
            f"--template-file {cloudformation_template_packaged_path} "
            f"--stack-name {self.stack} "
            f"--capabilities CAPABILITY_NAMED_IAM "
            f"--profile {self.profile}"
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
        temporary_files = [
            AWS_DEPLOYMENT_DIRECTORY / f"cloudformation_template.{cls.SUFFIX_POLICY_RAW}.yml",
            AWS_DEPLOYMENT_DIRECTORY / f"cloudformation_template.{cls.SUFFIX_POLICY_BUCKET}.yml",
            AWS_DEPLOYMENT_DIRECTORY / f"cloudformation_template.{cls.SUFFIX_PACKAGED}.yml",
        ]

        for file in temporary_files:
            if file.exists():
                os.remove(str(file))
