"""The task format: what the agent sees for one cohort, and how its answer is turned into labels.

Following GenoMAS, the agent does not label samples one by one. It sees the trait and the unique
values of each metadata row, picks the row that holds the trait, and maps each unique value to
disease, control, or unknown. That mapping is then applied to every sample.

Rows with very many unique values (sample titles like "patient 17", ages) would make prompts huge.
So a row with more than MAX_SHOWN unique values is shown with digit runs replaced by "#"
("patient 17" becomes "patient #"), and if it still has too many values only the first MAX_SHOWN
are listed. The same collapsing is applied when the mapping is used, so the agent's keys match.
Rows with few unique values (where a coded trait like "group: 1" would live) are never collapsed.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COHORT_DIR = ROOT / "benchmark" / "cohorts"
MAX_SHOWN = 30
MAX_NUMERIC_SHOWN = 60
LABELS = ("disease", "control", "unknown")
LABEL_TO_INT = {"disease": 1, "control": 0}


def _unique_in_order(values: list[str]) -> list[str]:
    seen, out = set(), []
    for v in values:
        if v not in seen:
            seen.add(v)
            out.append(v)
    return out


def _num_key(v: str):
    m = re.findall(r"-?\d+(?:\.\d+)?", v)
    return (0, float(m[-1]), v) if m else (1, 0.0, v)


def collapse_digits(v: str) -> str:
    return re.sub(r"\d+(\.\d+)?", "#", v)


def row_view(row: dict) -> dict:
    """How one row is shown to the agent: its key function, shown values, and hidden count."""
    raw = _unique_in_order(row["values"])
    uniq, collapsed, limit = raw, False, MAX_SHOWN
    if len(raw) > MAX_SHOWN:
        squeezed = _unique_in_order([collapse_digits(v) for v in row["values"]])
        if len(squeezed) == 1 and len(raw) <= MAX_NUMERIC_SHOWN:
            # a purely numeric row (an age, a repeat length): collapsing would hide everything,
            # so show the raw numbers, sorted, up to a larger limit
            uniq, limit = sorted(raw, key=_num_key), MAX_NUMERIC_SHOWN
        else:
            uniq, collapsed = squeezed, True
    shown = uniq[:limit]
    return {"row_id": row["row_id"], "name": row["name"], "collapsed": collapsed,
            "values": shown, "n_hidden": len(uniq) - len(shown)}


def sample_key(row: dict, value: str) -> str:
    """The key a sample's value is looked up under in the agent's mapping."""
    return collapse_digits(value) if row_view(row)["collapsed"] else value


def load_cohort(cohort_id: str) -> dict:
    return json.loads((COHORT_DIR / f"{cohort_id}.json").read_text(encoding="utf-8"))


def all_cohorts(split: str | None = None) -> list[dict]:
    out = [json.loads(p.read_text(encoding="utf-8")) for p in sorted(COHORT_DIR.glob("*.json"))]
    return [c for c in out if split is None or c["split"] == split]


def trait_name(cohort: dict) -> str:
    return cohort["trait"]


def apply_mapping(cohort: dict, row_id: str | None, mapping: dict) -> dict:
    """Turn (row, value -> label) into a label per sample: 1, 0, or None (unknown or abstained).

    Values missing from the mapping, and anything that is not "disease" or "control"
    (including "unknown" and "unsure"), become None.
    """
    rows = {r["row_id"]: r for r in cohort["rows"]}
    if row_id not in rows:
        return {s: None for s in cohort["samples"]}
    row = rows[row_id]
    norm = {str(k).strip(): str(v).strip().lower() for k, v in (mapping or {}).items()}
    preds = {}
    for s, v in zip(cohort["samples"], row["values"]):
        lab = norm.get(sample_key(row, v).strip())
        preds[s] = LABEL_TO_INT.get(lab)
    return preds


def best_row_accuracy(cohort: dict, row: dict) -> float:
    """Upper bound: accuracy of the best possible value -> label mapping for this row.

    Each shown value is mapped to the expert label held by most of its samples. Used to decide
    which rows "hold the trait" when grading row choice.
    """
    labels = cohort["labels"]
    groups: dict[str, list[int]] = {}
    for s, v in zip(cohort["samples"], row["values"]):
        if s in labels:
            groups.setdefault(sample_key(row, v), []).append(labels[s])
    if len(groups) < 2:
        return 0.0
    correct = sum(max(g.count(0), g.count(1)) for g in groups.values())
    return correct / sum(len(g) for g in groups.values())
