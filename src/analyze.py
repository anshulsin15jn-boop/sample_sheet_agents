"""Summarize a run: metrics per model and method, and an error category for every failed cohort.

    python -m src.analyze --run main

Writes results/runs/<run>/summary.json, metrics.md, errors.csv, and error_examples.md.

How numbers are averaged: for each (model, method, repeat) we average the per cohort metric over
cohorts (so a cohort with 4000 samples counts the same as one with 30). Then we report the mean and
standard deviation of that average across repeats. "Pooled accuracy" instead pools all samples.

Error categories (one per failed cohort, the first that applies, in this order):
  invalid output         the answer could not be parsed or had the wrong structure
  abstained              method D said "cannot determine" or left most samples "unsure"
  wrong row              the chosen row cannot explain the expert labels
  flipped labels         disease and control swapped on the right row
  other disease as disease   a different condition (expert: control) was called disease
  negation missed        a value with non, no, not, adjacent, negative, un... was called disease
  synonym or code missed     a trait value that does not literally name the trait (an abbreviation,
                         a synonym, a code like T21 or M#, a number) was not called disease
  values left unlabelled the row was right but some values were left out or marked unknown
  other                  anything else
Cohorts whose expert labels involve a debatable judgment are also flagged (JUDGMENT_CALLS).
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import statistics
from collections import Counter, defaultdict

from .cohort import ROOT, load_cohort, row_view, sample_key
from .prompts import gold_answer
from .rules import CONTROL_WORDS, _has_word, _norm, trait_keywords

JUDGMENT_CALLS = {
    "GSE120490": "all samples are endometrioid cancer; experts used metastasis yes/no as the label",
    "GSE32924": "non lesional skin (ANL) of eczema patients labelled disease",
    "GSE148810": "lesional skin of a different disease (juvenile dermatomyositis) labelled control",
    "GSE273225": "intracranial bleeding counted as stroke, head trauma as control",
    "GSE235307": "trait is atrial fibrillation one year after surgery, not at sampling",
    "GSE178201": "cell lines: HepG2 (liver cancer) vs MCF10A (breast) as control",
    "GSE161533": "stroke taken from a disease history row in a cancer tissue study",
}
NEG_WORDS = ["non", "no", "not", "adjacent", "negative", "neg", "without", "free"]


def load_attempts(run: str) -> list[dict]:
    p = ROOT / "results" / "runs" / run / "attempts.jsonl"
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def _mean_sd(xs):
    xs = [x for x in xs if x is not None]
    if not xs:
        return None, None
    return statistics.mean(xs), (statistics.stdev(xs) if len(xs) > 1 else 0.0)


def per_sample_errors(cohort: dict, row: str, mapping: dict) -> list[tuple[str, str, str, int]]:
    """(value, predicted label, gold label, number of samples) for mislabelled values on the row."""
    gold = gold_answer(cohort)["mapping"] if row == cohort["expert_trait_row"] else None
    r = next(x for x in cohort["rows"] if x["row_id"] == row)
    counts: dict[tuple, int] = Counter()
    for s, v in zip(cohort["samples"], r["values"]):
        if s not in cohort["labels"]:
            continue
        k = sample_key(r, v)
        y = "disease" if cohort["labels"][s] == 1 else "control"
        p = mapping.get(k, "missing")
        if p != y:
            counts[(k, p, y)] += 1
    return [(k, p, y, n) for (k, p, y), n in counts.most_common()]


def _value_part(v: str) -> str:
    return v.split(":", 1)[1] if ":" in v else v


def categorize(att: dict, cohort: dict) -> str:
    res = att["result"]
    if not res["valid"]:
        return "invalid output"
    if res["cannot_determine"] or (att["method"] == "D" and att["coverage"] < 0.5):
        return "abstained"
    if not att["row_correct"]:
        return "wrong row"
    errs = per_sample_errors(cohort, res["row"], res["mapping"])
    if not errs:
        return "other"
    swaps = [(p, y) for k, p, y, n in errs if {p, y} == {"disease", "control"}]
    if len(swaps) == len(errs) and {p for p, y in swaps} == {"disease", "control"}:
        return "flipped labels"   # every error is a swap, in both directions
    kws = trait_keywords(cohort["trait"])
    votes = Counter()
    for k, p, y, n in errs:
        vp = _norm(_value_part(k))
        if p == "disease" and y == "control":
            if any(_has_word(vp, w) for w in NEG_WORDS) or vp.startswith("un"):
                votes["negation missed"] += n
            elif not any(_has_word(vp, w) for w in CONTROL_WORDS):
                votes["other disease as disease"] += n
            else:
                votes["other"] += n
        elif y == "disease" and p in ("control", "unknown", "unsure"):
            if not any(_has_word(vp, w) for w in kws):
                votes["synonym or code missed"] += n
            else:
                votes["values left unlabelled" if p != "control" else "other"] += n
        elif p in ("missing", "unknown", "unsure"):
            votes["values left unlabelled"] += n
        else:
            votes["other"] += n
    return votes.most_common(1)[0][0]


def summarize(atts: list[dict], split: str = "test") -> dict:
    atts = [a for a in atts if a["split"] == split]
    groups = defaultdict(list)
    for a in atts:
        groups[(a["model"], a["method"])].append(a)
    rows = []
    for (model, method), xs in sorted(groups.items()):
        by_rep = defaultdict(list)
        for a in xs:
            by_rep[a["repeat"]].append(a)
        per_rep = defaultdict(list)
        for rep, ys in by_rep.items():
            n = len(ys)
            per_rep["accuracy"].append(statistics.mean(a["accuracy"] for a in ys))
            per_rep["macro_f1"].append(statistics.mean(a["macro_f1"] for a in ys))
            per_rep["row_acc"].append(statistics.mean(a["row_correct"] for a in ys))
            per_rep["solved"].append(sum(a["solved"] for a in ys))
            per_rep["invalid_rate"].append(statistics.mean(not a["result"]["valid"] for a in ys))
            per_rep["coverage"].append(statistics.mean(a["coverage"] for a in ys))
            sel = [a["selective_accuracy"] for a in ys if a["selective_accuracy"] is not None]
            per_rep["selective_accuracy"].append(statistics.mean(sel) if sel else None)
            per_rep["pooled_accuracy"].append(sum(a["accuracy"] * a["n_graded"] for a in ys)
                                              / sum(a["n_graded"] for a in ys))
            per_rep["seconds"].append(statistics.mean(a["result"]["seconds"] for a in ys))
            per_rep["calls"].append(statistics.mean(a["result"]["n_calls"] for a in ys))
            per_rep["n_cohorts"].append(n)
        row = {"model": model, "method": method, "repeats": len(by_rep)}
        for k, v in per_rep.items():
            m, s = _mean_sd(v)
            row[k] = m
            row[k + "_sd"] = s
        rows.append(row)
    return {"split": split, "rows": rows}


def fmt(m, s=None, pct=True, nd=1):
    if m is None:
        return "n/a"
    if pct:
        out = f"{100 * m:.{nd}f}"
        return out + (f" ± {100 * s:.{nd}f}" if s else "")
    out = f"{m:.{nd}f}"
    return out + (f" ± {s:.{nd}f}" if s else "")


def metrics_markdown(summary: dict) -> str:
    L = [f"Split: {summary['split']}. Means over cohorts; ± is the standard deviation across repeats.\n",
         "| Model | Method | Repeats | Accuracy % | Macro F1 % | Row choice % | Solved cohorts | Invalid % | "
         "Coverage % | Selective acc % | Pooled acc % | Seconds | Calls |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in summary["rows"]:
        L.append(f"| {r['model']} | {r['method']} | {r['repeats']} | {fmt(r['accuracy'], r['accuracy_sd'])} | "
                 f"{fmt(r['macro_f1'], r['macro_f1_sd'])} | {fmt(r['row_acc'], r['row_acc_sd'])} | "
                 f"{fmt(r['solved'], r['solved_sd'], pct=False)} of {int(r['n_cohorts'])} | "
                 f"{fmt(r['invalid_rate'], r['invalid_rate_sd'])} | {fmt(r['coverage'], r['coverage_sd'])} | "
                 f"{fmt(r['selective_accuracy'], r['selective_accuracy_sd'])} | "
                 f"{fmt(r['pooled_accuracy'], r['pooled_accuracy_sd'])} | {fmt(r['seconds'], pct=False, nd=0)} | "
                 f"{fmt(r['calls'], pct=False, nd=1)} |")
    return "\n".join(L) + "\n"


def error_table(atts: list[dict], split: str = "test") -> list[dict]:
    out = []
    cache = {}
    for a in atts:
        if a["split"] != split or a["solved"]:
            continue
        c = cache.setdefault(a["cohort_id"], load_cohort(a["cohort_id"]))
        out.append({"model": a["model"], "method": a["method"], "repeat": a["repeat"],
                    "cohort_id": a["cohort_id"], "trait": a["trait"], "accuracy": round(a["accuracy"], 3),
                    "category": categorize(a, c), "chosen_row": a["result"]["row"],
                    "expert_row": c["expert_trait_row"],
                    "judgment_call": JUDGMENT_CALLS.get(a["cohort_id"], ""),
                    "invalid_reason": a["result"]["invalid_reason"]})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--split", default="test")
    a = ap.parse_args()
    atts = load_attempts(a.run)
    d = ROOT / "results" / "runs" / a.run
    summ = summarize(atts, a.split)
    errs = error_table(atts, a.split)
    cats = Counter((e["model"], e["method"], e["category"]) for e in errs)
    summ["error_counts"] = [{"model": m, "method": me, "category": c, "count": n}
                            for (m, me, c), n in sorted(cats.items())]
    (d / "summary.json").write_text(json.dumps(summ, indent=2))
    (d / "metrics.md").write_text(metrics_markdown(summ), encoding="utf-8")
    if errs:
        with open(d / "errors.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(errs[0]))
            w.writeheader()
            w.writerows(errs)
    print(metrics_markdown(summ))
    tot = Counter(e["category"] for e in errs)
    print("error categories (all models, methods, repeats):", dict(tot.most_common()))


if __name__ == "__main__":
    main()
