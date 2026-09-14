"""Reproducibly download and extract the real mushroom-body connectome.

Downloads the public Janelia MaleCNS annotations + connectivity tables from
Google Cloud Storage and extracts the mushroom body (Kenyon cells, DANs,
MBONs) into the small committed artifacts consumed by flylab.connectome.

Run from the repository root:
    python scripts/build_connectome.py
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

BASE = "https://storage.googleapis.com/flyem-male-cns/v1.0/connectome-data/flat-connectome"
ANNOTATIONS = "body-annotations-male-cns-v1.0-minconf-0.5.feather"
WEIGHTS = "connectome-weights-male-cns-v1.0-minconf-0.5.feather"


def download(url: str, dest: Path) -> None:
    if dest.exists():
        print(f"already present: {dest.name}")
        return
    print(f"downloading {url} ...")
    subprocess.run(["curl", "-s", url, "-o", str(dest)], check=True)


def main() -> None:
    try:
        import pandas as pd
    except ImportError:
        print("pandas/pyarrow required: pip install pandas pyarrow", file=sys.stderr)
        raise

    data = Path("data")
    data.mkdir(exist_ok=True)

    ann = data / ANNOTATIONS
    weights = data / WEIGHTS
    download(f"{BASE}/{ANNOTATIONS}", ann)
    download(f"{BASE}/{WEIGHTS}", weights)

    df = pd.read_feather(ann)
    mb = df[df["class"].isin(["Kenyon_Cell", "DAN", "MBON"])].copy()
    mb = mb[["bodyId", "class", "type", "instance", "somaSide"]].dropna(subset=["bodyId"])
    mb["bodyId"] = mb["bodyId"].astype("int64")
    mb.to_csv(data / "mb_neurons.csv", index=False)

    ids = set(mb["bodyId"])
    id2class = dict(zip(mb["bodyId"], mb["class"]))
    id2type = dict(zip(mb["bodyId"], mb["type"]))

    edges = pd.read_feather(weights)
    mask = edges["body_pre"].isin(ids) & edges["body_post"].isin(ids)
    sub = edges[mask].copy()
    sub["pre_class"] = sub["body_pre"].map(id2class)
    sub["post_class"] = sub["body_post"].map(id2class)
    sub["pre_type"] = sub["body_pre"].map(id2type)
    sub["post_type"] = sub["body_post"].map(id2type)
    sub.to_csv(data / "mb_connectome.csv", index=False)

    kc_mbon = sub[(sub["pre_class"] == "Kenyon_Cell") & (sub["post_class"] == "MBON")]
    dan_mbon = sub[(sub["pre_class"] == "DAN") & (sub["post_class"] == "MBON")]
    dan_mbon = dan_mbon.copy()
    dan_mbon["family"] = dan_mbon["pre_type"].apply(
        lambda t: "PAM" if str(t).startswith("PAM") else ("PPL" if str(t).startswith("PPL") else "other")
    )

    summary = {
        "source": "Janelia MaleCNS v1.0 mushroom body (male-cns.janelia.org)",
        "neurons": {
            "Kenyon_Cell": int((mb["class"] == "Kenyon_Cell").sum()),
            "DAN": int((mb["class"] == "DAN").sum()),
            "MBON": int((mb["class"] == "MBON").sum()),
        },
        "mb_edges": int(len(sub)),
        "mb_synaptic_weight": int(sub["weight"].sum()),
        "kc_to_mbon": {
            "edges": int(len(kc_mbon)),
            "mean_kc_per_mbon": float(kc_mbon.groupby("body_post")["body_pre"].nunique().mean()),
            "mean_weight_per_mbon": float(kc_mbon.groupby("body_post")["weight"].sum().mean()),
        },
        "dan_to_mbon": {
            "edges": int(len(dan_mbon)),
            "mean_dan_per_mbon": float(dan_mbon.groupby("body_post")["body_pre"].nunique().mean()),
            "mean_weight_per_mbon": float(dan_mbon.groupby("body_post")["weight"].sum().mean()),
        },
        "dan_family_to_mbon_weight": {
            k: int(v) for k, v in dan_mbon.groupby("family")["weight"].sum().items()
        },
        "class_matrix_weight": {
            f"{a}->{b}": int(w)
            for (a, b), w in sub.groupby(["pre_class", "post_class"])["weight"].sum().items()
        },
    }
    (data / "mb_summary.json").write_text(json.dumps(summary, indent=2))

    print("\nDone. Extracted mushroom-body connectome into data/mb_* files.")
    print(f"  neurons: {summary['neurons']}")
    print(f"  MB edges: {summary['mb_edges']}")


if __name__ == "__main__":
    main()
