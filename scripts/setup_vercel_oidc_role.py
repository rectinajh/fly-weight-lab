"""Create the AWS OIDC provider and role that lets Vercel assume AWS access.

This replaces long-lived access keys with short-lived web-identity credentials.
The role is scoped to the ``web`` Vercel project in the production environment.

Run from the repository root:
    AWS_PROFILE=flyweight-agentcore .venv/bin/python scripts/setup_vercel_oidc_role.py
"""

from __future__ import annotations

import json
import os
import sys
import time

import boto3
from botocore.exceptions import ClientError


ACCOUNT_ID = os.environ.get("AWS_ACCOUNT_ID", "032529260721")
REGION = os.environ.get("AWS_REGION", "us-east-1")
TEAM_SLUG = os.environ.get("VERCEL_TEAM_SLUG", "rectinajhs-projects")
PROJECT_NAME = os.environ.get("VERCEL_PROJECT_NAME", "web")
ROLE_NAME = "flyweight-vercel-oidc-role"
POLICY_NAME = "flyweight-vercel-oidc-policy"
RUNTIME_ARN = (
    "arn:aws:bedrock-agentcore:us-east-1:032529260721:runtime/"
    "flyweight_lab-k3JItG63s2"
)

ISSUER_URL = f"https://oidc.vercel.com/{TEAM_SLUG}"
AUDIENCE = f"https://vercel.com/{TEAM_SLUG}"
PROVIDER_ARN = (
    f"arn:aws:iam::{ACCOUNT_ID}:oidc-provider/oidc.vercel.com/{TEAM_SLUG}"
)
SUBJECT = (
    f"owner:{TEAM_SLUG}:project:{PROJECT_NAME}:environment:production"
)


def trust_policy() -> str:
    return json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"Federated": PROVIDER_ARN},
                    "Action": "sts:AssumeRoleWithWebIdentity",
                    "Condition": {
                        "StringEquals": {
                            f"oidc.vercel.com/{TEAM_SLUG}:sub": SUBJECT,
                            f"oidc.vercel.com/{TEAM_SLUG}:aud": AUDIENCE,
                        }
                    },
                }
            ],
        }
    )


def permission_policy() -> str:
    return json.dumps(
        {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": "InvokeAgentRuntime",
                    "Effect": "Allow",
                    "Action": "bedrock-agentcore:InvokeAgentRuntime",
                    "Resource": [RUNTIME_ARN, f"{RUNTIME_ARN}/*"],
                },
                {
                    "Sid": "GetAgentRuntime",
                    "Effect": "Allow",
                    "Action": "bedrock-agentcore:GetAgentRuntime",
                    "Resource": RUNTIME_ARN,
                },
            ],
        }
    )


def ensure_provider(iam) -> None:
    for item in iam.list_open_id_connect_providers()["OpenIDConnectProviderList"]:
        detail = iam.get_open_id_connect_provider(
            OpenIDConnectProviderArn=item["Arn"]
        )
        if detail["Url"] == ISSUER_URL:
            print(f"Reusing OIDC provider: {item['Arn']}")
            return

    try:
        iam.create_open_id_connect_provider(
            Url=ISSUER_URL,
            ClientIDList=[AUDIENCE],
        )
    except ClientError as exc:
        if exc.response["Error"]["Code"] not in (
            "EntityAlreadyExists",
            "EntityAlreadyExistsException",
        ):
            raise
    print(f"Created OIDC provider: {PROVIDER_ARN}")
    time.sleep(2)


def ensure_role(iam) -> str:
    try:
        role = iam.get_role(RoleName=ROLE_NAME)["Role"]
        print(f"Reusing role: {role['Arn']}")
        return role["Arn"]
    except ClientError as exc:
        if exc.response["Error"]["Code"] != "NoSuchEntity":
            raise

    role = iam.create_role(
        RoleName=ROLE_NAME,
        AssumeRolePolicyDocument=trust_policy(),
        Description="Vercel OIDC role for the fly-weight-lab web proxy",
    )["Role"]
    print(f"Created role: {role['Arn']}")
    time.sleep(3)
    return role["Arn"]


def main() -> None:
    iam = boto3.client("iam", region_name=REGION)
    ensure_provider(iam)
    role_arn = ensure_role(iam)
    iam.put_role_policy(
        RoleName=ROLE_NAME,
        PolicyName=POLICY_NAME,
        PolicyDocument=permission_policy(),
    )
    print(f"Attached inline policy: {POLICY_NAME}")
    print(f"\nAWS_ROLE_ARN={role_arn}")


if __name__ == "__main__":
    sys.exit(main())
