"""Build the benchmark: about 50 GEO cohorts with GenoTEX expert labels and GEO sample metadata.

    python -m scripts.build_benchmark

What it downloads (cached in data/raw/, which is not committed):
  * From the GenoTEX release on Hugging Face (CC BY 4.0), only small files:
      output/preprocess/<Trait>/cohort_info.json      which cohorts the experts found usable
      output/preprocess/<Trait>/clinical_data/<GSE>.csv  expert trait label (0 or 1) per sample
      output/preprocess/<Trait>/code/<GSE>.py         expert code, read as TEXT only (never run)
                                                     to find which metadata row they used
    and the folder listing of input/GEO/<Trait>/<GSE>/ to find which matrix file they used.
  * From NCBI GEO: the header of that series matrix file, streamed and cut off before the
    expression table, so each download is small.

Selection (seed 7, fixed): traits are shuffled; each trait needs at least 3 usable, unbiased GEO
cohorts. Cohorts are then taken round robin across traits (at most 4 per trait, at most 15 traits)
until 50 cohorts pass the checks: binary 0/1 labels, at least 3 samples in each class, and at least
90% of labelled samples found in the GEO header. Then 10 cohorts are drawn as the development set.
No cohort is chosen or rejected based on how hard it looks.
"""
from __future__ import annotations

import io
import json
import random
import time
from pathlib import Path

import pandas as pd
import requests

from src.cohort import COHORT_DIR, best_row_accuracy, sample_key
from src.geo import matrix_url, parse_expert_trait_row, parse_header, stream_header

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
HF_API = "https://huggingface.co/api/datasets/Liu-Hy/GenoTEX/tree/main/"
HF_FILE = "https://huggingface.co/datasets/Liu-Hy/GenoTEX/resolve/main/"
SEED = 7
N_COHORTS = 50
N_DEV = 10
MAX_PER_TRAIT = 4
MAX_TRAITS = 15
MIN_PER_CLASS = 3
UA = {"User-Agent": "sample-sheet-agents-benchmark/0.1 (research script)"}


def cached(path: Path, fetch) -> bytes:
    if path.exists():
        return path.read_bytes()
    data = fetch()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    time.sleep(0.4)   # be polite to the servers
    return data


def hf_list(sub: str) -> list[dict]:
    key = RAW / "hf_listings" / (sub.replace("/", "__") + ".json")
    return json.loads(cached(key, lambda: requests.get(HF_API + sub, headers=UA, timeout=60).content))


def hf_get(sub: str) -> bytes:
    def fetch():
        r = requests.get(HF_FILE + sub, headers=UA, timeout=120)
        r.raise_for_status()
        return r.content
    return cached(RAW / "genotex" / sub, fetch)


def trait_display_name(folder: str) -> str:
    return folder.replace("_", " ")


