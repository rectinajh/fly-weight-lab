# Fly Weight-Lab

An autonomous AI agent that breeds a swarm of **cyber fruit flies** — cheap, disposable digital twins — to evolve the one weight-loss protocol that actually works for *your* body, then surfaces only the single decision worth your attention.

Built for the **Agents for Humans Hackathon** (AWS × Strands Agents SDK).

---

## Background

Weight loss is one of the most universal and most frustrating goals in the world. Hundreds of millions of people attempt it every year, and most fail — not from a lack of knowledge, but because the feedback is slow, noisy, and deeply individual.

- A diet takes weeks to show a real signal, and that signal is polluted by water weight, plateaus, hormones, and life.
- What works for one person — say, 16:8 fasting — can actively trigger bingeing in another.
- You only have one body, so you cannot run 10,000 diet experiments on yourself. Every failed attempt costs weeks, momentum, and self-trust.

The fruit fly (*Drosophila melanogaster*) is biology's favorite model organism for exactly this reason: it is cheap, breeds fast, dies harmlessly, and lets researchers run thousands of experiments that would be impossible or unethical on more complex organisms — then transfer the surviving principles back to humans.

**Fly Weight-Lab is the digital version.** A swarm of cheap, disposable digital twins absorbs the cost of experimentation on your behalf, so your real body only ever runs the winning protocol.

## The Core Problem

Existing weight-loss apps solve the wrong problem. They *track* (food logging), *remind* (nudges), and *prescribe generic advice* ("cut carbs after 8pm"). None of them answer the question that actually decides success:

> **Which protocol can *this specific person* actually sustain, and how will *their body* respond?**

The result is that people run experiments on themselves in the dark, fail repeatedly, and conclude "it must be me." It is not them. It is that they have been running unmodeled, unrepeatable experiments on the one body they cannot afford to lose.

## The Solution

Fly Weight-Lab is an agent that runs quietly **in the background** and does three things:

1. **Builds a behavioral digital twin of you.** This is not a fake metabolic simulator. It is a model of *your* response — how *your* weight, adherence, and binge triggers actually behave — learned from *your* logged history (weight, food, sleep, mood, adherence).
2. **Breeds a swarm of candidate protocols.** Each "fly" carries a genotype: calorie target, protein split, meal timing, habit trigger, workout, sleep, refeed schedule. It runs each fly through thousands of simulated futures using your twin, scoring predicted adherence, weight trajectory, and risk of plateau / binge / dropout.
3. **Evolves and culls.** Genetic selection, crossover, and mutation across generations. Flies that would cause a plateau, a binge, or a quit turn red and die. Only the surviving champion protocols reach you.

The agent surfaces **one decision at a time**, never a dashboard of five hundred suggestions:

> *"This week, lock in this single habit."*

Your body runs one experiment. The flies ran ten thousand.

## Innovation

1. **From passive tracking to active experimentation.** Every other app observes you. This one *runs experiments for you*. The fruit fly here is a genetic experimenter, not a canary that merely watches and warns.
2. **A behavioral digital twin, not a metabolic fantasy.** We simulate *your adherence and response*, learned from your own data. That is honest, buildable in six weeks, and defensible under judge scrutiny. We do not claim to simulate metabolism.
3. **Evolutionary search over protocols, personalized.** The winning plan is *bred from your data*, not picked from a template. Two users with the same goal can receive opposite, individually correct protocols.
4. **One decision at a time.** The agent runs in the background and surfaces only when there is a genuine decision to make — the exact principle this hackathon is built around.
5. **Adherence-first fitness.** The swarm optimizes for "what this person will actually keep doing," not "what burns the most calories on paper." Anti-perfectionism is a feature, not a compromise.

## Why Build It This Way

- **The metaphor is load-bearing, not decorative.** The "spawn → test → breed → mutate → cull → converge" loop *is* the product. The fruit-fly framing is not a name slapped onto a tracker; it is the engine.
- **It answers the judge's killer question.** *"How is this different from MyFitnessPal or Noom?"* — They observe and remind. We run ten thousand disposable experiments so you only run one, and we surface only the decisions that actually matter.
- **It is honest and buildable in six weeks.** A behavioral twin learned from real logs is a tractable machine-learning problem; a metabolic simulator is not. We chose the credible path.
- **It hits the theme's core requirement.** The hackathon explicitly wants agents that "run autonomously and only surface when there's a real decision." That is the entire product.
- **It has a memorable demo.** The winning shot: two users, same goal, the swarm converging on *opposite* plans — proving the personalization is real, not template advice.

