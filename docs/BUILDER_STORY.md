# Fly Weight-Lab: letting ten thousand cyber flies fail for you

**Agents for Humans Hackathon · Everyday Agents**

## Why I built this

Weight loss is the most universal goal I know that also makes people doubt
themselves the most. The problem is not that people don't know to eat less and
move more. It is that everyone has exactly one body, so nobody can try ten
thousand protocols at once. Every failure costs weeks of progress plus one more
round of "I guess I just have no willpower."

I wanted to build an agent that genuinely works in the background: it absorbs the
cost of failed experiments, it only appears when a real decision is needed, and
even then it gives you exactly one decision.

## How it works

Fly Weight-Lab solves this with three pieces.

1. **A behavioral digital twin.** It does not pretend to simulate metabolism. It
   fits "can you actually sustain this, and what does your body roughly do" from
   your real logs.
2. **A fruit-fly swarm.** Each fly is a candidate protocol. It runs thousands of
   simulated futures through the twin. Weak protocols are culled; strong ones
   breed, cross over, and mutate until one champion remains.
3. **A real fruit-fly connectome prior.** The project wires in the Janelia
   MaleCNS mushroom body: 4,064 Kenyon cells, 340 reward and punishment neurons,
   97 decision neurons. Real wiring has reward outweighing punishment by about
   2.56 to 1, so a restriction-only crash diet triggers stronger rebound
   pressure than a hand-tuned model would assume.

## Where the Strands Agents SDK fits

The agent loop is orchestrated by Strands, and the capabilities are split into
six narrow tools:

- `get_user_context`
- `detect_plateau`
- `simulate_candidate`
- `evolve_champion`
- `surface_decision`
- `record_feedback`

The model is not calling one black-box function. It composes these tools itself:
read context, judge the plateau, simulate candidates, evolve a champion, produce
a decision, record feedback. The default offline path runs the full tool-call
loop against a deterministic MockModel, so it demos with no API key. Switching to
Ollama, OpenAI, Anthropic, or Bedrock is an environment variable.

## Safety boundaries

The project has hard guardrails. Calories cannot fall below a weight-based floor.
Protein share, sleep, and eating window all have hard bounds. When a profile
looks clinically out of scope or carries very high binge risk, the agent only
suggests talking to a professional. It never diagnoses and never prescribes.

## The shot I want judges to remember

Across the whole window the agent comes up only a few times and stays quiet the
rest. It is not pushing notifications. It is absorbing noise in the background
and giving you one decision when a plateau appears or the champion protocol
genuinely changes.

**Your body runs one champion protocol. The flies run ten thousand failed
experiments.**

Repository: https://github.com/rectinajh/fly-weight-lab

Live demo: https://fly-weight-lab-demo.vercel.app

`#AgentsforHumans`