def try_cohort(trait: str, gse: str) -> dict | None:
    """Download and check one cohort. Returns the benchmark record or None (with a reason printed)."""
    try:
        clin = pd.read_csv(io.BytesIO(hf_get(f"output/preprocess/{trait}/clinical_data/{gse}.csv")),
                           index_col=0)
    except Exception as e:
        print(f"  skip {gse}: no clinical table ({e})")
        return None
    trait_rows = [i for i in clin.index if i not in ("Age", "Gender")]
    if not trait_rows:
        print(f"  skip {gse}: no trait row")
        return None
    lab = clin.loc[trait_rows[0]].dropna()
    if not set(lab.unique()) <= {0, 1}:
        print(f"  skip {gse}: trait is not binary")
        return None
    labels = {s: int(v) for s, v in lab.items()}
    n1 = sum(labels.values())
    n0 = len(labels) - n1
    if min(n0, n1) < MIN_PER_CLASS:
        print(f"  skip {gse}: too few in one class ({n1} cases, {n0} controls)")
        return None
    files = [x["path"].split("/")[-1] for x in hf_list(f"input/GEO/{trait}/{gse}")]
    mats = sorted(f for f in files if f.endswith("series_matrix.txt.gz"))
    if not mats:
        print(f"  skip {gse}: no matrix file listed")
        return None
    try:
        hdr = cached(RAW / "geo" / (mats[0] + ".header.txt"),
                     lambda: stream_header(matrix_url(gse, mats[0])).encode("utf-8"))
    except Exception as e:
        print(f"  skip {gse}: header download failed ({e})")
        return None
    parsed = parse_header(hdr.decode("utf-8"))
    found = [s for s in labels if s in set(parsed["samples"])]
    if len(found) < 0.9 * len(labels):
        print(f"  skip {gse}: only {len(found)}/{len(labels)} labelled samples in the header")
        return None
    labels = {s: labels[s] for s in found}
    code = hf_get(f"output/preprocess/{trait}/code/{gse}.py").decode("utf-8", errors="replace")
    expert_row = parse_expert_trait_row(code)
    rec = {
        "cohort_id": gse,
        "trait": trait_display_name(trait),
        "trait_folder": trait,
        "series_title": parsed["series_title"],
        "matrix_file": mats[0],
        "samples": parsed["samples"],
        "rows": parsed["rows"],
        "labels": labels,
        "n_samples_total": len(parsed["samples"]),
        "n_labelled": len(labels),
        "n_disease": sum(labels.values()),
        "n_control": len(labels) - sum(labels.values()),
        "expert_trait_row": f"char_{expert_row}" if isinstance(expert_row, int) else expert_row,
    }
    valid = []
    for row in parsed["rows"]:
        n_groups = len({sample_key(row, v) for v in row["values"]})   # values as the agent sees them
        acc = best_row_accuracy(rec, row)
        if acc >= 0.95 and n_groups <= max(2, len(labels) / 2):
            valid.append(row["row_id"])
    if isinstance(rec["expert_trait_row"], str) and rec["expert_trait_row"] not in valid \
            and rec["expert_trait_row"] in {r["row_id"] for r in parsed["rows"]}:
        valid.append(rec["expert_trait_row"])
    rec["valid_rows"] = valid
    return rec


def main():
    rng = random.Random(SEED)
    traits = sorted(x["path"].split("/")[-1] for x in hf_list("output/preprocess") if x["type"] == "directory")
    rng.shuffle(traits)
    pools: dict[str, list[str]] = {}
    for t in traits:
        if len(pools) >= MAX_TRAITS + 5:   # a few spares in case some traits yield nothing
            break
        try:
            info = json.loads(hf_get(f"output/preprocess/{t}/cohort_info.json"))
        except Exception:
            continue
        ok = sorted(g for g, v in info.items() if g.startswith("GSE") and v.get("is_usable")
                    and v.get("is_trait_available") and v.get("is_biased") is False)
        if len(ok) >= 3:
            rng.shuffle(ok)
            pools[t] = ok
            print(f"trait {t}: {len(ok)} usable cohorts")

    chosen: dict[str, list[dict]] = {}
    trait_order = list(pools)
    while sum(len(v) for v in chosen.values()) < N_COHORTS and any(pools.values()):
        progressed = False
        for t in trait_order:
            if sum(len(v) for v in chosen.values()) >= N_COHORTS:
                break
            if len(chosen.get(t, [])) >= MAX_PER_TRAIT or not pools[t]:
                continue
            if t not in chosen and len(chosen) >= MAX_TRAITS:
                continue
            gse = pools[t].pop(0)
            progressed = True
            if any(r["cohort_id"] == gse for v in chosen.values() for r in v):
                print(f"  skip {gse}: already chosen for another trait")
                continue
            print(f"{t} {gse}")
            rec = try_cohort(t, gse)
            progressed = True
            if rec:
                chosen.setdefault(t, []).append(rec)
        if not progressed:
            break

    records = [r for t in trait_order for r in chosen.get(t, [])]
    ids = sorted(r["cohort_id"] for r in records)
    dev = set(random.Random(SEED + 1).sample(ids, N_DEV))
    COHORT_DIR.mkdir(parents=True, exist_ok=True)
    for old in COHORT_DIR.glob("*.json"):
        old.unlink()
    for r in records:
        r["split"] = "dev" if r["cohort_id"] in dev else "test"
        (COHORT_DIR / f"{r['cohort_id']}.json").write_text(json.dumps(r, indent=1, ensure_ascii=False),
                                                            encoding="utf-8")
    print(f"\nwrote {len(records)} cohorts across {len(chosen)} traits "
          f"({len(dev)} dev, {len(records) - len(dev)} test)")


if __name__ == "__main__":
    main()
