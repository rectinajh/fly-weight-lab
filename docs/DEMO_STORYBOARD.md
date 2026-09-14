# Demo Storyboard — Fly Weight-Lab

> Goal: a five-minute hackathon video and live-demo script. The whole story is
> one sentence: **your body runs one champion protocol; the flies run ten
> thousand failed experiments.**

## Demo principles

1. Every shot serves the same line: it runs quietly in the background and
   surfaces only when there is a real decision.
2. Emphasize that the connectome is load-bearing, not decoration. It changes the
   binge-risk model and therefore the final recommendation.
3. Never say "metabolic simulation". Always say "behavioral digital twin".
4. Produce every on-screen result from a real command or a real cloud call, so
   nobody thinks this is a slide deck.

## Shot 1 — Opening hook (15s)

**Screen:** the live demo hero: `FLY WEIGHT-LAB`, with the fly swarm drifting and
diving behind it.

> The hardest part of losing weight is not that you don't know to eat less and
> move more. It's that you only have one body, so you can't run ten thousand
> protocols at the same time.

**Voice-over:**

> MyFitnessPal records what you ate. Noom reminds you to keep going. Neither
> answers the question that actually decides success: which protocol can this
> specific person sustain, and how will their body respond?

**Transition:** the swarm dives across the screen.

## Shot 2 — Swarm evolution (60s)

**Run:** open https://fly-weight-lab-demo.vercel.app and press
**Launch background agent**.

**Screen:**

- The sonar convergence radar: best fitness spirals inward toward the champion
  while the sweep rotates.
- The best-versus-mean line chart converging across generations.
- The population farm: elite cells stay green, parent-pool cells are dim green,
  culled cells go red. This is actual elitism, not a 50/50 median split.
- The Strands tool-call list: get_user_context → detect_plateau →
  simulate_candidate → run_background_loop → emit_decision → record_feedback.
- The champion card and the Lock in / Skip buttons.

**Voice-over:**

> Every fly is a candidate protocol. We run thousands of simulated futures
> through your behavioral twin. Weak protocols go red and die. Strong ones breed,
> cross over, and mutate. Only one champion survives. And note this: two users
> with the same goal evolve opposite protocols — one keeps a late-night snack
> and a weekly refeed, the other does not.

**Key moment:** the two-user comparison card at the bottom of the dashboard.

## Shot 3 — Real fruit-fly connectome (60s)

**Run:** `python examples/demo_connectome.py`

**Screen:** the connectome panel at the top of the live demo, plus the terminal
output.

```text
REAL MUSHROOM BODY — Janelia MaleCNS v1.0
Kenyon cells (context):            4064
Dopaminergic neurons (reward):      340
MBONs (decision):                    97
KC -> MBON convergence:             631 KCs per MBON
DAN -> MBON modulation:             32.6 DANs per MBON
Reward (PAM) : Punishment (PPL):    2.56 : 1
```

Then show the grounded-versus-ungrounded binge risk:

```text
Aggressive protocol binge risk, un-grounded: 0.74
Aggressive protocol binge risk, grounded:     0.90
```

**Voice-over:**

> This is not decoration. We wired the real Janelia male fruit-fly mushroom body
> into the twin: 4,064 Kenyon cells, 340 reward and punishment neurons, 97
> decision neurons. Real wiring says reward outranks punishment 2.56 to one.
> Dieting leans on punishment and restriction, so the real circuit predicts
> restriction gets answered with stronger craving pressure. That is why an
> aggressive plan's binge risk jumps from 0.74 to 0.90 once we ground it.

**Key takeaway:** grounding flips the recommendation from "keep cutting
calories" to "raise calories and keep a planned late-night snack".

## Shot 4 — The background agent stays quiet (90s)

**Run:** press **Launch background agent** and scroll to the background-agent
timeline.

**Screen:** the weekly timeline with 12 ticks, quiet weeks as small green dots
and the weeks that surfaced a decision as yellow stars. Then click
**Lock in this habit**.

