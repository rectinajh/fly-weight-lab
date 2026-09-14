"""Download and normalize a real Fitbit dataset for Fly Weight-Lab.

The source is the CC-BY-4.0 Zenodo record:

    Furberg, R., Brinton, J., Keating, M., & Ortiz, A. (2016).
    Crowd-sourced Fitbit datasets 03.12.2016-05.12.2016.
    Zenodo. https://doi.org/10.5281/zenodo.53894

This script keeps only the small, human-readable per-user CSV files needed by
the demo. The original multi-hundred-MB minute-level export is never committed
to the repository.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import ssl
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "real_users"

ZIP_NAME = "mturkfitbit_export_3.12.16-4.11.16.zip"
ZIP_URL = f"https://zenodo.org/api/records/53894/files/{ZIP_NAME}/content"
WEIGHT_CSV = "Fitabase Data 3.12.16-4.11.16/weightLogInfo_merged.csv"
ACTIVITY_CSV = "Fitabase Data 3.12.16-4.11.16/dailyActivity_merged.csv"


def parse_date(value: str) -> str:
    value = value.strip()
    for fmt in ("%m/%d/%Y %I:%M:%S %p", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    raise ValueError(f"Unrecognized date: {value!r}")


def _download(url: str, dest: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "fly-weight-lab/1.0"})
    try:
        response = urllib.request.urlopen(request)
    except (ssl.SSLCertVerificationError, urllib.error.URLError):
        # Some developer machines have a restricted local CA bundle. This
        # fallback is only for downloading a public dataset and is not used by
        # the application itself.
        context = ssl._create_unverified_context()
        response = urllib.request.urlopen(request, context=context)

    with dest.open("wb") as handle:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            handle.write(chunk)


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def normalize_weight(weight_text: str, out_dir: Path, min_records: int) -> dict[str, int]:
    reader = csv.DictReader(io.StringIO(weight_text))
    by_user: dict[str, list[dict]] = defaultdict(list)
    for row in reader:
        user_id = row.get("Id", "")
        raw_weight = row.get("WeightKg", "")
        raw_date = row.get("Date", "")
        if not user_id or not raw_weight or not raw_date:
            continue
        by_user[user_id].append(
            {
                "date": parse_date(raw_date),
                "weight_kg": f"{float(raw_weight):.3f}",
                "is_manual_report": "true"
                if row.get("IsManualReport", "").strip().lower() == "true"
                else "false",
            }
        )

    counts: dict[str, int] = {}
    for user_id, rows in sorted(by_user.items()):
        rows.sort(key=lambda item: item["date"])
        if len(rows) < min_records:
            continue
        _write_csv(
            out_dir / f"{user_id}_weight.csv",
            ["date", "weight_kg", "is_manual_report"],
            rows,
        )
        counts[user_id] = len(rows)
    return counts


def normalize_activity(activity_text: str, out_dir: Path, user_ids: set[str]) -> None:
    reader = csv.DictReader(io.StringIO(activity_text))
    by_user: dict[str, list[dict]] = defaultdict(list)
    for row in reader:
        user_id = row.get("Id", "")
        if user_id not in user_ids:
            continue
        by_user[user_id].append(
            {
                "date": parse_date(row["ActivityDate"]),
                "total_steps": int(row.get("TotalSteps", "0") or 0),
                "active_minutes": int(row.get("VeryActiveMinutes", "0") or 0)
                + int(row.get("FairlyActiveMinutes", "0") or 0),
                "calories": int(float(row.get("Calories", "0") or 0)),
            }
        )

    for user_id, rows in sorted(by_user.items()):
        rows.sort(key=lambda item: item["date"])
        _write_csv(
            out_dir / f"{user_id}_activity.csv",
            ["date", "total_steps", "active_minutes", "calories"],
            rows,
        )


def write_manifest(counts: dict[str, int]) -> None:
    manifest = {
        "source": "Zenodo 10.5281/zenodo.53894",
        "license": "CC-BY-4.0",
        "citation": (
            "Furberg, R., Brinton, J., Keating, M., & Ortiz, A. (2016). "
            "Crowd-sourced Fitbit datasets 03.12.2016-05.12.2016. Zenodo."
        ),
        "normalized_at": datetime.now(timezone.utc).isoformat(),
        "weight_users": {
            user_id: {"n_records": n} for user_id, n in sorted(counts.items())
        },
    }
    (OUT_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_readme() -> None:
    readme = """# Real Fitbit data

These per-user files are normalized from the public CC-BY-4.0 dataset:

- Zenodo record: https://zenodo.org/records/53894
- DOI: 10.5281/zenodo.53894
- Original authors: Furberg, R., Brinton, J., Keating, M., & Ortiz, A. (2016)

They are real observations from the Fitabase exports, not synthetic rows. The
weight files are used to calibrate a behavioral twin. The activity files are
used to ground the step and activity context in the demo flow.

To regenerate these files, run:

    .venv/bin/python scripts/ingest_fitbit_data.py
"""
    (OUT_DIR / "README.md").write_text(readme, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--min-records", type=int, default=5)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=OUT_DIR,
    )
    args = parser.parse_args()

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        zip_path = Path(tmp) / ZIP_NAME
        print(f"Downloading {ZIP_URL}")
        _download(ZIP_URL, zip_path)

        with zipfile.ZipFile(zip_path) as archive:
            weight_text = archive.read(WEIGHT_CSV).decode("utf-8")
            activity_text = archive.read(ACTIVITY_CSV).decode("utf-8")

    counts = normalize_weight(weight_text, out_dir, args.min_records)
    normalize_activity(activity_text, out_dir, set(counts))
    write_manifest(counts)
    write_readme()

    print(f"Normalized {sum(counts.values())} weight rows for {len(counts)} users.")
    for user_id, n in sorted(counts.items()):
        print(f"  {user_id}: {n} weight records")


if __name__ == "__main__":
    main()
