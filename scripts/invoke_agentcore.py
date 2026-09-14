"""Invoke the deployed Bedrock AgentCore runtime through the data plane.

Example:
    AWS_PROFILE=flyweight-agentcore .venv/bin/python scripts/invoke_agentcore.py \
        --runtime-arn arn:aws:bedrock-agentcore:us-east-1:032529260721:runtime/flyweight_lab-k3JItG63s2

    AWS_PROFILE=flyweight-agentcore .venv/bin/python scripts/invoke_agentcore.py \
        --runtime-arn <arn> --payload '{"mode":"agent","prompt":"surface one decision"}'
"""

from __future__ import annotations

import argparse
import json
import sys

import boto3


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-arn", required=True)
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--payload", default="{}")
    parser.add_argument("--content-type", default="application/json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    client = boto3.client("bedrock-agentcore", region_name=args.region)
    response = client.invoke_agent_runtime(
        agentRuntimeArn=args.runtime_arn,
        contentType=args.content_type,
        accept=args.content_type,
        payload=args.payload.encode("utf-8"),
    )
    print("statusCode:", response.get("statusCode"))
    body = response.get("response")
    if body is not None:
        data = body.read() if hasattr(body, "read") else body
        if isinstance(data, bytes):
            data = data.decode("utf-8")
        try:
            print(json.dumps(json.loads(data), ensure_ascii=False, indent=2))
        except json.JSONDecodeError:
            print(data)
    print("runtimeSessionId:", response.get("runtimeSessionId"))


if __name__ == "__main__":
    sys.exit(main())
