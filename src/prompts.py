"""Prompt text for every LLM method, plus the three worked examples used by methods B to E.

All methods see the same cohort description (`render_cohort`). They differ only in instructions,
examples, and the answer format they must return.
"""
from __future__ import annotations

import json
from collections import Counter

from .cohort import load_cohort, row_view, sample_key

SYSTEM = ("You are a careful biomedical data curator. You read the sample metadata of a public gene "
          "expression study and decide which samples have a given trait. You always reply with a "
          "single JSON object and nothing else.")

LABEL_DEFS = """Label meanings:
- "disease": samples with this value HAVE the trait.
- "control": samples with this value do NOT have the trait. This includes healthy people and also
  people or samples with a different disease or condition.
- "unknown": the value says nothing about whether the sample has the trait."""


def render_cohort(cohort: dict) -> str:
    lines = [f'Trait: {cohort["trait"]}', f'Study title: {cohort["series_title"]}', "",
             "Metadata rows. Each row lists the distinct values it takes across the samples. "
             '"#" stands for a number in rows that were shortened.']
    for row in cohort["rows"]:
        v = row_view(row)
        extra = f", {v['n_hidden']} more not shown" if v["n_hidden"] else ""
        lines.append(f'Row "{v["row_id"]}" ({v["name"]}, {len(v["values"])} distinct values{extra}): '
                     + json.dumps(v["values"], ensure_ascii=False))
    return "\n".join(lines)


# ----------------------------------------------------------------------------- answer formats
FORMAT_SIMPLE = """Reply with JSON only, in this format:
{"row": "<row id, for example char_0>",
 "mapping": {"<value copied exactly from that row>": "disease" or "control" or "unknown", ...}}
Include every value of the chosen row in the mapping."""

FORMAT_REASONED = """Reply with JSON only, in this format:
{"row": "<row id, for example char_0>",
 "row_reason": "<one short sentence: why this row holds the trait>",
 "mapping": {"<value copied exactly from that row>": {"reason": "<a few words>",
                                                      "label": "disease" or "control" or "unknown"}, ...}}
Include every value of the chosen row. Write the reason first, then the label that follows from it."""

FORMAT_ABSTAIN = """You may abstain. If you are not confident about a value, label it "unsure" instead of
guessing. If no row lets you tell trait samples from the others, set "cannot_determine" to true and
"row" to null. Wrong labels are much worse than "unsure".
Reply with JSON only, in this format:
{"cannot_determine": false,
 "row": "<row id, for example char_0, or null>",
 "row_reason": "<one short sentence>",
 "mapping": {"<value copied exactly from that row>": {"reason": "<a few words>",
                                                      "label": "disease" or "control" or "unknown" or "unsure"}, ...}}
Include every value of the chosen row. Write the reason first, then the label."""

TASK = """Task:
1. Choose the ONE row whose values tell whether a sample has the trait "{trait}".
2. Map every value of that row to a label.

{label_defs}"""

STRUCTURED_TIPS = """Check these before answering:
- Prefer a row whose values directly name the condition or group (diagnosis, disease state, group,
  genotype, tissue type). Sample titles and IDs can also encode the group, for example "C#" vs "P#".
- Watch for negation and controls: "non-tumor", "adjacent normal", "unaffected", "wild type",
  "negative", "No" mean the trait is absent.
- Expand abbreviations and synonyms using the study title (for example "AF" = atrial fibrillation,
  "T21" = Down syndrome, "HD" = Huntington's disease).
- A sample with a different disease than the trait is a control.
- Make sure both groups are covered: most studies have trait samples and comparison samples."""


def task_text(cohort: dict) -> str:
    return TASK.format(trait=cohort["trait"], label_defs=LABEL_DEFS)


# ----------------------------------------------------------------------------- worked examples
# Three development set cohorts, never used for testing. Their mappings come from the expert labels
# (majority label of the samples holding each value); the reasons were written by hand.
EXAMPLE_IDS = ["GSE270312", "GSE112943", "GSE143924"]
EXAMPLE_REASONS = {
    "GSE270312": ("the row is literally named asthma status",
                  {"asthma status: No": "says no asthma", "asthma status: Yes": "says asthma"}),
    "GSE112943": ("tissue names lupus forms and control tissues",
                  {"tissue: CCLE": "chronic cutaneous lupus",
                   "tissue: SCLE": "subacute cutaneous lupus",
                   "tissue: Skin Control": "control skin",
                   "tissue: Kidney Control": "control kidney",
                   "tissue: Lupus Nephritis": "lupus affecting the kidney"}),
    "GSE143924": ("diagnosis separates atrial fibrillation from normal sinus rhythm",
                  {"patient diagnosis: sinus rhythm after surgery": "normal heart rhythm",
                   "patient diagnosis: postoperative atrial fibrillation after surgery (POAF)":
                       "atrial fibrillation"}),
}