**Voice-over:**

> This is the shot we want judges to remember. Across twelve weeks the agent
> only comes up a few times; every other week it is completely silent. It reruns
> in the background, but it does not interrupt you. It only surfaces when a new
> plateau appears or the champion protocol genuinely changed. That is the
> definition of an agent for humans: autonomous, and only surfaces on a real
> decision. Strands composed six narrow tools to get there — you can read the
> tool trace on the page.

**Add:** state is persisted, so a restart does not lose the current protocol or
the weight history.

## Shot 5 — Real Fitbit data, no upload (60s)

**Run:** press **Launch background agent** on the live demo. No file picker.

**Screen:**

- The header showing the data source: `data/real_users/6962181067` and the
  Zenodo DOI with the CC-BY-4.0 license.
- The real weight trajectory with yellow × markers on the weeks the agent spoke.
- The calibration card showing the fitted `binge_sensitivity`,
  `metabolic_adaptation`, and adherence prior.
- The decision card with the single surfaced action.

**Voice-over:**

> This is not mock data. We normalized a real Fitbit dataset from Zenodo and
> fitted the behavioral twin from the real weight trajectory. Two real users ship
> inside the runtime, so you can experience the whole flow without uploading
> anything. CSV import still exists if you want to bring your own export.

**Optional terminal equivalent:**

```bash
.venv/bin/python scripts/run_business_flow.py --user-id 6962181067
```

## Shot 6 — Real cloud deployment (45s)

**Run:** open the AgentCore deployment doc, then invoke the runtime directly.

```bash
AWS_PROFILE=flyweight-agentcore .venv/bin/python scripts/invoke_agentcore.py \
  --runtime-arn arn:aws:bedrock-agentcore:us-east-1:032529260721:runtime/flyweight_lab-k3JItG63s2
```

**Screen:** the `READY` runtime, the container image, and the 200 response from
the data plane.

**Voice-over:**

> The swarm does not run in your browser. It runs inside a managed Bedrock
> AgentCore Runtime in us-east-1. The Vercel page reaches it through a serverless
> proxy that authenticates with Vercel-to-AWS OIDC federation, so there are no
> long-lived AWS keys anywhere.

## Shot 7 — Technical honesty and boundaries (45s)

**Screen:** three short lines.

- Behavioral twin, not a metabolic simulator.
- Real Drosophila connectome as a structural prior.
- Safety floor plus medical boundary: prompt, never diagnose, never prescribe.

**Voice-over:**

> We deliberately do not pretend to simulate human metabolism, because that
> would be neither honest nor necessary. What we model is: will this person do
> it, and what happens if they do. The real connectome is only a structural prior
> for habit and reward dynamics. And on safety: calories have a floor, dangerous
> protocols are filtered out, and users with a clinical background only get
> "go talk to a clinician".

## Shot 8 — Closing line (15s)

> Your body runs one experiment. The flies ran ten thousand.

**Voice-over:**

> Fly Weight-Lab. Let ten thousand cyber flies fail for you, so you only ever run
> the one protocol that is proven to work.

## Demo checklist

- [ ] The live demo loads and `/api/ping` reports `Healthy`.
- [ ] `Launch background agent` renders the radar, the farm, the trajectory, the
      timeline, the champion, the decision, and the two-user comparison.
- [ ] `python examples/demo_connectome.py` output matches the numbers in this
      document and in the README.
- [ ] `python -m unittest discover -s tests -v` passes (15 tests).
- [ ] `python scripts/run_business_flow.py --user-id 6962181067` reproduces the
      real-data flow locally.
- [ ] Evolution dashboard image: `assets/evolution_dashboard.png`.
- [ ] Architecture diagram: `diagrams/fly_weight_lab_architecture.png`.
- [ ] Any remaining "metabolism" wording in the video is replaced with
      "behavioral response".
- [ ] Submission page links the repository, the demo video, the PRD, the
      technical design, and this storyboard.
