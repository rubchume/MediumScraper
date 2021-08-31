from aws_deployment.aws_deployer import AwsDeployer


def main():
    deployer = AwsDeployer()
    deployer.cleanup()
    deployer.full_deploy()


if __name__ == "__main__":
    main()
