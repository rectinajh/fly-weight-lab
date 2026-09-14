"""Deploy Fly Weight-Lab to Amazon Bedrock AgentCore Runtime.

This script performs the container-image deployment path:
  1. build a linux/arm64 image
  2. push it to ECR
  3. create an AgentCore runtime

Required environment variables:
    AWS_REGION
    AWS_ACCOUNT_ID
    AGENTCORE_ROLE_ARN

Optional environment variables:
    ECR_REPOSITORY      default: fly-weight-lab-agent
    AGENT_NAME          default: fly-weight-lab
    IMAGE_TAG           default: latest

Run from the repository root:
    .venv/bin/python scripts/deploy_agentcore.py
"""

from __future__ import annotations

import base64
import os
import subprocess
import sys

import boto3


REQUIRED_ENV = ("AWS_REGION", "AWS_ACCOUNT_ID", "AGENTCORE_ROLE_ARN")


def require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    print("+", " ".join(cmd))
    result = subprocess.run(cmd, text=True)
    if check and result.returncode != 0:
        raise SystemExit(f"Command failed with exit code {result.returncode}")
    return result


def ecr_login_password(region: str) -> str:
    ecr = boto3.client("ecr", region_name=region)
    auth = ecr.get_authorization_token()["authorizationData"][0]
    token = auth["authorizationToken"]
    return base64.b64decode(token).decode("utf-8").split(":", 1)[1]


def ensure_repository(region: str, repository: str) -> str:
    ecr = boto3.client("ecr", region_name=region)
    try:
        repos = ecr.describe_repositories(repositoryNames=[repository])
        return repos["repositories"][0]["repositoryUri"]
    except ecr.exceptions.RepositoryNotFoundException:
        response = ecr.create_repository(repositoryName=repository)
        return response["repository"]["repositoryUri"]


def main() -> None:
    region = require_env("AWS_REGION")
    account_id = require_env("AWS_ACCOUNT_ID")
    role_arn = require_env("AGENTCORE_ROLE_ARN")
    repository = os.environ.get("ECR_REPOSITORY", "fly-weight-lab-agent")
    agent_name = os.environ.get("AGENT_NAME", "fly-weight-lab")
    image_tag = os.environ.get("IMAGE_TAG", "latest")

    registry = f"{account_id}.dkr.ecr.{region}.amazonaws.com"
    local_image = f"{repository}:{image_tag}"
    remote_image = f"{registry}/{repository}:{image_tag}"

    run(
        [
            "docker",
            "buildx",
            "build",
            "--platform",
            "linux/arm64",
            "-t",
            local_image,
            ".",
        ]
    )

    repository_uri = ensure_repository(region, repository)
    if repository_uri != remote_image:
        raise SystemExit(
            f"ECR repository URI mismatch: expected {remote_image}, got {repository_uri}"
        )

    password = ecr_login_password(region)

    # docker login is intentionally done through a pipe in the real path.
    login = subprocess.Popen(
        ["docker", "login", "--username", "AWS", "--password-stdin", registry],
        stdin=subprocess.PIPE,
        text=True,
    )
    login.communicate(input=password)
    if login.returncode != 0:
        raise SystemExit("docker login to ECR failed")

    run(["docker", "tag", local_image, remote_image])
    run(["docker", "push", remote_image])

    client = boto3.client("bedrock-agentcore-control", region_name=region)
    response = client.create_agent_runtime(
        agentRuntimeName=agent_name,
        description="Fly Weight-Lab background weight-loss agent",
        agentRuntimeArtifact={
            "containerConfiguration": {
                "containerUri": remote_image,
            }
        },
        roleArn=role_arn,
        networkConfiguration={"networkMode": "PUBLIC"},
        protocolConfiguration={"serverProtocol": "HTTP"},
        environmentVariables={"PYTHONUNBUFFERED": "1"},
    )
    print("Agent runtime created:")
    print(response.get("agentRuntimeArn", response))


if __name__ == "__main__":
    main()