def gold_answer(cohort: dict) -> dict:
    """Expert row plus the majority expert label of each displayed value (unknown if no labels)."""
    row = next(r for r in cohort["rows"] if r["row_id"] == cohort["expert_trait_row"])
    votes: dict[str, Counter] = {}
    for s, v in zip(cohort["samples"], row["values"]):
        k = sample_key(row, v)
        votes.setdefault(k, Counter())
        if s in cohort["labels"]:
            votes[k][cohort["labels"][s]] += 1
    mapping = {}
    for k in row_view(row)["values"]:
        c = votes.get(k, Counter())
        mapping[k] = "unknown" if not c else ("disease" if c.most_common(1)[0][0] == 1 else "control")
    return {"row": row["row_id"], "mapping": mapping}


def example_answer(cohort: dict, style: str) -> str:
    g = gold_answer(cohort)
    if style == "simple":
        return json.dumps(g, ensure_ascii=False)
    row_reason, reasons = EXAMPLE_REASONS[cohort["cohort_id"]]
    m = {k: {"reason": reasons.get(k, "not informative"), "label": lab} for k, lab in g["mapping"].items()}
    out = {"row": g["row"], "row_reason": row_reason, "mapping": m}
    if style == "abstain":
        out = {"cannot_determine": False, **out}
    return json.dumps(out, ensure_ascii=False)


def examples_block(style: str) -> str:
    parts = ["Here are three solved examples from other studies.\n"]
    for i, cid in enumerate(EXAMPLE_IDS, 1):
        c = load_cohort(cid)
        parts.append(f"### Example {i}\n{render_cohort(c)}\nAnswer:\n{example_answer(c, style)}\n")
    return "\n".join(parts)


# ----------------------------------------------------------------------------- full prompts
def build_messages(method: str, cohort: dict) -> list[dict]:
    """Messages for the extractor call of methods A, B, C, D (and the first call of E)."""
    style = {"A": "simple", "B": "simple", "C": "reasoned", "D": "abstain", "E": "reasoned"}[method]
    fmt = {"simple": FORMAT_SIMPLE, "reasoned": FORMAT_REASONED, "abstain": FORMAT_ABSTAIN}[style]
    parts = []
    if method != "A":
        parts.append(examples_block(style))
        parts.append("### Your study")
    parts.append(render_cohort(cohort))
    parts.append(task_text(cohort))
    if method in ("C", "D", "E"):
        parts.append(STRUCTURED_TIPS)
    parts.append(fmt)
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": "\n\n".join(parts)}]


CHECKER_SYSTEM = ("You are a strict reviewer checking another curator's work on the sample metadata of a "
                  "gene expression study. You always reply with a single JSON object and nothing else.")

CHECKER_TASK = """Another curator was asked which samples have the trait "{trait}". Their answer is below.

Curator's answer:
{answer}

{label_defs}

Check the answer carefully:
1. Is the chosen row really the one that tells trait samples apart from the others?
2. For each value, is the label right? Look for flipped labels, missed negations ("non", "adjacent",
   "unaffected", "wild type", "No"), missed abbreviations or synonyms, and other diseases that should
   be control.
3. Are all values of the chosen row labelled, and does the answer contain both disease and control
   samples where the study has both?
Only ask for a revision for real mistakes.

Reply with JSON only, in this format:
{{"verdict": "accept" or "revise", "problems": ["<specific problem and how to fix it>", ...]}}"""

REVISE_TASK = """A reviewer checked your answer and found these problems:
{problems}

Fix them if you agree, then reply with the full corrected answer as JSON only, in the same format as
before."""


def checker_messages(cohort: dict, answer_text: str) -> list[dict]:
    body = render_cohort(cohort) + "\n\n" + CHECKER_TASK.format(
        trait=cohort["trait"], answer=answer_text, label_defs=LABEL_DEFS)
    return [{"role": "system", "content": CHECKER_SYSTEM}, {"role": "user", "content": body}]


def revise_message(problems: list[str]) -> dict:
    return {"role": "user", "content": REVISE_TASK.format(problems="\n".join(f"- {p}" for p in problems))}
