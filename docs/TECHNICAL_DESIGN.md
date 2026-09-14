# Technical Design — Fly Weight-Lab

> Version: v0.2 · Scope: six-week hackathon delivery · Stack: Strands Agents SDK + Bedrock AgentCore + Python

## 1. Architecture overview

```text
User logs (weight / food / sleep / mood / adherence)
        │
        ▼
┌───────────────────────┐
│  Data ingestion        │  normalize, denoise, baseline
└──────────┬────────────┘
           ▼
┌───────────────────────┐
│  Behavioral twin       │  personalized: adherence / weight response / binge risk
└──────────┬────────────┘
           ▼
┌───────────────────────┐
│  Fruit-fly swarm       │  genetic algorithm: spawn → score → breed → converge
└──────────┬────────────┘
           ▼
┌───────────────────────┐
│  Decision surface      │  background reruns + surfaces only a real decision
└──────────┬────────────┘
           ▼
┌───────────────────────┐
│  Evolution dashboard   │  cull/keep population, convergence, champion lineage
└───────────────────────┘
```

In production the middle three boxes run inside the AgentCore Runtime
container, and the dashboard is a static Vercel frontend that reaches it
through a serverless proxy.

### Deployment topology

```text
Browser (Vercel static page + canvas visuals)
   │  fetch /api/ping, /api/invocations
   ▼
Vercel Serverless Functions            (web/api/*.js)
   │  OIDC → sts:AssumeRoleWithWebIdentity  → flyweight-vercel-oidc-role
   │  SigV4
   ▼
Amazon Bedrock AgentCore Runtime       (flyweight_lab-k3JItG63s2, HTTP, PUBLIC)
   │  BedrockAgentCoreApp
   │   ├── GET  /ping
   │   ├── POST /invocations   (local swarm, demo/business flow, Strands agent)
   │   └── POST /business-flow (direct container route for local use)
   ▼
Container image in ECR                 (linux/arm64, port 8080)
```

## 2. Core components

### 2.1 Data ingestion

- Inputs: weight (daily or rolling), food (down to meal or category), sleep
  duration, mood and energy, adherence flags, optionally cycle and medication.
- Sources: manual entry, Apple Health or Fitbit export, food-log APIs.
- Responsibilities: clean, align timelines, drop outliers (a one-day jump is
  treated as water first), and emit trainable features.

### 2.2 Behavioral twin

**Positioning: a personalized behavioral response model, not a metabolic
simulator.**

- Input: historical log features plus one candidate protocol.
- Output: three predictions.
  - `predict_adherence(protocol)` — how likely this person is to stick with it.
  - `simulate_weight(protocol, horizon)` — the 12-week weight trajectory.
  - `predict_binge_risk(protocol)` — how much this protocol invites bingeing.
- Implementation: calibrated rules plus simple regression first (deliverable in
  six weeks), upgradeable to gradient boosting or a light Bayesian model later.
  Refit weekly on new logs so the twin keeps tracking the person.
- Honest boundary: we model "will this person do it and what happens if they
  do", not "how their mitochondria work".
- **Real connectome grounding:** the restriction → rebound coupling uses the
  Janelia MaleCNS mushroom body, where PAM (reward) → MBON outweighs
  PPL (punishment) → MBON by roughly 2.56×. This replaces a hand-tuned constant
  with a structural prior for habit and reward dynamics. It does not claim that
  a human brain equals a fly brain.

### 2.3 Genetic swarm engine

Each fly is a candidate protocol. A genetic algorithm searches the protocol
space for the best solution for this specific person.

- Population: `N = 500–2000` in offline demos, `250–350` for the live demo to
  keep latency inside the serverless timeout budget.
- Selection: tournament (`k = 3–5`), elitism keeps the top K each generation.
- Variation: uniform crossover plus per-gene mutation (Gaussian jitter for
  continuous genes, flip or resample for discrete genes).
- Determinism: each fly's simulated future is seeded from its genotype via a
  stable SHA-1 digest, so the same fly always receives the same score. This
  removed a real bug caused by Python's per-process salted string hash.

### 2.4 Decision surface and background loop

- Implemented in `flylab/agent_loop.py` as `WeightLossAgent`.
- The agent holds the current protocol, the weight history, and the connectome
  parameters.
- Each week, `ingest(weight_kg)` takes the new observation and `tick(week)`
  reruns the swarm.
- A protocol "fingerprint" decides whether the champion genuinely changed; a
  short-window weight delta detects a plateau.
- When a new plateau appears, the agent nudges the twin's
  `metabolic_adaptation` up by 0.05 so the next search is forced to find a
  different lever instead of repeating the same advice.
