"""Summarize a run: metrics per model and method, and an error category for every failed cohort.

    python -m src.analyze --run main
    python -m src.analyze --run main,main_f,main_b --out combined     # several runs together

Writes results/runs/<run or out>/summary.json, metrics.md, errors.csv, error_examples.md, and
mechanism.md (error type rates per method, plus tool use statistics for method F).

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
    """Attempts of one run, or of several runs given as a comma separated list."""
    out = []
    for r in run.split(","):
        p = ROOT / "results" / "runs" / r.strip() / "attempts.jsonl"
        out += [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    return out


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


def error_examples(atts: list[dict], split: str = "test", per_cat: int = 2) -> str:
    """Real failures with the actual metadata values, the model's labels, and the expert labels."""
    errs = error_table(atts, split)
    by_key = {(a["model"], a["method"], a["repeat"], a["cohort_id"]): a for a in atts}
    L = ["# Error examples\n",
         "Real failed cohorts from this run, grouped by error type. For each: the trait, the row the "
         "method chose, and the values of that row with the method's label and the expert label "
         "(majority of the expert labels of its samples).\n"]
    seen_cohorts = set()
    for cat in ["wrong row", "other disease as disease", "negation missed", "synonym or code missed",
                "values left unlabelled", "flipped labels", "invalid output", "abstained", "other"]:
        xs = [e for e in errs if e["category"] == cat and e["model"] != "none"]
        if not xs:
            continue
        L.append(f"## {cat} ({len(xs)} failed cohort attempts)\n")
        shown = 0
        for e in xs:
            if shown >= per_cat or e["cohort_id"] in seen_cohorts:
                continue
            a = by_key[(e["model"], e["method"], e["repeat"], e["cohort_id"])]
            c = load_cohort(e["cohort_id"])
            res = a["result"]
            L.append(f"**{e['cohort_id']}**, trait *{c['trait']}*, method {e['method']}, {e['model']}, "
                     f"accuracy {100 * e['accuracy']:.0f}%. Study title: {c['series_title']}")
            if e["judgment_call"]:
                L.append(f"(Expert judgment call: {e['judgment_call']}.)")
            if cat == "invalid output":
                start = (res["raw"][0] if res["raw"] else "")[:200].replace("\n", " ")
                L.append(f"\nReason: {res['invalid_reason']}. Start of the output: `{start}`\n")
            elif cat == "abstained":
                L.append("\nThe method answered cannot determine or unsure for most samples.\n")
            else:
                gold_row = c["expert_trait_row"]
                L.append(f"\nChosen row `{res['row']}`; expert row `{gold_row}`.\n")
                gold = gold_answer(c)["mapping"]
                rows = {r["row_id"]: r for r in c["rows"]}
                if res["row"] != gold_row and res["row"] in rows:
                    vals = row_view(rows[res["row"]])["values"][:8]
                    L.append("Values of the chosen row and the method's labels: "
                             + "; ".join(f"`{v}` -> {res['mapping'].get(v, 'missing')}" for v in vals) + "\n")
                    L.append("Expert row values: "
                             + "; ".join(f"`{v}` -> {g}" for v, g in list(gold.items())[:8]) + "\n")
                else:
                    L.append("| Value | Method | Expert |\n|---|---|---|")
                    for v, g in list(gold.items())[:10]:
                        m = res["mapping"].get(v, "missing")
                        why = res.get("reasons", {}).get(v, "")
                        why = f" ({why})" if why else ""
                        mark = "" if m == g else " **x**"
                        L.append(f"| `{v}` | {m}{why} | {g}{mark} |")
                    L.append("")
            seen_cohorts.add(e["cohort_id"])
            shown += 1
    return "\n".join(L) + "\n"


