# PRD — Fly Weight-Lab

> Version: v0.2 · Track: Everyday Agents · Event: Agents for Humans Hackathon (AWS × Strands Agents SDK)

## 1. One-line positioning

A background AI agent that breeds a swarm of cyber fruit flies — cheap,
disposable digital twins — to evolve the one weight-loss protocol that a
specific person can actually sustain, and surfaces a single decision only when
a real decision is needed.

## 2. Background and problem

Weight loss is one of the most universal and most frustrating goals in the
world. Most failures are not caused by not knowing that you should eat less and
move more. They come from three structural problems:

1. **Feedback is slow and noisy.** A real signal takes weeks, and it is polluted
   by water weight, plateaus, hormones, cycles, and life events.
2. **It is deeply individual.** A 16:8 fast that works for one person can
   directly trigger bingeing in another, and the same person changes across
   life stages.
3. **Experimentation is expensive.** You only have one body, so you cannot run
   ten thousand protocols at once. Every failed attempt costs weeks plus one
   more round of self-doubt.

Existing products solve the wrong problem. MyFitnessPal does **tracking**. Noom
does **nudging**. Template content does **generic advice**. None of them answer
the question that actually decides success: **which protocol can this specific
person sustain, and how will their body respond?**

The wrong conclusion people draw is "it must be me." The truth is that they have
been running unmodelled, unrepeatable experiments on the one body they cannot
afford to lose.

## 3. Target users

- **Core user:** ordinary people who have failed at weight loss repeatedly and
  have started to blame themselves. They tried fasting, keto, calorie counting,
  personal training, and quit because they could not sustain it or hit a
  plateau.
- **Secondary users:** people who lost weight and fear regaining it; people with
  chronic conditions or medication who need a more cautious protocol and get a
  sentinel plus an escalation prompt rather than medical advice.

## 4. Value proposition

**Other apps record what you ate. This agent runs experiments for you and
absorbs the cost of failure.**

Your body runs one protocol. The flies run ten thousand. You make one "lock in
this habit" decision per week; the agent absorbs the rest of the noise in the
background.

## 5. Core features

### F1. Behavioral twin

- Trains a **personalized behavioral response model** from the user's real logs
  (weight, food, sleep, mood, adherence; optionally cycle and medication).
- Predicts behavior, not metabolism: given a protocol, will **this person**
  sustain it, how will weight move, and how high is the binge risk?

### F2. Genetic swarm engine

- Each fly is a candidate protocol (genotype: calorie target, protein share,
  eating window, habit trigger, training, sleep, refeed cadence).
- The twin simulates thousands of futures, scores each fly, culls the weak, and
  breeds, crosses over, and mutates the strong across generations.

### F3. Decision surface

- The agent reruns on a schedule in the background (refit on new logs, full
  evolution weekly).
- It interrupts a human in exactly three situations: a clearly better champion
  appears; a risk crosses a threshold (plateau, adherence drop, binge warning);
  or the weekly "lock one habit" update is due.
- Every surface is **one decision** plus one reason plus one action for the week.

### F4. Evolution dashboard

- Dead flies versus surviving champions, generation-by-generation population
  farm, and a convergence view of the protocol lineage.
- It is both a product surface and the core visual of the demo.

## 6. Core user journey

1. The user connects data (manual entry or wearable export) and completes a
   two-week baseline.
2. The agent fits the behavioral twin and runs the first swarm in the
   background.
3. Each week the user receives one message: **"lock in this single habit"**,
   with the reason and the next action.
4. On a plateau or adherence drop, the agent proactively surfaces one lever.
5. The user keeps logging, the twin keeps sharpening, and the swarm keeps
   evolving toward a protocol that looks like it grew only for them.

## 7. Success criteria (judge-oriented)

- **Demonstrable:** two users with the same goal evolve **opposite** protocols,
  proving personalization is real rather than templated.
- **Explainable:** every champion carries the evolutionary evidence for why it
  won.
- **Verifiable:** the twin is fitted from real logs, not from invented market or
  metabolic assumptions.
- **On theme:** runs autonomously in the background, surfaces only real
  decisions, one at a time.
- **Safe:** never emits a dangerous deficit target and never crosses into
  medical advice.

## 8. Non-goals

- No metabolic simulator (neither credible nor necessary).
- No medical diagnosis or prescription; users with a clinical background get a
  "talk to a clinician" escalation only.
- No social feed, streak leaderboard, or commerce funnel in v1.
- No automatic external action that affects health (no ordering, no dosing).

## 9. Risks and compliance

- **Trust barrier:** money and health are high-trust domains. Mitigation: the
  agent offers decision prompts, not commands, and everything is explainable and
  reversible.
- **Twin credibility:** it must be described honestly as a *behavioral* twin,
  not a metabolic model. This is the first question a judge asks.
- **Health safety:** calorie targets carry a hard floor, and dangerous protocols
  are filtered out.
- **Data privacy:** weight, food, and mood are sensitive. Store locally or
  encrypted, state the purpose clearly, and allow deletion.

## 10. Milestones

- **M0 (week 1):** plateau-breaker slice. One fly equals one future, ten thousand
  runs, cull/keep visualization. This is the smallest demonstrable atom.
- **M1 (weeks 2–3):** Strands Agents SDK plus AgentCore, so it reruns on a
  schedule in the background and only interrupts when a risk line is crossed.
- **M2 (weeks 4–5):** protocol generation plus genetic evolution, so the swarm
  genuinely breeds and converges into a full lab.
- **M3 (week 6):** five-minute demo video, documentation, submission.

## 11. Current status

The MVP is built and deployed. Full details live in
[IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md); the short version:

- Genetic swarm, behavioral twin, process-stable fitness, and the background
  agent loop are implemented and tested.
- The behavioral twin is grounded in the real Janelia MaleCNS mushroom body
  (4,064 Kenyon cells, 340 DANs, 97 MBONs, reward : punishment = 2.56 : 1).
- Two real Fitbit users are preloaded, so the live demo runs the real business
  flow without asking anyone to upload a CSV.
- A real Bedrock AgentCore Runtime is deployed in `us-east-1` and is `READY`;
  the data plane has been invoked successfully.
- The Vercel frontend proxies to AgentCore through two serverless functions and
  authenticates with Vercel ↔ AWS OIDC federation instead of long-lived keys.
- GitHub Actions and the Vercel production deployment both pass on `main`.

## 12. Open hypotheses

1. Users will log consistently enough for at least two weeks to fit a usable
   behavioral twin.
2. "One decision at a time" drives more real adherence than "a screen of
   suggestions."
3. The two-user opposite-protocol comparison is enough to convince a judge that
   personalization is real.