- The decision surface is called only when `new_plateau or changed` and the
  resurface interval has elapsed. Every other week stays quiet.
- `state_dict()` / `save_state()` / `load_state()` persist the current protocol,
  weight history, plateau memory, and last surface week as JSON, so a restart
  does not lose the experiment.
- Every tick also records a compact evolution history (best, mean, and a
  culled/kept farm string per generation) that the dashboard renders.

### 2.5 Strands Agents SDK bridge

- `flylab/strands_agent.py` exposes narrow tools instead of one god
  function: `get_user_context`, `detect_plateau`, `simulate_candidate`,
  `evolve_champion`, `run_background_loop`, `emit_decision`, `record_feedback`.
- Live `mode=demo` uses a deterministic `FlowModel` that composes those tools
  against real Fitbit users. Tests still use `MockModel`.
- Set `STRANDS_MODEL_PROVIDER` to `ollama`, `openai`, `anthropic`, or `bedrock`
  to use a real model through the same tools.

### 2.6 AgentCore runtime entrypoint

- `agentcore/main.py` wraps the project in `BedrockAgentCoreApp`.
- `@app.entrypoint` handles three payload modes:
  - `{}` (default, `local`) runs the swarm directly with no model or AWS call.
  - `{"mode":"demo", ...}` runs the Strands tool-call loop, then the 12-week
    background agent. If no `weight_records` are supplied it loads the
    preloaded real Fitbit users from `data/real_users/`.
  - `{"mode":"business_flow", ...}` runs the same product loop without Strands.
  - `{"mode":"feedback", ...}` records Lock in / Skip from the UI.
  - `{"mode":"agent","prompt":"..."}` runs the Strands tool-call loop.
- The response for a demo run includes the calibration, the real weight summary,
  the per-week flow, the compact evolution history, the champion protocol, the
  connectome parameters, the surfaced weeks, the final decision, and the durable
  feedback memory.
- AgentCore Runtime provides `POST /invocations` and `GET /ping` automatically.
- `Dockerfile` builds a `linux/arm64` image on port 8080;
  `scripts/deploy_agentcore.py` builds, pushes to ECR, and creates or updates
  the runtime, then waits for `READY`.

### 2.7 Edge proxy and frontend

- `web/api/invocations.js` forwards browser requests to `InvokeAgentRuntime`.
- `web/api/ping.js` calls the control-plane `GetAgentRuntime` for a real health
  check rather than a static "ok".
- Both authenticate with `@vercel/oidc-aws-credentials-provider`, exchanging the
  Vercel OIDC token for short-lived STS credentials. No long-lived AWS keys are
  stored in Vercel.
- The static frontend is dependency-free and uses three canvases: the diving fly
  swarm, the sonar convergence radar, and the connectome wiring animation.
  Charts are hand-rendered SVG so there is no charting library to load.

## 3. Fly genotype

| Gene | Meaning | Example range |
|---|---|---|
| `calorie_target` | daily calorie target | maintenance − 200 to 500 (hard floor applied) |
| `protein_pct` | protein share | 25% – 45% |
| `carb_pct` | carbohydrate share | 20% – 50% |
| `fat_pct` | fat share | derived from the remainder |
| `meal_window` | eating window in hours | 8 = 16:8, 12 = no fasting |
| `meal_count` | meals per day | 2 – 5 |
| `late_night_rule` | allow a planned late-night snack | bool; protective for some people |
| `workout_freq` | training sessions per week | 0 – 6 |
| `workout_type` | training type | cardio / resistance / mix |
| `sleep_target` | sleep target | 7 – 9 hours |
| `refeed_schedule` | planned higher-calorie day | none / weekly / biweekly |
| `step_target` | daily steps (NEAT) | 4,000 – 12,000 |

## 4. Fitness function

For each fly `p`:

```text
adherence     = twin.predict_adherence(p)
weight_curve  = twin.simulate_weight(p, 12 weeks)
total_loss    = start_weight - end_weight
plateau_risk  = plateau detection over the curve
binge_risk    = twin.predict_binge_risk(p)
dropout_risk  = 1 - adherence

fitness = loss_term(total_loss) + w2 * adherence
        - w3 * plateau_risk - w4 * binge_risk - w5 * dropout_risk
        + personalization_terms
```

Weight loss is scored as a **sustainable band** rather than a pure maximization
target. Losing less than the band or more than the band both lose points, which
stops the swarm from crowning either a do-nothing plan or a crash diet.

Adherence carries the largest weight. Anti-perfectionism is written into the
function, not bolted on as a disclaimer.

## 5. Safety constraints

