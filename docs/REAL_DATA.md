# Real Data

Fly Weight-Lab's demo is not run on synthetic sample rows. The repository
contains a small, normalized subset of a public Fitbit dataset:

- Dataset: Crowd-sourced Fitbit datasets 03.12.2016-05.12.2016
- DOI: [10.5281/zenodo.53894](https://doi.org/10.5281/zenodo.53894)
- License: CC-BY-4.0
- Original archive: `mturkfitbit_export_3.12.16-4.11.16.zip`

## What is committed

`data/real_users/` contains only the small cleaned files needed for the demo:

- `6962181067_weight.csv` — 14 daily weight observations for one real Fitbit user.
- `6962181067_activity.csv` — the same user's daily steps, active minutes, and calories.
- `8877689391_weight.csv` — 9 daily weight observations for a second real user.
- `8877689391_activity.csv` — the second user's daily activity.
- `manifest.json` — source, license, citation, and row counts.

The original minute-level archives total hundreds of megabytes and are not
committed. They can be regenerated locally with:

```bash
.venv/bin/python scripts/ingest_fitbit_data.py
```

## What is real vs. what is a model prior

The weight trajectory, weight volatility, step count, and active minutes are
observed data. Fly Weight-Lab does not claim to have measured diet adherence
from a weight-only CSV; `adherence_base` is therefore kept as an explicitly
neutral model prior when no explicit adherence column is present. The product
does not pretend a logging cadence proves someone followed a diet.
