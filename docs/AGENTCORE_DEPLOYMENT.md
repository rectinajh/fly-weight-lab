# AgentCore Deployment — Fly Weight-Lab

> Status: a real Amazon Bedrock AgentCore Runtime is deployed to AWS, is
> `READY`, and has been invoked through the data plane returning real swarm
> results. Nothing in this document is aspirational.

## 1. Why AgentCore

Hackathon judging for Technical Implementation looks for an agent that is
actually deployed to Amazon Bedrock AgentCore Runtime rather than only running
as a local script. AgentCore gives us:

- The standard runtime contract: `POST /invocations` and `GET /ping`.
- Managed execution, auth, metrics, tracing, and session management.
- First-class integration with the Strands Agents SDK.

## 2. What this repository already contains

- `agentcore/main.py` — `BedrockAgentCoreApp` entrypoint wrapping the swarm and
  the Strands agent.
- Default local mode: `POST /invocations` with `{}` runs the swarm directly.
- Demo/business mode: `{"mode":"demo","user_id":"..."}` runs the real-data
  product loop. With no `weight_records` supplied it loads the preloaded real
  Fitbit users baked into the image.
- Optional model mode: `{"mode":"agent","prompt":"..."}` runs the Strands
  tool-call loop (deterministic MockModel by default).
- `flylab/strands_agent.py` — Strands tools: `get_user_context`,
  `detect_plateau`, `simulate_candidate`, `evolve_champion`,
  `run_background_loop`, `emit_decision`, `record_feedback`.
  Live `mode=demo` runs this loop.
- `requirements-strands.txt` — `strands-agents>=1.55`.
- `requirements-agentcore.txt` — `bedrock-agentcore>=1.23`.
- `Dockerfile` — `linux/arm64` container image on port 8080.
- `scripts/setup_agentcore_role.py` — create the runtime execution role.
- `scripts/deploy_agentcore.py` — build, push to ECR, create or update the
  runtime, then wait for `READY`.
- `scripts/invoke_agentcore.py` — invoke the deployed runtime from the CLI.

Local verification without AWS credentials:

```text
GET  /ping            -> 200 {"status":"Healthy", ...}
POST /invocations {}  -> 200 {"mode":"local","champion":{...},"fitness":..., ...}
```

## 3. Prerequisites

- Python 3.10+
- An AWS account with usable credentials (IAM, SSO, or environment variables)
- Bedrock model access if you enable the model-driven path
- Docker (or Finch/Podman) for local container builds
- Node.js only if you use the official AgentCore CLI

## 4. Deploy with the repository scripts (verified path)

Create the runtime execution role once:

```bash
AWS_PROFILE=flyweight-agentcore .venv/bin/python scripts/setup_agentcore_role.py
```

The role trusts `bedrock-agentcore.amazonaws.com` and carries a least-privilege
inline policy for ECR image pull, CloudWatch Logs, X-Ray, CloudWatch metrics,
Bedrock model invocation, and the AgentCore memory/identity actions the runtime
needs.

Then build, push, and deploy:

```bash
export AWS_PROFILE=flyweight-agentcore
export AGENTCORE_ROLE_ARN=arn:aws:iam::032529260721:role/flyweight-agentcore-runtime-role
export AWS_REGION=us-east-1
.venv/bin/python scripts/deploy_agentcore.py
```

Notes:

- The script derives the account ID from STS and the region from the boto3
  session, or you can set `AWS_REGION` and `AWS_ACCOUNT_ID` explicitly.
- If `docker buildx` is unavailable it falls back to
  `docker build --platform linux/arm64`.
- The script is idempotent: if a runtime with the same name exists it issues
  `update_agent_runtime` and waits for the new version to reach `READY`.
- The runtime name must match `[a-zA-Z][a-zA-Z0-9_]{0,47}`, which is why the
  agent is named `flyweight_lab` and not `fly-weight-lab`.

## 4a. Deployed runtime (current)

| Field | Value |
|---|---|
| Runtime ARN | `arn:aws:bedrock-agentcore:us-east-1:032529260721:runtime/flyweight_lab-k3JItG63s2` |
| Runtime ID | `flyweight_lab-k3JItG63s2` |
| Version / status | `4` · `READY` |
| Image | `032529260721.dkr.ecr.us-east-1.amazonaws.com/fly-weight-lab-agent:latest` |
| Protocol | `HTTP` |
| Network | `PUBLIC` |
| Execution role | `arn:aws:iam::032529260721:role/flyweight-agentcore-runtime-role` |

