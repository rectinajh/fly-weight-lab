# Agents for Humans: Building a Cyber Fruit-Fly Swarm on Amazon Bedrock AgentCore

**How Fly Weight-Lab evolves a personalized weight-loss protocol in the
background and surfaces exactly one decision at a time.**

Every weight-loss app I have used asks the same thing of me: be the experiment.
Log the food, step on the scale, wait three weeks, discover it did not work, and
try again. The failure is not a knowledge problem. It is a bandwidth problem. I
have exactly one body, so I can only run one protocol at a time, and each failed
run costs weeks of momentum.

Fruit flies solved this problem for biology a century ago. *Drosophila* is
cheap, breeds fast, and dies harmlessly, so researchers can run thousands of
genetic experiments that would be impossible on a human. That is the idea I
wanted to port to software: **a swarm of disposable digital twins that absorbs
the cost of failure, so a real person only ever runs the protocol that survived.**

That project is Fly Weight-Lab, and this is the build story — including the four
bugs that taught me the most, all of them found by actually deploying to Amazon
Bedrock AgentCore rather than demoing from a laptop.

![Fly Weight-Lab live demo hero](https://raw.githubusercontent.com/rectinajh/fly-weight-lab/main/assets/fly_weight_lab_hero.png)

## What it does

1. **It builds a behavioral digital twin of one person** from their real logs —
   how *their* weight, adherence, and binge triggers behave.
2. **It breeds a swarm of candidate protocols.** Each fly is a genotype: calorie
   target, protein split, eating window, late-night rule, training, sleep,
   refeed cadence, step target.
3. **It culls and converges.** Flies that would cause a plateau, a binge, or a
   dropout go red and die. Survivors breed, cross over, and mutate.

Then it stays quiet. The agent reruns in the background and surfaces **one
decision**, only when there is something real to decide:

> *"Switch to this protocol this week: lower your daily calorie target from 1,700
> to 1,686 kcal and keep a fixed late-night snack."*

That last part is the whole point. The hackathon theme is agents that run
autonomously and only interrupt when there is a real decision. A weight-loss
experiment has weeks of noise between every real decision, which makes it a
perfect fit.

![Swarm evolution dashboard with convergence radar and culled population](https://raw.githubusercontent.com/rectinajh/fly-weight-lab/main/assets/fly_weight_lab_dashboard.png)

The radar sweeps generation by generation while best fitness spirals inward
toward the champion. Below it, each row in the population farm is one generation:
green survived, red was culled. The full page is
[here](https://raw.githubusercontent.com/rectinajh/fly-weight-lab/main/assets/fly_weight_lab_dashboard_full.png).

## The AWS architecture

```text
Browser (static frontend + canvas visuals)
   │  fetch /api/ping, /api/invocations
   ▼
Vercel Serverless Functions
   │  Vercel OIDC  →  sts:AssumeRoleWithWebIdentity
   │  SigV4
   ▼
Amazon Bedrock AgentCore Runtime        (HTTP, PUBLIC)
   ├── GET  /ping
   ├── POST /invocations   local swarm · real-data flow · Strands agent
   └── POST /business-flow direct container route
   ▲
   │  linux/arm64 image, port 8080
Amazon ECR
```

| Service | How it is used |
|---|---|
| Amazon Bedrock AgentCore Runtime | Hosts the agent container; provides the `/invocations` and `/ping` contract, managed scaling, sessions, and tracing |
| Amazon ECR | Stores the `linux/arm64` container image |
| AWS IAM | A runtime execution role for the container, plus a narrowly scoped role for the edge proxy |
| AWS STS | `AssumeRoleWithWebIdentity` so the frontend never needs static keys |
| Amazon CloudWatch | Runtime logs and the `bedrock-agentcore` metric namespace |
| AWS X-Ray | Trace segments from the runtime |
| Amazon Bedrock models | Optional model-driven path via `InvokeModel` / `InvokeModelWithResponseStream` |

The swarm math itself is plain Python and NumPy, which keeps the container small
and the runtime cheap. Bedrock is used for the model-driven reasoning path.

## Grounding the metaphor in real biology

I did not want the fruit fly to be a sticker on a tracker. The binge-risk model
uses the real Janelia MaleCNS mushroom body as a structural prior:

| Measure | Value |
|---|---|
| Kenyon cells (context) | 4,064 |
| Dopaminergic neurons (reward / punishment) | 340 |
| MBONs (decision) | 97 |
| KC → MBON convergence | 631 KCs per MBON |
| Reward (PAM) : punishment (PPL) weight | **2.56 : 1** |

That ratio is load-bearing. Dieting leans on punishment — restriction — but the
measured circuit says reward outweighs punishment. So the model predicts that
restriction gets answered with disproportionate craving pressure, and an
aggressive plan's simulated binge risk jumps once the real wiring is applied.
This is a prior for habit and reward dynamics, not a claim that a human brain is
a fly brain, and I am explicit about that boundary.

## Four bugs that only a real deployment finds

### 1. My "deterministic" solver was not deterministic

Each fly is scored by simulating a future. I seeded the simulation from the fly's
genotype — using Python's built-in `hash()` on a string. That hash is salted per
process, so the same fly got a different future on every run, and the fitness
ranking silently shuffled. The fix is a stable digest:

```python
def _fly_seed(fly: Fly) -> int:
    """Return a process-stable seed for a fly's genotype."""
    digest = hashlib.sha1(repr(fly.key()).encode("utf-8")).hexdigest()
    return int(digest, 16) % (2**31)
```

This is the kind of bug that never shows up in a single-process demo and quietly
ruins any comparison the moment you reproduce a run.

### 2. AgentCore runtime names reject hyphens

`CreateAgentRuntime` validates the name against
`[a-zA-Z][a-zA-Z0-9_]{0,47}`. My natural choice, `fly-weight-lab`, failed
immediately:

```text
ValidationException: Value 'fly-weight-lab' at 'agentRuntimeName' failed to
satisfy constraint: Member must satisfy regular expression pattern:
[a-zA-Z][a-zA-Z0-9_]{0,47}
```

Renaming the runtime to `flyweight_lab` was trivial. Recording it here because
the error is unambiguous and the fix costs thirty seconds — but only if you read
it instead of guessing.

### 3. Invoking a runtime needs a sub-resource permission

This one is subtle. I scoped the edge role's `InvokeAgentRuntime` permission to
the runtime ARN only. The call failed with an AccessDenied that named a resource
I had not expected:

```text
not authorized to perform: bedrock-agentcore:InvokeAgentRuntime on resource:
arn:aws:bedrock-agentcore:us-east-1:...:runtime/flyweight_lab-k3JItG63s2/runtime-endpoint/DEFAULT
```

Invoking through the default endpoint needs the `runtime-endpoint/*`
sub-resource as well. The fix:

```json
{
  "Sid": "InvokeAgentRuntime",
  "Effect": "Allow",
  "Action": "bedrock-agentcore:InvokeAgentRuntime",
  "Resource": [
    "arn:aws:bedrock-agentcore:us-east-1:<account>:runtime/<runtime-id>",
    "arn:aws:bedrock-agentcore:us-east-1:<account>:runtime/<runtime-id>/*"
  ]
}
```

The lesson I keep re-learning: when IAM denies you, read the ARN in the error
message. It tells you exactly which resource shape to grant.

### 4. The "failing CI" that was actually a Vercel misconfiguration

GitHub showed a red failure on every push, which looked like a broken pipeline.
The Actions workflow was green the whole time. The failure was a Vercel
deployment status posted back to the commit: the repository-root Vercel project
was configured with the `Python` framework preset and the root as its base
directory, so the build died with:

```text
Error: No python entrypoint found in default locations, but found potential
entrypoints:
agentcore/__init__.py (variable: app)
agentcore/main.py (variable: app)
```

Vercel was trying to deploy my backend as a Python function because it found
Python files. Pointing that project's Root Directory at `web` and setting the
framework preset to `Other` made it build the actual frontend, and the commit
status went green.

## Wiring the browser to AgentCore without shipping static keys

A browser cannot SigV4-sign an AgentCore call, so the frontend needs an edge
proxy. I added two serverless functions (`/api/invocations` and `/api/ping`) and
then removed the long-lived AWS access keys entirely.

The proxy authenticates with Vercel's OIDC identity provider:

```javascript
const { awsCredentialsProvider } = require("@vercel/oidc-aws-credentials-provider");

const client = new BedrockAgentCoreClient({
  region: process.env.AWS_REGION,
  credentials: awsCredentialsProvider({ roleArn: process.env.AWS_ROLE_ARN }),
});
```

The AWS side trusts `oidc.vercel.com/<team>` and is scoped hard: production only,
specific Vercel projects, and only two AgentCore actions against one runtime.

```json
{
  "Effect": "Allow",
  "Principal": {
    "Federated": "arn:aws:iam::<account>:oidc-provider/oidc.vercel.com/<team>"
  },
  "Action": "sts:AssumeRoleWithWebIdentity",
  "Condition": {
    "StringLike": {
      "oidc.vercel.com/<team>:sub": [
        "owner:<team>:project:fly-weight-lab:environment:production",
        "owner:<team>:project:web:environment:production"
      ]
    },
    "StringEquals": {
      "oidc.vercel.com/<team>:aud": "https://vercel.com/<team>"
    }
  }
}
```

The result is short-lived credentials, no rotation chore, and no static key that
can leak from an environment variable.

## Deploying the agent

The whole runtime is a small `linux/arm64` image on port 8080 exposing
`/invocations` and `/ping`. Deployment is idempotent — it creates the runtime the
first time and updates it afterwards, then waits for `READY`:

```bash
export AWS_PROFILE=flyweight-agentcore
export AWS_REGION=us-east-1
export AGENTCORE_ROLE_ARN=arn:aws:iam::<account>:role/flyweight-agentcore-runtime-role

.venv/bin/python scripts/deploy_agentcore.py
```

The execution role is least-privilege: ECR image pull, CloudWatch Logs, X-Ray,
CloudWatch metrics in the `bedrock-agentcore` namespace, Bedrock model
invocation, and the AgentCore memory and identity actions the runtime needs.

Verified against the live runtime:

```text
POST /invocations  {}
-> 200 {"mode":"local","champion":{...},"fitness":53.872,"adherence":0.607,...}
```

## Using real data instead of a happy-path demo

The demo does not ship with invented rows. It uses a normalized slice of a
public Fitbit dataset (Zenodo `10.5281/zenodo.53894`, CC-BY-4.0), and two real
users are baked into the container image so nobody has to upload a CSV to see
the real flow. The weight trajectory and volatility drive the twin; step counts
and active minutes ground the activity context.

I am careful about one thing here: a weight log cannot prove someone followed a
diet. So when there is no explicit adherence data, the model keeps adherence as
an explicitly neutral prior rather than pretending the logging cadence proves
consistency.

## What judges can check

![Full dashboard, top to bottom](https://raw.githubusercontent.com/rectinajh/fly-weight-lab/main/assets/fly_weight_lab_dashboard_full.png)

| Check | Result |
|---|---|
| AgentCore Runtime | deployed, version 4, `READY` in `us-east-1` |
| Data-plane invocation | `200` with real swarm output |
| Live demo | runs the real flow with no local backend |
| Test suite | 14 tests covering genotype, swarm, connectome, background loop, calibration, safety, memory, evals, Strands loop |
| GitHub Actions | green on `main` |
| Vercel production deploy | green on `main` |

## What I would build next

- Swap the deterministic mock model for a real Bedrock model to narrate the
  surfaced decision in the user's own words.
- Move state from JSON snapshots into DynamoDB so multiple users can each hold a
  long-running experiment.
- Add AgentCore Memory so the twin remembers a user's history across sessions
  without shipping the whole log every call.
- Let the twin refit inside the runtime on a schedule instead of on each request.

## Closing thought

The fruit fly is not a mascot here. It is a strategy: make failure cheap enough
that you can afford to be wrong many times, and let only the survivors reach a
body that cannot afford to fail.

**Your body runs one experiment. The flies run ten thousand.**

---

**Links**

- Live demo: https://fly-weight-lab-demo.vercel.app
- Source: https://github.com/rectinajh/fly-weight-lab
- Implementation status: https://github.com/rectinajh/fly-weight-lab/blob/main/docs/IMPLEMENTATION_STATUS.md
- AgentCore deployment guide: https://github.com/rectinajh/fly-weight-lab/blob/main/docs/AGENTCORE_DEPLOYMENT.md

`#AgentsforHumans` `#AmazonBedrock` `#AgentCore` `#StrandsAgents`

<!-- POST ENDS HERE — everything below is publishing notes, not part of the article -->

---

## Publishing notes (do not paste this section)

**Where:** https://builder.aws.com — build a new post, paste everything above the
comment marker, upload the three images, publish publicly.

**Images to upload** (in the order they appear):

| File | Kind | Suggested caption |
|---|---|---|
| `assets/fly_weight_lab_hero.png` | hero (1600×1000) | Fly Weight-Lab live demo: real connectome wiring, live AgentCore health, preloaded real users |
| `assets/fly_weight_lab_dashboard.png` | inline (1600×1000) | Swarm evolution: convergence radar, best vs. mean fitness, culled population farm |
| `assets/fly_weight_lab_dashboard_full.png` | inline (1200×2699) | Full dashboard: weight trajectory, background-agent timeline, champion protocol, one surfaced decision, two-user comparison |

The image links in the article point at `raw.githubusercontent.com` so the
markdown renders even before you upload anything. Replace them with the
builder.aws CDN URLs after upload if you prefer.

**Alternate titles** (all contain "Agents for Humans"):

1. Agents for Humans: Letting Ten Thousand Cyber Fruit Flies Fail So You Only Run One Diet
2. Agents for Humans: A Fruit-Fly Swarm That Runs Your Weight-Loss Experiments on Amazon Bedrock AgentCore
3. Agents for Humans: One Decision at a Time, Backed by Ten Thousand Simulated Failures

**Submission checklist:**

- [ ] Title contains the exact phrase "Agents for Humans".
- [ ] Post is published publicly on builder.aws.com (not a draft).
- [ ] Published before the submission deadline, and the public URL pasted into
      the Devpost submission.
- [ ] Live demo link and repository link verified from a logged-out browser.
- [ ] Images uploaded and loading, not just referenced from GitHub.

**Second post ideas** (the rules allow more than one):

1. A deep dive on least-privilege AgentCore access: runtime execution roles plus
   Vercel ↔ AWS OIDC federation, with the `runtime-endpoint/DEFAULT` gotcha.
2. A short post on determinism in evolutionary search: why Python's salted
   `hash()` silently broke fitness reproducibility and what to do instead.