def mechanism(atts: list[dict], split: str = "test") -> dict:
    """Per (model, method): share of ALL attempts whose main error is each type, and F tool stats."""
    atts = [a for a in atts if a["split"] == split]
    errs = {(e["model"], e["method"], e["repeat"], e["cohort_id"]): e["category"] for e in error_table(atts, split)}
    groups = defaultdict(list)
    for a in atts:
        groups[(a["model"], a["method"])].append(a)
    rates, agent = [], []
    for (model, method), xs in sorted(groups.items()):
        cats = Counter(errs.get((a["model"], a["method"], a["repeat"], a["cohort_id"]), "solved") for a in xs)
        rates.append({"model": model, "method": method, "n": len(xs),
                      **{c: cats[c] / len(xs) for c in ("values left unlabelled", "wrong row", "invalid output")}})
        if method == "F":
            ag = [a["result"].get("agent", {}) for a in xs]
            n_calls = sum(g.get("n_tool_calls", 0) for g in ag)
            flagged = [g for g in ag if g.get("flagged")]
            err = sum((Counter(g.get("errors", {})) for g in ag), Counter())
            agent.append({"model": model, "n": len(xs),
                          "tool_calls_per_cohort": n_calls / len(xs),
                          "steps_per_cohort": sum(g.get("n_steps", 0) for g in ag) / len(xs),
                          "recovered_share": sum(g.get("n_recovered", 0) for g in ag) / max(1, n_calls),
                          "submitted": sum(g.get("stop") == "submitted" for g in ag),
                          "check_used": sum(bool(g.get("checks")) for g in ag),
                          "flagged": len(flagged),
                          "fixed_after_flag": sum(bool(g.get("fixed_after_flag")) for g in flagged),
                          "final_check_ok": sum(bool(g.get("final_check_ok")) for g in ag),
                          "errors": dict(err)})
    return {"rates": rates, "agent": agent}


def mechanism_markdown(m: dict) -> str:
    L = ["# Error type rates and tool use\n",
         "Share of all attempts (cohort x repeat) whose main error is each type; attempts with accuracy of "
         "at least 95% count as solved and have no error type.\n",
         "| Model | Method | Attempts | Values left unlabelled % | Wrong row % | Invalid output % |",
         "|---|---|---|---|---|---|"]
    for r in m["rates"]:
        L.append(f"| {r['model']} | {r['method']} | {r['n']} | {100 * r['values left unlabelled']:.1f} | "
                 f"{100 * r['wrong row']:.1f} | {100 * r['invalid output']:.1f} |")
    if m["agent"]:
        L += ["\n## Method F tool use\n",
              "| Model | Attempts | Tool calls per cohort | Steps per cohort | Calls recovered from text % | "
              "Submitted | Used check_mapping | check_mapping flagged | Fixed after flag | Final answer passes check | "
              "Loop events |", "|---|---|---|---|---|---|---|---|---|---|---|"]
        for g in m["agent"]:
            errs = ", ".join(f"{k} {v}" for k, v in sorted(g["errors"].items())) or "none"
            L.append(f"| {g['model']} | {g['n']} | {g['tool_calls_per_cohort']:.1f} | {g['steps_per_cohort']:.1f} | "
                     f"{100 * g['recovered_share']:.0f} | {g['submitted']} | {g['check_used']} | {g['flagged']} | "
                     f"{g['fixed_after_flag']} | {g['final_check_ok']} | {errs} |")
    return "\n".join(L) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--split", default="test")
    ap.add_argument("--out", default=None, help="output folder name when several runs are combined")
    a = ap.parse_args()
    atts = load_attempts(a.run)
    d = ROOT / "results" / "runs" / (a.out or a.run)
    d.mkdir(parents=True, exist_ok=True)
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
    (d / "error_examples.md").write_text(error_examples(atts, a.split), encoding="utf-8")
    mech = mechanism(atts, a.split)
    summ["mechanism"] = mech
    (d / "summary.json").write_text(json.dumps(summ, indent=2))
    (d / "mechanism.md").write_text(mechanism_markdown(mech), encoding="utf-8")
    print(metrics_markdown(summ))
    tot = Counter(e["category"] for e in errs)
    print("error categories (all models, methods, repeats):", dict(tot.most_common()))


if __name__ == "__main__":
    main()
