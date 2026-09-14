# Fly Weight-Lab

An autonomous AI agent that breeds a swarm of **cyber fruit flies** — cheap,
disposable digital twins — to evolve the one weight-loss protocol that actually
works for *your* body, then surfaces only the single decision worth your
attention.

Built for the **Agents for Humans Hackathon** (AWS × Strands Agents SDK),
**Everyday Agents** track.

> **Your body runs one experiment. The flies run ten thousand.**

## Live demo

**https://fly-weight-lab-demo.vercel.app**

The demo runs a real Amazon Bedrock AgentCore Runtime in `us-east-1`. There is no
local backend and no mock data in the path:

- Two real Fitbit users are preloaded inside the runtime, so **no CSV upload is
  required** — press *Launch background agent* and the real flow runs.
- The Vercel frontend reaches AgentCore through two serverless functions that
  authenticate with **Vercel ↔ AWS OIDC federation**, so no long-lived AWS keys
  are stored anywhere.
- The UI is English and fully animated: a diving fly swarm, a sonar-style
  convergence radar, and a live real-connectome wiring diagram.

Full deployment and verification details live in
[docs/IMPLEMENTATION_STATUS.md](./docs/IMPLEMENTATION_STATUS.md).

## Background

Weight loss is one of the most universal and most frustrating goals in the
world. Hundreds of millions of people attempt it every year, and most fail — not
from a lack of knowledge, but because the feedback is slow, noisy, and deeply
individual.

- A diet takes weeks to show a real signal, and that signal is polluted by water
  weight, plateaus, hormones, and life.
- What works for one person — say, 16:8 fasting — can actively trigger bingeing
  in another.
- You only have one body, so you cannot run 10,000 diet experiments on yourself.
  Every failed attempt costs weeks, momentum, and self-trust.

The fruit fly (*Drosophila melanogaster*) is biology's favorite model organism
for exactly this reason: it is cheap, breeds fast, dies harmlessly, and lets
researchers run thousands of experiments that would be impossible or unethical
on more complex organisms — then transfer the surviving principles back to
humans.

**Fly Weight-Lab is the digital version.** A swarm of cheap, disposable digital
twins absorbs the cost of experimentation on your behalf, so your real body only
ever runs the winning protocol.

## The core problem

Existing weight-loss apps solve the wrong problem. They *track* (food logging),
*remind* (nudges), and *prescribe generic advice* ("cut carbs after 8pm"). None
of them answer the question that actually decides success:

> **Which protocol can *this specific person* actually sustain, and how will
> *their body* respond?**

The result is that people run experiments on themselves in the dark, fail
repeatedly, and conclude "it must be me." It is not them. It is that they have
been running unmodeled, unrepeatable experiments on the one body they cannot
afford to lose.

## The solution

Fly Weight-Lab is an agent that runs quietly **in the background** and does three
things:

1. **Builds a behavioral digital twin of you.** This is not a metabolic
   simulator. It is a model of *your* response — how *your* weight, adherence,
   and binge triggers behave — learned from *your* logged history.
2. **Breeds a swarm of candidate protocols.** Each "fly" carries a genotype:
   calorie target, protein split, meal timing, late-night rule, workout, sleep,
   refeed schedule, step target. It runs each fly through thousands of simulated
   futures using your twin, scoring predicted adherence, weight trajectory, and
   risk of plateau, binge, or dropout.
3. **Evolves and culls.** Selection, crossover, and mutation across generations.
   Flies that would cause a plateau, a binge, or a quit turn red and die. Only
   the surviving champion protocols reach you.

The agent surfaces **one decision at a time**, never a dashboard of five hundred
suggestions:

> *"This week, lock in this single habit."*

## Innovation

1. **From passive tracking to active experimentation.** Every other app observes
   you. This one *runs experiments for you*.
2. **A behavioral digital twin, not a metabolic fantasy.** We simulate *your
   adherence and response*, learned from your own data. That is honest,
   buildable, and defensible under judge scrutiny.
3. **Evolutionary search over protocols, personalized.** The winning plan is
   *bred from your data*, not picked from a template. Two users with the same
   goal can receive opposite, individually correct protocols.
4. **One decision at a time.** The agent runs in the background and surfaces only
   when there is a genuine decision to make — the exact principle this hackathon
   is built around.
5. **Adherence-first fitness.** The swarm optimizes for "what this person will
   actually keep doing," not "what burns the most calories on paper."
6. **A real connectome, used as a prior.** The resting binge-risk coupling comes
   from the measured Janelia mushroom body, not a hand-tuned constant.

## Why build it this way

- **The metaphor is load-bearing, not decorative.** The "spawn → test → breed →
  mutate → cull → converge" loop *is* the product.
- **It answers the judge's killer question.** *"How is this different from
  MyFitnessPal or Noom?"* — They observe and remind. We run ten thousand
  disposable experiments so you only run one, and we surface only the decisions
  that matter.
- **It is honest and buildable.** A behavioral twin learned from real logs is a
  tractable problem; a metabolic simulator is not. We chose the credible path.
- **It hits the theme's core requirement.** The hackathon explicitly wants
  agents that "run autonomously and only surface when there's a real decision."
- **It has a memorable demo.** The winning shot: two users, same goal, the swarm
  converging on *opposite* plans — proving the personalization is real.

## Real connectome grounding