Verified through the AgentCore data plane:

```text
POST /invocations (payload {})
-> 200 {"mode":"local","champion":{...},"fitness":53.872,"adherence":0.607,"safety":{...}}
```

The `/invocations` and `/ping` entrypoints and the real swarm computation run
inside the managed cloud runtime, not in a local mock.

Invoke it directly from a terminal:

```bash
AWS_PROFILE=flyweight-agentcore .venv/bin/python scripts/invoke_agentcore.py \
  --runtime-arn arn:aws:bedrock-agentcore:us-east-1:032529260721:runtime/flyweight_lab-k3JItG63s2
```

## 4b. Browser access through the Vercel edge proxy

The browser cannot SigV4-sign an AgentCore call, so the Vercel project ships two
serverless functions:

| Function | Responsibility |
|---|---|
| `web/api/invocations.js` | Forward `/api/invocations` to `InvokeAgentRuntime` |
| `web/api/ping.js` | Control-plane `GetAgentRuntime` health check |

Live demo: https://fly-weight-lab-demo.vercel.app

### Authentication: Vercel ↔ AWS OIDC

The proxy does not use long-lived AWS access keys. It uses
`@vercel/oidc-aws-credentials-provider` to exchange the Vercel OIDC token for
short-lived STS credentials via `sts:AssumeRoleWithWebIdentity`.

Production environment variables on the Vercel project (values live in Vercel,
never in the repository):

| Variable | Value |
|---|---|
| `AWS_ROLE_ARN` | `arn:aws:iam::032529260721:role/flyweight-vercel-oidc-role` |
| `AWS_REGION` | `us-east-1` |
| `AGENTCORE_RUNTIME_ARN` | the runtime ARN above |
| `AGENTCORE_RUNTIME_ID` | `flyweight_lab-k3JItG63s2` |

The OIDC side is created by
[`scripts/setup_vercel_oidc_role.py`](../scripts/setup_vercel_oidc_role.py):

| Field | Value |
|---|---|
| Issuer | `https://oidc.vercel.com/rectinajhs-projects` |
| Audience | `https://vercel.com/rectinajhs-projects` |
| Trusted subjects | `project:fly-weight-lab` and `project:web`, production only |
| Permissions | `bedrock-agentcore:InvokeAgentRuntime` and `bedrock-agentcore:GetAgentRuntime`, scoped to the runtime ARN and its `runtime-endpoint/*` resources |

The permission list matters: `InvokeAgentRuntime` via the default endpoint needs
the `runtime-endpoint/DEFAULT` sub-resource, so granting only the bare runtime
ARN fails. The script grants both.

## 4c. GitHub-triggered deploys

The Vercel project wired to GitHub is `fly-weight-lab`. It is configured with:

| Setting | Value |
|---|---|
| Root Directory | `web` |
| Framework Preset | `Other` |
| Build / Output / Install | auto-detected |

With that configuration every push to `main` rebuilds the real frontend (static
page plus the `web/api/*` serverless proxy). The project also carries the four
production environment variables listed above.

> Pitfall worth recording: if the Root Directory stays at the repository root
> while the Framework Preset is `Python`, Vercel tries to find a Python
> entrypoint and the build fails with `No python entrypoint found`. That failure
> is reported back to GitHub as a red commit status, which looks like a broken
> CI pipeline but is actually a deployment misconfiguration. GitHub Actions was
> green the whole time.

## 5. Manual path: ECR plus CreateAgentRuntime

AgentCore Runtime requires:

- Platform `linux/arm64`
- Port `8080`
- `POST /invocations` and `GET /ping`
- An image pushed to ECR

`BedrockAgentCoreApp` provides both routes automatically, so the remaining work
is build, push, and create. After deployment you can invoke it directly:

```json
{
  "prompt": "Detect a plateau and surface the one decision for this user."
}
```

## 6. Auth and security

- Least-privilege IAM roles only.
- No AWS credentials in code or in the repository.
- Vercel authenticates with short-lived OIDC credentials, not static keys.
- Health guidance keeps a safety floor and a medical boundary at the
  application layer; it is not a diagnosis or a prescription.
- Local `.env` files are ignored by `.gitignore`.

## 7. Local verification without AWS

```bash
.venv/bin/python -c "import agentcore; print(agentcore.app.handlers)"
```

Triggering a model call does reach Bedrock, so credentials and model access are
required for that path only.