- Calorie targets cannot fall below a weight-based floor.
- Protein, sleep, and eating-window values have hard bounds.
- Out-of-scope profiles (`start_weight_kg` outside 40–220 kg, extremely low
  adherence, extreme binge sensitivity) raise an escalation instead of a plan.
- The agent produces decision prompts, never diagnoses or prescriptions.

## 6. Data flow

1. New log arrives → incremental twin refit.
2. Weekly, or when a risk line is crossed → full swarm evolution.
3. Evolution converges → the champion protocol reaches the decision surface.
4. The decision surface decides whether it is worth interrupting → one decision
   reaches the user.
5. User feedback (kept it / dropped it / logged) flows back as fitness evidence
   for the next generation.

## 7. Technology stack

| Layer | Choice |
|---|---|
| Agent orchestration | Strands Agents SDK |
| Managed runtime | Amazon Bedrock AgentCore Runtime |
| Container registry | Amazon ECR |
| Frontend + edge proxy | Vercel static site + Node serverless functions |
| Edge authentication | Vercel ↔ AWS OIDC federation |
| Algorithms | Python 3.12, numpy, stdlib `random` for the GA |
| Persistence | JSON snapshots for the demo; DynamoDB or Postgres for production |
| Visualization | Hand-rolled canvas and SVG |

## 8. MVP slice: the plateau breaker

The narrowest demonstrable atom:

1. One fly equals one future; run ten thousand.
2. Visualize culled versus surviving flies.
3. Surface one lever only when a plateau or adherence drop appears.

This slice stands alone as a demo and later grew into the full lab.

## 8.1 Code inventory

| Module | Responsibility |
|---|---|
| `flylab/genotype.py` | one fly equals one protocol genotype |
| `flylab/twin.py` | behavioral twin: adherence, weight trajectory, binge risk |
| `flylab/fitness.py` | sustainable-band fitness with adherence weighted highest |
| `flylab/evolution.py` | tournament selection, crossover, mutation, elitism |
| `flylab/plateau.py` | plateau detection |
| `flylab/connectome.py` | Janelia MaleCNS mushroom-body parameter loading |
| `flylab/agent.py` | translate a champion into one decision plus one reason |
| `flylab/agent_loop.py` | background agent loop, state persistence, evolution summary |
| `flylab/business_flow.py` | real-data product loop over weekly checkpoints |
| `flylab/strands_agent.py` | Strands tools, FlowModel demo loop, real provider factory |
| `flylab/calibration.py` | fit twin parameters from real CSV logs |
| `flylab/safety.py` | calorie/protein/sleep/window guardrails and escalation |
| `flylab/memory.py` | durable per-user session and feedback memory |
| `flylab/evaluation.py` | offline plateau and personalization evaluation |
| `flylab/telemetry.py` | structured JSON events and timing |
| `agentcore/main.py` | AgentCore Runtime entrypoint and demo payload handling |
| `scripts/setup_agentcore_role.py` | create the runtime execution role |
| `scripts/deploy_agentcore.py` | build, push, create or update the runtime, wait for READY |
| `scripts/invoke_agentcore.py` | invoke the deployed runtime from the CLI |
| `scripts/setup_vercel_oidc_role.py` | create the Vercel OIDC provider and role |
| `scripts/run_business_flow.py` | real-data end-to-end business loop |
| `scripts/ingest_fitbit_data.py` | download and normalize the real Fitbit dataset |
| `scripts/make_dashboard.py` | generate the 2880×1600 evolution dashboard image |
| `scripts/run_evals.py` | offline evaluation scorecard |
| `scripts/calibrate_twin.py` | fit and print twin parameters from a CSV |
| `web/` | Vercel frontend, canvas visuals, and serverless proxy functions |
| `examples/demo_agent.py` | 12-week background agent demo |
| `tests/` | evolution, connectome, calibration, safety, memory, Strands loop |

## 9. Six-week plan

- Week 1: data ingestion + plateau-breaker MVP + evolution visualization.
- Weeks 2–3: Strands Agents SDK orchestration + AgentCore deployment +
  scheduled background reruns.
- Weeks 4–5: full genetic evolution and the twin refit loop.
- Week 6: demo video, README, architecture diagrams, submission.

## 10. Risks and mitigation

- **Twin credibility:** keep the honest "behavioral twin" framing and fit from
  real data instead of inventing metabolism.
- **Sparse data:** cold-start with common-sense seeds and fast calibration, then
  personalize after a two-week baseline.
- **Health safety:** calorie floors, hard filtering of dangerous protocols, and
  explicit medical escalation.
- **Scope creep:** pin the MVP to the plateau breaker, then expand slice by
  slice.
