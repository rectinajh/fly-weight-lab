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

two users, same goal:
  binge_prone:
    calories:        1928
    late_night_rule: true
    refeed:          weekly
    simulated loss:  2.85 kg / 12 weeks
    adherence:       0.68
    binge risk:      0.55

  disciplined:
    calories:        1513
    late_night_rule: false
    refeed:          none
    simulated loss:  6.00 kg / 12 weeks
    adherence:       0.74
    binge risk:      0.37

champion vs aggressive:
  aggressive:   -5.11 kg change, adherence 0.43, binge risk 0.90
  champion:     +2.91 kg change, adherence 0.62, binge risk 0.62
```

The plateau detector is deliberately conservative. It avoids false alarms, so
the agent stays quiet more often, which is the intended product behavior.

The `two users` result is the important one: two people with the same starting
weight and the same goal can evolve opposite protocols. The binge-prone twin
keeps a planned late-night snack and a weekly refeed; the disciplined twin
gets a tighter calorie target with neither. The aggressive baseline
illustrates the product's safety thesis: an extreme 1,500 kcal / 8-hour plan
simulates as a *gain* because adherence collapses and binge events dominate.

## How this is checked in CI

The GitHub Actions `ci` workflow runs the full test suite on every push:

```bash
pip install -r requirements-local.txt
python -m unittest discover -s tests -v
```

That is 14 tests covering the genotype, the swarm, connectome grounding, the
background loop's quietness, calibration, safety, memory, the offline
evaluation, and the Strands local tool-call loop. The reference numbers above
come from `scripts/run_evals.py` and are regenerated locally, not asserted as
golden values, so the suite stays stable while the search improves.