## Track

**Everyday Agents** — daily life, money, health, errands, family. Fly Weight-Lab takes the busywork, and the emotional weight, out of one of the most common human struggles.

## Real Connectome Grounding

Fly Weight-Lab does not treat the fruit fly as a metaphor alone. The behavioral twin is grounded in the real *Drosophila* mushroom body from the Janelia MaleCNS connectome ([male-cns.janelia.org](https://male-cns.janelia.org/)):

- 4,064 Kenyon cells (context), 340 dopaminergic neurons (reward/punishment), 97 MBONs (decision).
- 631 Kenyon cells converge on each MBON: context is massively compressed before a single behavioral decision.
- Reward (PAM) outweighs punishment (PPL) ~2.56:1 in real MBON modulation.

That last number is load-bearing. Dieting leans on punishment (restriction), but the real wiring says reward is stronger, so restriction produces disproportionate craving pressure. The grounded twin therefore rates aggressive diets as riskier and recommends gentler, sustainable protocols.

## Current Implementation Status

The repository now contains a runnable end-to-end MVP, not just the idea:

- **Genetic swarm** (`flylab/evolution.py`, `flylab/genotype.py`, `flylab/fitness.py`) evolves a personalized protocol.
- **Behavioral twin** (`flylab/twin.py`) predicts adherence, weight trajectory, and binge risk, honestly labeled as a behavioral model rather than a metabolic simulator.
- **Real connectome grounding** (`flylab/connectome.py`, `data/mb_summary.json`) feeds the Janelia mushroom-body prior into binge-risk coupling.
- **Decision surface** (`flylab/agent.py`) turns a champion protocol into one action plus one reason.
- **Background agent loop** (`flylab/agent_loop.py`) ingests weekly weights, reruns the swarm, and surfaces a decision only when a plateau appears or the champion protocol genuinely changes.
- **State persistence** (`WeightLossAgent.save_state` / `load_state`) snapshots the current protocol, weight history, and plateau memory as JSON, so a restart does not lose the user's experiment.
- **Optional Strands SDK bridge** (`flylab/strands_agent.py`) exposes `run_swarm` and `is_plateau` as tools for a model-driven agent.
- **Verified SDK path** — `pip install -r requirements-strands.txt`, then `build_strands_agent()` constructs a `strands.Agent` without needing live AWS calls.
- **AgentCore runtime entrypoint** (`agentcore/main.py`) wraps the Strands agent in `BedrockAgentCoreApp`; `/invocations` and `/ping` routes register successfully.

Runnable demos:

- `python examples/demo_plateau_breaker.py` — two users evolve opposite protocols.
- `python examples/demo_connectome.py` — shows how real connectome grounding changes the recommendation.
- `python examples/demo_agent.py` — 12-week background agent that stays quiet most weeks and surfaces only real decisions.

Verification:

- `python tests/test_evolution.py -v` — genotype, swarm, connectome loading, and agent-loop quietness tests.

## Repository Layout

- [`README.md`](./README.md) — this document.
- [`docs/PRD.md`](./docs/PRD.md) — product requirements.
- [`docs/TECHNICAL_DESIGN.md`](./docs/TECHNICAL_DESIGN.md) — architecture and implementation plan.
- [`docs/DEMO_STORYBOARD.md`](./docs/DEMO_STORYBOARD.md) — 5-minute hackathon demo script.
- [`docs/AGENTCORE_DEPLOYMENT.md`](./docs/AGENTCORE_DEPLOYMENT.md) — AWS Bedrock AgentCore deployment guide.
- [`requirements-strands.txt`](./requirements-strands.txt) — optional Strands Agents SDK integration.
- [`requirements-agentcore.txt`](./requirements-agentcore.txt) — optional AgentCore runtime dependency.
- [`agentcore/`](./agentcore) — deployable AgentCore runtime entrypoint.
- [`flylab/`](./flylab) — genetic swarm, behavioral twin, connectome grounding, decision surface, and background agent loop.
- [`examples/`](./examples) — runnable demos (plateau breaker, connectome, background agent).
- [`tests/`](./tests) — automated verification.
- [`scripts/build_connectome.py`](./scripts/build_connectome.py) — reproducible download/extract of the real mushroom body.

## License

MIT — see [LICENSE](./LICENSE).
