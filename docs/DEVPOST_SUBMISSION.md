# Devpost submission copy — Fly Weight-Lab

Paste-ready text for the Agents for Humans submission form. Each heading matches
the field on Devpost.

---

## Inspiration

Every weight-loss tool I have used asks the same thing of me: be the experiment.
Log the food, step on the scale, wait three weeks, find out it did not work, and
start over. The failure is almost never a knowledge problem. It is a bandwidth
problem. I have exactly one body, so I can only run one protocol at a time, and
every failed run costs weeks of momentum plus one more round of "I guess I just
have no willpower."

Biology solved this problem a century ago with the fruit fly. *Drosophila* is
cheap, breeds fast, and dies harmlessly, so researchers can run thousands of
genetic experiments that would be impossible on a human, then carry the
surviving principles back. That is the idea I wanted to make digital: a swarm of
disposable twins that absorbs the cost of failure, so a real person only ever
runs the version that survived.

The hackathon theme closed the loop. "Agents for Humans" asks for agents that
take the busywork and the emotional weight, and that run autonomously while only
surfacing when there is a real decision. Weight loss is exactly that shape: weeks
of noise between a handful of decisions that actually matter. Most apps fill that
gap with notifications. I wanted an agent that fills it with computation and
stays quiet.

## What it does

Fly Weight-Lab is an agent that works in the background and only interrupts you
when there is a real decision to make.

1. **It builds a behavioral digital twin of you.** Not a metabolic simulator — a
   model of how *your* weight, adherence, and binge triggers behave, fitted from
   your real logs.
2. **It breeds a swarm of candidate protocols.** Each fly is a genotype: calorie
   target, protein split, eating window, late-night rule, training, sleep, refeed
   cadence, step target. Each fly is run through thousands of simulated futures
   against your twin.
3. **It culls and converges.** Flies that would cause a plateau, a binge, or a
   dropout go red and die. Survivors breed, cross over, and mutate until one
   champion remains.
4. **It surfaces exactly one decision.** Something like *"Switch to this
   protocol this week: lower your daily calorie target from 1,700 to 1,686 kcal
   and keep a fixed late-night snack"* — one action, one reason. Then it goes
   quiet again.

Two real Fitbit users are preloaded into the deployed runtime, so the live demo
runs the entire real flow with no CSV upload and no local backend. The demo is
English, fully animated, and shows the swarm converging, the real weight
trajectory, the weeks the agent spoke versus stayed silent, the champion
protocol, the surfaced decision, and a two-user comparison.

The agent is also grounded in a real brain. The binge-risk model uses the
measured Janelia MaleCNS mushroom body: 4,064 Kenyon cells, 340 reward and
punishment neurons, 97 decision neurons, and a reward-to-punishment weight ratio
of 2.56 to 1. Dieting leans on restriction, which is punishment, so the real
circuit predicts restriction gets answered with disproportionate craving
pressure — and the aggressive plan's simulated binge risk rises accordingly.

Live demo: https://fly-weight-lab-demo.vercel.app
Source: https://github.com/rectinajh/fly-weight-lab

## How we built it

**The engine (Python + NumPy).** `flylab/genotype.py` encodes a protocol as a
genotype. `flylab/fitness.py` scores it on a *sustainable loss band* rather than
pure maximization, so the swarm cannot crown either a do-nothing plan or a crash
diet, and adherence carries the heaviest weight. `flylab/evolution.py` runs
tournament selection with elitism, uniform crossover, and per-gene mutation.
`flylab/twin.py` is the behavioral twin, and `flylab/agent_loop.py` is the
background agent: it ingests a weekly weight, reruns the swarm, fingerprints the
champion to detect real change, detects plateaus, and only calls the decision
surface when something genuinely changed.

**Real data, not sample rows.** `scripts/ingest_fitbit_data.py` downloads the
CC-BY-4.0 Fitbit dataset from Zenodo (`10.5281/zenodo.53894`) and normalizes the
small per-user weight and activity files into `data/real_users/`.
`flylab/business_flow.py` runs the full product loop over real weekly
checkpoints: calibrate the twin, run background ticks, surface one decision, then
record the real next-week outcome into durable memory.

**Strands Agents SDK.** The agent layer exposes six narrow tools —
`get_user_context`, `detect_plateau`, `simulate_candidate`, `evolve_champion`,
`surface_decision`, `record_feedback` — so the model composes capabilities
instead of calling one black-box function. The default path uses a deterministic
MockModel, which runs a complete tool-call loop with no API key; switching to
Ollama, OpenAI, Anthropic, or Bedrock is one environment variable.

**Amazon Bedrock AgentCore.** `agentcore/main.py` wraps everything in
`BedrockAgentCoreApp`, which gives us the standard `/invocations` and `/ping`
contract. The container is a `linux/arm64` image on port 8080 pushed to ECR.
`scripts/deploy_agentcore.py` builds it, pushes it, creates the runtime the first
time and updates it afterwards, and waits for `READY`. The runtime execution role
is least-privilege: ECR pull, CloudWatch Logs, X-Ray, CloudWatch metrics, Bedrock
model invocation, and the AgentCore memory and identity actions.

**The frontend and the edge.** A browser cannot SigV4-sign an AgentCore call, so
the Vercel site ships two serverless functions: one forwards `/api/invocations`
to `InvokeAgentRuntime`, and one does a real health check via the control-plane
`GetAgentRuntime`. The static UI is dependency-free and hand-draws its charts in
SVG and canvas: a squad of cyber flies that periodically dive with glowing
trails, a sonar-style radar where best fitness spirals inward toward the
champion, and a live wiring diagram of the connectome. Authentication is Vercel ↔
AWS OIDC federation, so there are no long-lived AWS keys anywhere.

