"""Create the IAM execution role used by Bedrock AgentCore Runtime.

This script is idempotent: if the role already exists it reuses it. It prints
the role ARN on stdout so it can be exported into ``AGENTCORE_ROLE_ARN``.

Run from the repository root with the named AWS profile:
    AWS_PROFILE=flyweight-agentcore .venv/bin/python scripts/setup_agentcore_role.py
"""

from __future__ import annotations

import json
import os
import sys
import time

import boto3
from botocore.exceptions import ClientError


ROLE_NAME = "flyweight-agentcore-runtime-role"
POLICY_NAME = "flyweight-agentcore-runtime-policy"
REGION = os.environ.get("AWS_REGION", "us-east-1")


def caller_account() -> str:
    return boto3.client("sts", region_name=REGION).get_caller_identity()["Account"]


def trust_policy(account_id: str) -> str:
    return json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "AssumeRolePolicy",
                    "Effect": "Allow",
                    "Principal": {"Service": "bedrock-agentcore.amazonaws.com"},
                    "Action": "sts:AssumeRole",
                    "Condition": {
                        "StringEquals": {"aws:SourceAccount": account_id},
                        "ArnLike": {
                            "aws:SourceArn": (
                                f"arn:aws:bedrock-agentcore:{REGION}:{account_id}:*"
                            )
                        },
                    },
                }
            ],
        }
    )


def permission_policy(account_id: str, repository: str, agent_name: str) -> str:
    """Minimal-but-complete policy matching the official runtime-role template."""
    log_group = f"arn:aws:logs:{REGION}:{account_id}:log-group"
    ecr_repo = f"arn:aws:ecr:{REGION}:{account_id}:repository/{repository}"
    acore = f"arn:aws:bedrock-agentcore:{REGION}:{account_id}"

    return json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "ECRImageAccess",
                    "Effect": "Allow",
                    "Action": [
                        "ecr:BatchGetImage",
                        "ecr:GetDownloadUrlForLayer",
                        "ecr:GetAuthorizationToken",
                    ],
                    "Resource": [ecr_repo, "*"],
                },
                {
                    "Sid": "CloudWatchLogs",
                    "Effect": "Allow",
                    "Action": [
                        "logs:DescribeLogStreams",
                        "logs:DescribeLogGroups",
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                        "logs:PutResourcePolicy",
                    ],
                    "Resource": [
                        f"{log_group}:/aws/bedrock-agentcore/runtimes/*",
                        f"{log_group}:/aws/bedrock-agentcore/runtimes/*:log-stream:*",
                        f"{log_group}:*",
                    ],
                },
                {
                    "Sid": "XRay",
                    "Effect": "Allow",
                    "Action": [
                        "xray:PutTraceSegments",
                        "xray:PutTelemetryRecords",
                        "xray:GetSamplingRules",
                        "xray:GetSamplingTargets",
                    ],
                    "Resource": ["*"],
                },
                {
                    "Sid": "CloudWatchMetrics",
                    "Effect": "Allow",
                    "Action": "cloudwatch:PutMetricData",
                    "Resource": "*",
                    "Condition": {
                        "StringEquals": {"cloudwatch:namespace": "bedrock-agentcore"}
                    },
                },
                {
                    "Sid": "BedrockModelInvocation",
                    "Effect": "Allow",
                    "Action": [
                        "bedrock:InvokeModel",
                        "bedrock:InvokeModelWithResponseStream",
                        "bedrock:ApplyGuardrail",
                    ],
                    "Resource": [
                        f"arn:aws:bedrock:*::foundation-model/*",
                        f"arn:aws:bedrock:{REGION}:{account_id}:*",
                    ],
                },
                {
                    "Sid": "MarketplaceSubscribeOnFirstCall",
                    "Effect": "Allow",
                    "Action": [
                        "aws-marketplace:ViewSubscriptions",
                        "aws-marketplace:Subscribe",
                    ],
                    "Resource": "*",
                    "Condition": {
                        "StringEquals": {"aws:CalledViaLast": "bedrock.amazonaws.com"}
                    },
                },
                {
                    "Sid": "AgentCoreMemory",
                    "Effect": "Allow",
                    "Action": [
                        "bedrock-agentcore:GetMemory",
                        "bedrock-agentcore:RetrieveMemoryRecords",
                        "bedrock-agentcore:GetResourceApiKey",
                        "bedrock-agentcore:GetResourceOauth2Token",
                        "bedrock-agentcore:GetWorkloadAccessTokenForUserId",
                    ],
                    "Resource": [
                        f"{acore}:memory/{agent_name}_mem-*",
                        f"{acore}:token-vault/default",
                        f"{acore}:token-vault/default/*",
                        f"{acore}:workload-identity-directory/default",
                        f"{acore}:workload-identity-directory/default/workload-identity/*",
                    ],
                },
                {
                    "Sid": "AwsJwtFederation",
                    "Effect": "Allow",
                    "Action": "sts:GetWebIdentityToken",
                    "Resource": "*",
                },
            ],
        }
    )


def get_or_create_role(iam, account_id: str) -> str:
    try:
        role = iam.get_role(RoleName=ROLE_NAME)["Role"]
        print(f"Reusing existing role: {role['Arn']}")
        return role["Arn"]
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "NoSuchEntity":
            raise

    role = iam.create_role(
        RoleName=ROLE_NAME,
        AssumeRolePolicyDocument=trust_policy(account_id),
        Description="Execution role for the Fly Weight-Lab AgentCore runtime",
    )["Role"]
    print(f"Created role: {role['Arn']}")
    time.sleep(3)
    return role["Arn"]


def put_policy(iam, account_id: str, repository: str, agent_name: str) -> None:
    iam.put_role_policy(
        RoleName=ROLE_NAME,
        PolicyName=POLICY_NAME,
        PolicyDocument=permission_policy(account_id, repository, agent_name),
    )
    print(f"Attached inline policy: {POLICY_NAME}")


def main() -> None:
    account_id = caller_account()
    repository = os.environ.get("ECR_REPOSITORY", "fly-weight-lab-agent")
    agent_name = os.environ.get("AGENT_NAME", "flyweight_lab")
    iam = boto3.client("iam", region_name=REGION)

    role_arn = get_or_create_role(iam, account_id)
    put_policy(iam, account_id, repository, agent_name)

    print(f"\nAGENTCORE_ROLE_ARN={role_arn}")
    print(f"AWS_ACCOUNT_ID={account_id}")
    print(f"AWS_REGION={REGION}")


if __name__ == "__main__":
    sys.exit(main())
