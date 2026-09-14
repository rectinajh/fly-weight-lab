# Implementation Status

Snapshot of what is actually built, deployed, and verified. Everything below
was run against the live services, not sketched on a slide.

## Live endpoints

| Surface | URL |
|---|---|
| Public demo | https://fly-weight-lab-demo.vercel.app |
| Git-connected production | https://fly-weight-lab.vercel.app |
| Health check | `GET /api/ping` → `{"status":"Healthy"}` |
| Agent invocation | `POST /api/invocations` → real AgentCore result |

## Deployed AWS Bedrock AgentCore Runtime

| Field | Value |
|---|---|
| Runtime ARN | `arn:aws:bedrock-agentcore:us-east-1:032529260721:runtime/flyweight_lab-k3JItG63s2` |
| Runtime ID | `flyweight_lab-k3JItG63s2` |
| Version / status | `4` · `READY` |
| Region | `us-east-1` |
| Container image | `032529260721.dkr.ecr.us-east-1.amazonaws.com/fly-weight-lab-agent:latest` |
| Protocol / network | `HTTP` · `PUBLIC` |
| Execution role | `arn:aws:iam::032529260721:role/flyweight-agentcore-runtime-role` |

Verified through the Bedrock AgentCore data plane:

```text
POST /invocations  {}
  -> 200 {"mode":"local","champion":{...},"fitness":53.872,"adherence":0.607,"safety":{...}}

POST /invocations  {"mode":"demo","user_id":"6962181067","population_size":250,"generations":25}
  -> 200 with real calibration, evolution history, champion, surfaced decision, feedback

POST /invocations  {"mode":"agent","prompt":"..."}
  -> 200 with a completed Strands tool-call loop
```

The swarm math runs inside the managed AgentCore container. There is no local
backend in the demo path.

## Frontend and edge proxy

The browser cannot SigV4-sign an AgentCore call, so the Vercel project ships two
serverless functions that proxy to AWS:

| Function | Responsibility |
|---|---|
| `web/api/ping.js` | Control-plane `GetAgentRuntime` health check |
| `web/api/invocations.js` | Data-plane `InvokeAgentRuntime` for every demo mode |

Both use the Vercel ↔ AWS OIDC federation (`@vercel/oidc-aws-credentials-provider`)
so no long-lived AWS keys are stored on Vercel.

The UI itself is a dependency-free static page with three canvas visualizations:

1. A cyber fruit-fly swarm that periodically dives with glowing trails and
   scatters away from the pointer.
2. A sonar-style convergence radar where best fitness spirals inward toward the
   champion while the sweep rotates.
3. A real-connectome view that wires 4,064 Kenyon cells through 340 DANs into
   97 MBONs with flowing signal particles.

Dashboard cards render the swarm evolution, the real weight trajectory, the
background-agent timeline, the champion protocol, the single surfaced decision,
the calibration and safety gauges, and a two-user personalization comparison.
All copy is English.

## Two real Fitbit users are preloaded

The demo no longer asks a user to upload a CSV. Two real Fitbit users ship
inside the container image under `data/real_users/`:

| User | Weight rows | Activity rows |
|---|---|---|
| `6962181067` | 14 | 14 |
| `8877689391` | 9 | 12 |

CSV upload is still available as an optional "bring your own export" path.

## Real connectome grounding

Loaded from `data/mb_summary.json`, built from the Janelia MaleCNS v1.0
mushroom body:

| Measure | Value |
|---|---|
| Kenyon cells (context) | 4,064 |
| Dopaminergic neurons (reward/punishment) | 340 |
| MBONs (decision) | 97 |
| KC → MBON convergence | 631 KCs per MBON |
| DAN → MBON modulation | 32.6 DANs per MBON |
| Reward (PAM) : punishment (PPL) weight | 2.56 : 1 |

The reward-to-punishment ratio is used as a structural prior in the binge-risk
coupling, so restriction is modelled as triggering disproportionate craving
pressure rather than being a hand-tuned constant.

## Verification

| Check | Status |
|---|---|
| `python -m unittest discover -s tests -v` | 14 tests pass |
| GitHub Actions `ci` workflow | passing on `main` |
| Vercel production deploy check | passing on `main` |
| Live `/api/ping` on both domains | `Healthy` |
| Live demo flow through AgentCore | returns real decision, not a mock |

## Retrieval and reproduction

```bash
# build + deploy the runtime (idempotent: updates when it already exists)
AWS_PROFILE=flyweight-agentcore \
AGENTCORE_ROLE_ARN=arn:aws:iam::032529260721:role/flyweight-agentcore-runtime-role \
AWS_REGION=us-east-1 \
.venv/bin/python scripts/deploy_agentcore.py

# invoke the deployed runtime directly
AWS_PROFILE=flyweight-agentcore .venv/bin/python scripts/invoke_agentcore.py \
  --runtime-arn arn:aws:bedrock-agentcore:us-east-1:032529260721:runtime/flyweight_lab-k3JItG63s2

# create the runtime execution role and the Vercel OIDC role
AWS_PROFILE=flyweight-agentcore .venv/bin/python scripts/setup_agentcore_role.py
AWS_PROFILE=flyweight-agentcore .venv/bin/python scripts/setup_vercel_oidc_role.py
```

## Known limitations

- The behavioral twin is a transparent parametric model, not a learned
  production model. It is honest about being a behavior model rather than a
  metabolic simulator.
- The two preloaded users have short histories (1–3 weekly checkpoints), so the
  background-agent timeline is short in the live demo.
- Preview deployments are not part of the OIDC trust policy; only production
  deployments can assume the AWS role.
- Model-driven mode defaults to a deterministic offline MockModel. Point
  `STRANDS_MODEL_PROVIDER` at Ollama, OpenAI, Anthropic, or Bedrock to use a real
  model.
