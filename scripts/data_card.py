"""Write benchmark/DATA_CARD.md from the built cohorts. Every number in the card comes from here.

    python -m scripts.data_card
"""
from __future__ import annotations

from collections import Counter

from src.cohort import ROOT, all_cohorts, row_view
from src.grading import grade
from src.rules import rule_answer


def main():
    cs = all_cohorts()
    lines = []
    w = lines.append
    n_dev = sum(c["split"] == "dev" for c in cs)
    traits = Counter(c["trait"] for c in cs)
    w("# Data card: sample sheet trait extraction benchmark\n")
    w("Built by `python -m scripts.build_benchmark` (fixed seed 7). Inputs are the sample metadata "
      "rows from GEO series matrix headers (NCBI GEO). Labels are the expert trait labels from the "
      "GenoTEX release (Liu et al., arXiv 2406.15341, CC BY 4.0), file "
      "`output/preprocess/<Trait>/clinical_data/<GSE>.csv`.\n")
    w(f"* Cohorts: **{len(cs)}** ({n_dev} development, {len(cs) - n_dev} test)")
    w(f"* Traits: **{len(traits)}**")
    w(f"* Labelled samples: **{sum(c['n_labelled'] for c in cs)}** "
      f"({sum(c['n_disease'] for c in cs)} disease, {sum(c['n_control'] for c in cs)} control)")
    sizes = sorted(c["n_labelled"] for c in cs)
    w(f"* Labelled samples per cohort: median {sizes[len(sizes) // 2]}, smallest {sizes[0]}, "
      f"largest {sizes[-1]}")
    nrows = sorted(len(c["rows"]) for c in cs)
    w(f"* Metadata rows per cohort (title, source, characteristics): median {nrows[len(nrows) // 2]}, "
      f"range {nrows[0]} to {nrows[-1]}")
    multi = sum(len(c["valid_rows"]) > 1 for c in cs)
    w(f"* Cohorts where more than one row can explain the labels: {multi}")
    unl = sum(c["n_samples_total"] - c["n_labelled"] for c in cs)
    w(f"* Samples in the GEO files that the experts left unlabelled (not graded): {unl}\n")

    w("## What counts as disease and control\n")
    w("The label is whatever the GenoTEX experts decided: 1 means the sample has the trait, 0 means it "
      "does not. A 0 is often a healthy control, but sometimes it is a sample with a different disease "
      "(for example, in GSE123086 every non asthma patient is a 0 for Asthma), a non lesional sample, or a "
      "different tumour subtype. This is a real part of why the task is hard: \"control\" is defined by "
      "the study design, not by a word in the metadata.\n")

    w("## Cohorts per trait\n")
    w("| Trait | Cohorts | Dev | Test | Labelled samples | Disease share |")
    w("|---|---|---|---|---|---|")
    for t, k in sorted(traits.items()):
        sub = [c for c in cs if c["trait"] == t]
        lab = sum(c["n_labelled"] for c in sub)
        dis = sum(c["n_disease"] for c in sub)
        w(f"| {t} | {k} | {sum(c['split'] == 'dev' for c in sub)} | {sum(c['split'] == 'test' for c in sub)}"
          f" | {lab} | {dis / lab:.0%} |")

    w("\n## How many cohorts a trivial keyword rule already solves\n")
    res = [(c, grade(c, **{"row": (a := rule_answer(c))["row"], "mapping": a["mapping"],
                           "cannot_determine": a["cannot_determine"]})) for c in cs]
    for split in ("dev", "test"):
        sub = [g for c, g in res if c["split"] == split]
        w(f"* {split}: {sum(g['solved'] for g in sub)} of {len(sub)} cohorts solved (accuracy at least 95%), "
          f"mean accuracy {sum(g['accuracy'] for g in sub) / len(sub):.3f}")
    w("\nThe rule is baseline R (`src/rules.py`). So roughly a third of cohorts are easy; the rest need "
      "reading and judgment.\n")

    w("## All cohorts\n")
    w("| Cohort | Split | Trait | Disease | Control | Expert row | Rows that explain labels | Example values of expert row | Rule solves |")
    w("|---|---|---|---|---|---|---|---|---|")
    for c, g in sorted(res, key=lambda x: (x[0]["split"], x[0]["trait"], x[0]["cohort_id"])):
        rows = {r["row_id"]: r for r in c["rows"]}
        er = c["expert_trait_row"]
        ex = ""
        if er in rows:
            v = row_view(rows[er])["values"][:3]
            ex = "; ".join(x.replace("|", "/") for x in v)[:90]
        w(f"| {c['cohort_id']} | {c['split']} | {c['trait']} | {c['n_disease']} | {c['n_control']} | {er} | "
          f"{', '.join(c['valid_rows'])} | {ex} | {'yes' if g['solved'] else 'no'} |")

    w("\n## Notes and caveats\n")
    w("* Rows that explain the labels: a row counts if the best possible value to label mapping on it "
      "reaches at least 95% agreement with the expert labels and it has at most half as many distinct "
      "(displayed) values as labelled samples. The expert's own row is always included.")
    w("* Long rows: a row with more than 30 distinct values is shown with digit runs replaced by #, "
      "unless it is purely numeric (then up to 60 raw numbers are shown).")
    w("* Labels are inherited from GenoTEX and may contain the occasional expert judgment call that "
      "others would make differently.")
    w("* GEO text is public, so the models may have seen some of it during training.")
    (ROOT / "benchmark" / "DATA_CARD.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:16]))


if __name__ == "__main__":
    main()