**Verification.** 15 unit tests cover the genotype, the swarm, connectome
grounding, the background loop's quietness, calibration, safety, memory, offline
evaluation, the Strands tool-call loop, and the requirement that the two
preloaded users actually diverge. GitHub Actions runs them on every push, and the
Vercel production deploy is green.

## Challenges we ran into

**Our "deterministic" simulation was not deterministic.** Each fly's simulated
future was seeded with Python's built-in `hash()` on a string, which is salted
per process. The same fly got a different future every run and the fitness
ranking silently reshuffled. We replaced it with a stable SHA-1 digest of the
genotype, so the same fly always receives the same future. This was the single
most important bug we fixed: nothing you show a judge is trustworthy if you
cannot reproduce it.

**AgentCore runtime names reject hyphens.** `CreateAgentRuntime` enforces
`[a-zA-Z][a-zA-Z0-9_]{0,47}`, so `fly-weight-lab` fails validation outright. The
runtime is now `flyweight_lab`.

**Invoking a runtime needs a sub-resource permission.** We scoped the edge role
to the runtime ARN, and the call was denied for a resource we had not anticipated:
`.../runtime/<id>/runtime-endpoint/DEFAULT`. Invoking through the default endpoint
requires the endpoint sub-resource too. The lesson: read the ARN in the IAM error
message — it tells you exactly which resource shape to grant.

**Removing long-lived keys took more than deleting an environment variable.**
The first working version of the proxy used an access key stored in Vercel. We
replaced it with OIDC federation to `sts:AssumeRoleWithWebIdentity`, then scoped
the trust policy to production environments of two specific Vercel projects and
limited the permissions to two AgentCore actions on one runtime.

**The "broken CI" that was not CI.** GitHub showed a red failure on every push.
GitHub Actions was green the whole time — the failure was a Vercel deployment
status posted back to the commit. The repository-root Vercel project was set to
the `Python` framework preset, so it tried to deploy our backend as a Python
function and died with `No python entrypoint found`. Pointing that project at the
`web` directory and setting the framework to `Other` turned the commit status
green.

**Resisting the dishonest version.** The tempting pitch is "we simulate your
metabolism." We do not, and we cannot. We model behavior: will this person do it,
and what happens if they do. In the same spirit, a weight-only log cannot prove
someone followed a diet, so when there is no explicit adherence data the model
keeps adherence as an explicitly neutral prior instead of pretending the logging
cadence proves consistency. Being precise here made the product stronger under
questioning, not weaker.

## Accomplishments that we're proud of

- **It is genuinely deployed.** A real Bedrock AgentCore Runtime in `us-east-1`,
  `READY` and invoked through the data plane returning real swarm output — not a
  recorded demo. The live page calls it through a serverless proxy on every
  button press.
- **Two users, same goal, opposite protocols.** The two-user comparison is the
  proof that personalization is real: the binge-prone twin keeps a planned
  late-night snack and a weekly refeed, while the disciplined twin gets a tighter
  calorie target and neither.
- **The agent actually stays quiet.** Across the demo window it surfaces a
  handful of decisions and is silent the rest of the time, because it only speaks
  on a new plateau or a genuine champion change. That behavior is the product,
  and it is visible in the timeline.
- **The metaphor is load-bearing.** The real connectome ratio changes the
  binge-risk model, which changes the champion protocol. It is not decoration.
- **No long-lived AWS credentials anywhere.** OIDC federation, a narrow trust
  policy, and two narrowly scoped permissions on one runtime.
- **Honesty and safety by design.** Hard calorie floors, filtered dangerous
  protocols, and escalation to a clinician instead of a plan when a profile is
  out of scope. The agent never diagnoses and never prescribes.
- **Reproducibility.** 15 tests, deterministic scoring, green CI, and a green
  production deploy on every push.

## What we learned

- **Managed runtimes surface bugs that local demos hide.** Determinism, IAM
  resource shapes, and naming constraints only appear when you actually deploy.
  Every one of our best fixes came from running the real thing.
- **IAM errors are documentation.** The denial names the exact resource ARN you
  forgot. Reading it carefully is faster than guessing at policies.
- **Reproducibility is a prerequisite, not a nicety.** A silently non-deterministic
  scorer invalidates every comparison you might want to present.
- **Honest scoping wins.** Saying "behavioral twin, not metabolic simulator" made
  the project easier to defend and easier to build.
- **A constraint can be a design tool.** "One decision at a time" is not just a
  feature; it forced us to decide what genuinely deserves to interrupt a person.
- **The last 5% of least privilege is where the learning is.** Being broadly
  correct is easy. Scoping to a single runtime and an endpoint sub-resource is
  where you learn how the resource model actually works.

## What's next for fly-weight-lab

- **Let a real model narrate.** Point `STRANDS_MODEL_PROVIDER` at Bedrock so the
  decision is phrased in the user's own context instead of a template, using the
  same six tools.
- **Move state into DynamoDB.** Today the agent persists JSON snapshots; a
  multi-user version wants durable per-user state and long-running experiments.
- **Use AgentCore Memory.** Keep a user's history across sessions without
  resending the whole log on every call.
- **Refit on a schedule inside the runtime.** Right now the twin refits per
  request; a scheduled job would let the swarm run while the user sleeps.
- **Connect real wearables.** Replace CSV import with the Fitbit and Apple Health
  APIs so the twin keeps improving without anyone exporting a file.
- **Learn from accept/reject over longer horizons.** Feed whether a surfaced
  decision was actually kept back into fitness, so the swarm learns what this
  person follows through on.
- **Widen the safety evaluation.** More adversarial profiles, more edge cases,
  and a clinical review before anything resembling real medical use.

**Your body runs one experiment. The flies run ten thousand.**
