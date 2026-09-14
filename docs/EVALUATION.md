# Evaluation

Fly Weight-Lab has an offline evaluation suite so the demo is backed by numbers.

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
  binge_prone:  1416 kcal, late-night=yes, refeed=weekly
  disciplined:  1534 kcal, late-night=yes, refeed=biweekly
```

The plateau detector is deliberately conservative. It avoids false alarms, so
the agent stays quiet more often, which is the intended product behavior.