Fly Weight-Lab does not treat the fruit fly as a metaphor alone. The behavioral
twin is grounded in the real *Drosophila* mushroom body from the Janelia MaleCNS
connectome ([male-cns.janelia.org](https://male-cns.janelia.org/)):

| Measure | Value |
|---|---|
| Kenyon cells (context) | 4,064 |
| Dopaminergic neurons (reward/punishment) | 340 |
| MBONs (decision) | 97 |
| KC → MBON convergence | 631 KCs per MBON |
| DAN → MBON modulation | 32.6 DANs per MBON |
| Reward (PAM) : punishment (PPL) weight | 2.56 : 1 |

That last number is load-bearing. Dieting leans on punishment (restriction), but
the real wiring says reward is stronger, so restriction produces disproportionate
craving pressure. The grounded twin therefore rates aggressive diets as riskier
and recommends gentler, sustainable protocols. This is a structural prior for
habit and reward dynamics — not a claim that a human brain equals a fly brain.

## What's shipped

| Area | Status |
|---|---|
| Genetic swarm engine | implemented, deterministic, tested |
| Behavioral twin + calibration | implemented, fits from real CSV logs |
| Background agent loop | implemented with JSON state persistence |
| Real-data business flow | implemented over real Fitbit rows |
| Strands Agents SDK tools | six narrow tools, offline MockModel by default |
| Bedrock AgentCore Runtime | **deployed, `READY`, invoked successfully** |
| Vercel frontend + edge proxy | live, animated, English, OIDC-authenticated |
| Real Fitbit users preloaded | 2 users baked into the container image |
| Safety guardrails | calorie floor, protocol filtering, medical escalation |
| Offline evaluation | plateau detection + personalization scorecard |
| CI | GitHub Actions green; Vercel production deploy green |

Details, evidence, and known limitations:
[docs/IMPLEMENTATION_STATUS.md](./docs/IMPLEMENTATION_STATUS.md).

## Run it

```bash
# one-time setup
python -m venv .venv && .venv/bin/pip install -r requirements-local.txt

# offline swarm run — no model and no AWS needed
.venv/bin/python -m uvicorn agentcore.main:app --host 0.0.0.0 --port 8080

# real-data product loop on a preloaded user
.venv/bin/python scripts/run_business_flow.py --user-id 6962181067

# deploy or update the real AgentCore runtime
AWS_PROFILE=flyweight-agentcore \
AGENTCORE_ROLE_ARN=arn:aws:iam::032529260721:role/flyweight-agentcore-runtime-role \
AWS_REGION=us-east-1 \
.venv/bin/python scripts/deploy_agentcore.py

# invoke the deployed runtime directly
AWS_PROFILE=flyweight-agentcore .venv/bin/python scripts/invoke_agentcore.py \
  --runtime-arn arn:aws:bedrock-agentcore:us-east-1:032529260721:runtime/flyweight_lab-k3JItG63s2
```

Runnable demos:

| Command | What it shows |
|---|---|
| `python examples/demo_plateau_breaker.py` | two users evolve opposite protocols |
| `python examples/demo_connectome.py` | how the real connectome changes the advice |
| `python examples/demo_agent.py` | 12-week background agent that stays quiet |
| `python scripts/ingest_fitbit_data.py` | download and normalize the real Fitbit data |
| `python scripts/run_business_flow.py --user-id 6962181067` | real-data business loop |
| `python scripts/run_evals.py` | offline evaluation scorecard |
| `python scripts/calibrate_twin.py <data.csv>` | fit the twin from real logs |
| `python -m unittest discover -s tests -v` | full test suite (14 tests) |

## Repository layout

| Path | Contents |
|---|---|
| [`docs/IMPLEMENTATION_STATUS.md`](./docs/IMPLEMENTATION_STATUS.md) | what is built, deployed, and verified |
| [`docs/PRD.md`](./docs/PRD.md) | product requirements |
| [`docs/TECHNICAL_DESIGN.md`](./docs/TECHNICAL_DESIGN.md) | architecture and implementation plan |
| [`docs/AGENTCORE_DEPLOYMENT.md`](./docs/AGENTCORE_DEPLOYMENT.md) | AWS deployment, OIDC, and CI setup |
| [`docs/DEMO_STORYBOARD.md`](./docs/DEMO_STORYBOARD.md) | five-minute demo script |
| [`docs/LOCAL_DEMO.md`](./docs/LOCAL_DEMO.md) | local backend and frontend guide |
| [`docs/REAL_DATA.md`](./docs/REAL_DATA.md) | source, license, and normalization of the Fitbit data |
| [`docs/EVALUATION.md`](./docs/EVALUATION.md) | offline evaluation reference numbers |
| [`docs/BUILDER_STORY.md`](./docs/BUILDER_STORY.md) | builder.aws bonus post draft |
| [`agentcore/`](./agentcore) | deployable AgentCore runtime entrypoint |
| [`flylab/`](./flylab) | swarm, twin, calibration, safety, memory, evaluation, telemetry |
| [`web/`](./web) | Vercel frontend, canvas visuals, serverless proxy |
| [`scripts/`](./scripts) | data ingestion, calibration, deployment, invocation, evals |
| [`examples/`](./examples) | runnable demos |
| [`tests/`](./tests) | automated verification |
| [`data/real_users/`](./data/real_users) | normalized real Fitbit inputs |
| [`assets/`](./assets) | evolution dashboard image |
| [`diagrams/`](./diagrams) | architecture diagram (SVG + PNG) |
| [`Dockerfile`](./Dockerfile) | linux/arm64 container image for AgentCore |
| [`requirements.txt`](./requirements.txt) | core runtime dependencies |
| [`requirements-local.txt`](./requirements-local.txt) | local dev + CI install (numpy, Strands, AgentCore, ollama) |
| [`requirements-strands.txt`](./requirements-strands.txt) | Strands Agents SDK |
| [`requirements-agentcore.txt`](./requirements-agentcore.txt) | Bedrock AgentCore runtime |

## License

MIT — see [LICENSE](./LICENSE).
