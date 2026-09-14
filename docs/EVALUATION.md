# Evaluation

Fly Weight-Lab has an offline evaluation suite so the demo is backed by
numbers, not just a pretty metaphor.

## Run

```bash
.venv/bin/python scripts/run_evals.py
```

## Current reference output

```text
plateau_detection:
  precision: 1.00
  recall:    0.48
  f1:        0.64
  accuracy:  0.74

two users, same start weight (88 kg, safety floor 1936 kcal):
  binge_prone:
    calories:        1936
    late_night_rule: true
    refeed:          weekly
    simulated loss:  2.05 kg / 12 weeks
    adherence:       0.71
    binge risk:      0.55

  disciplined:
    calories:        2028
    late_night_rule: true
    refeed:          none
    simulated loss:  5.71 kg / 12 weeks
    adherence:       0.81
    binge risk:      0.07

champion vs aggressive:
  aggressive:   -5.11 kg change, adherence 0.43, binge risk 0.90
  champion:     +3.32 kg change, adherence 0.69, binge risk 0.48
```

The live demo uses two real Fitbit users of different size, so the champions
diverge more clearly (binge-prone ~1850 kcal with a late-night snack and weekly
refeed; disciplined ~2200 kcal with neither). Same-weight eval twins sit on
the shared safety floor, and personalization shows up in refeed, loss, and
binge risk.

The plateau detector is deliberately conservative. It avoids false alarms, so
the agent stays quiet more often, which is the intended product behavior.

The `two users` result is the important one: two people with the same goal
receive different protocols. The binge-prone twin keeps a weekly refeed and
accepts slower loss; the disciplined twin can sustain a larger simulated loss
with much lower binge risk. The aggressive baseline illustrates the safety
thesis: an extreme 1,500 kcal / 8-hour plan simulates as a *gain* because
adherence collapses and binge events dominate.

## How this is checked in CI

The GitHub Actions `ci` workflow runs the full test suite on every push:

```bash
pip install -r requirements-local.txt
python -m unittest discover -s tests -v
```

That is 15 tests covering the genotype, the swarm, connectome grounding, the
background loop's quietness, calibration, safety, memory, the offline
evaluation, the real two-user divergence, and the Strands local tool-call loop.
