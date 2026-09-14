"""Deploy Fly Weight-Lab to Amazon Bedrock AgentCore Runtime.

This script performs the container-image deployment path:
  1. build a linux/arm64 image
  2. push it to ECR
  3. create an AgentCore runtime

Required environment variables:
    AGENTCORE_ROLE_ARN

Optional environment variables:
    AWS_REGION          (falls back to the active boto3 session region)
    AWS_ACCOUNT_ID      (falls back to the active STS caller identity)

Optional environment variables:
    ECR_REPOSITORY      default: fly-weight-lab-agent
    AGENT_NAME          default: fly-weight-lab
    IMAGE_TAG           default: latest

Run from the repository root:
    .venv/bin/python scripts/deploy_agentcore.py
"""

from __future__ import annotations

import base64
import json
import os
import shutil
import subprocess
import sys
import time

import boto3
from botocore.exceptions import ClientError


REQUIRED_ENV = ("AGENTCORE_ROLE_ARN",)


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


def build_arm64_image(local_image: str) -> None:
    """Build a linux/arm64 image with buildx when available, else plain Docker."""
    if shutil.which("docker") is None:
        raise SystemExit("Docker is required but was not found on PATH")

    buildx_cmd = [
        "docker",
        "buildx",
        "build",
        "--platform",
        "linux/arm64",
        "-t",
        local_image,
        ".",
    ]
    fallback_cmd = [
        "docker",
        "build",
        "--platform",
        "linux/arm64",
        "-t",
        local_image,
        ".",
    ]
    try:
        run(buildx_cmd)
    except SystemExit:
        print("buildx is unavailable; falling back to `docker build`.")
        run(fallback_cmd)


def main() -> None:
    role_arn = require_env("AGENTCORE_ROLE_ARN")
    region = os.environ.get("AWS_REGION") or boto3.Session().region_name
    if not region:
        raise SystemExit("Missing AWS_REGION and no active boto3 session region")

    account_id = os.environ.get("AWS_ACCOUNT_ID")
    if not account_id:
        account_id = boto3.client("sts", region_name=region).get_caller_identity()["Account"]

    repository = os.environ.get("ECR_REPOSITORY", "fly-weight-lab-agent")
    agent_name = os.environ.get("AGENT_NAME", "flyweight_lab")
    image_tag = os.environ.get("IMAGE_TAG", "latest")

    local_image = f"{repository}:{image_tag}"

    build_arm64_image(local_image)

    repository_uri = ensure_repository(region, repository)
    registry = f"{account_id}.dkr.ecr.{region}.amazonaws.com"
    remote_image = f"{repository_uri}:{image_tag}"

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
    try:
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
    except ClientError as exc:
        if exc.response["Error"]["Code"] == "ConflictException":
            runtimes = client.list_agent_runtimes()
            match = next(
                (
                    item
                    for item in runtimes.get("agentRuntimes", [])
                    if item.get("agentRuntimeName") == agent_name
                ),
                None,
            )
            if match is None:
                raise
            print("Reusing existing runtime:")
            print(json.dumps(match, default=str, indent=2))
            return
        raise

    runtime_id = response["agentRuntimeId"]
    print("Agent runtime requested:")
    print(json.dumps(response, default=str, indent=2))

    for _ in range(60):
        state = client.get_agent_runtime(agentRuntimeId=runtime_id)
        status = state.get("status")
        print(f"  runtime status: {status}")
        if status == "READY":
            print("Agent runtime is READY:")
            print(json.dumps(state, default=str, indent=2))
            return
        if status in {"CREATE_FAILED", "UPDATE_FAILED", "FAILED"}:
            print("Agent runtime failed:")
            print(json.dumps(state, default=str, indent=2))
            raise SystemExit("Agent runtime creation failed")
        time.sleep(10)

    raise SystemExit("Timed out waiting for Agent runtime to become READY")


if __name__ == "__main__":
    main()
