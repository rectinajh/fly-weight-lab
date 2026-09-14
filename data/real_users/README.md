# Real Fitbit data

These per-user files are normalized from the public CC-BY-4.0 dataset:

- Zenodo record: https://zenodo.org/records/53894
- DOI: 10.5281/zenodo.53894
- Original authors: Furberg, R., Brinton, J., Keating, M., & Ortiz, A. (2016)

They are real observations from the Fitabase exports, not synthetic rows. The
weight files are used to calibrate a behavioral twin. The activity files are
used to ground the step and activity context in the demo flow.

To regenerate these files, run:

    .venv/bin/python scripts/ingest_fitbit_data.py
