"""Baseline R: a keyword rule with no LLM. Every LLM method has to beat this.

For each metadata value:
  1. If the value (the part after "key:") contains a control word such as control, normal,
     healthy, non, adjacent, unaffected, negative, no, or none, it is a control. Negation comes
     first on purpose, so "non tumor" and "healthy control" are not read as disease.
  2. Else if the value contains a word from the trait name (or its abbreviation), it is disease.
  3. Else if the key (the part before ":") names the trait and the value is yes or positive,
     it is disease (for rows like "asthma status: Yes").
  4. Otherwise unknown.

Row choice: prefer a row whose shown values get both a disease and a control label; among those,
the row with the largest share of its values labelled; ties go to characteristics rows, then
source, then title, then fewer values. If no value in any row matches anything, the rule answers
"cannot determine".
"""
from __future__ import annotations

import re

from .cohort import row_view

CONTROL_WORDS = ["control", "controls", "ctrl", "ctl", "normal", "healthy", "non", "adjacent",
                 "unaffected", "uninfected", "wild type", "wildtype", "wt", "negative", "neg",
                 "no", "none", "absent", "benign"]
YES_WORDS = ["yes", "positive", "pos", "true", "present", "affected"]
GENERIC = {"disease", "disorder", "syndrome", "levels", "type", "chronic", "acute", "and", "the",
           "of", "with", "cell", "systemic"}


def _norm(s: str) -> str:
    s = s.lower().replace("'", "").replace("’", "")
    return re.sub(r"\s+", " ", re.sub(r"[_\-/,;()\[\]]+", " ", s)).strip()


def _has_word(text: str, word: str) -> bool:
    return re.search(r"(?<![a-z0-9])" + re.escape(word) + r"(?![a-z0-9])", text) is not None


def trait_keywords(trait: str) -> list[str]:
    t = _norm(trait)
    words = [w for w in t.split() if len(w) >= 3 and w not in GENERIC]
    kws = {t.strip()} | set(words)
    abbrev = re.findall(r"\(([^)]+)\)", trait)          # e.g. "(COPD)"
    kws |= {_norm(a).strip() for a in abbrev}
    kws |= {w[:-1] for w in words if w.endswith("s") and len(w) > 5}   # huntingtons -> huntington
    return sorted(k for k in kws if k)


def label_value(value: str, trait: str) -> str:
    key, _, val = value.partition(":") if ":" in value else ("", "", value)
    v, k = _norm(val), _norm(key)
    if any(_has_word(v, w) for w in CONTROL_WORDS):
        return "control"
    kws = trait_keywords(trait)
    if any(_has_word(v, w) for w in kws):
        return "disease"
    if k and any(_has_word(k, w) for w in kws) and any(_has_word(v, w) for w in YES_WORDS):
        return "disease"
    return "unknown"


_ROW_PRIORITY = {"title": 2, "source": 1}


def rule_answer(cohort: dict) -> dict:
    """Return {"row", "mapping", "cannot_determine"} in the same format as the LLM methods."""
    best, best_key = None, None
    for row in cohort["rows"]:
        view = row_view(row)
        mapping = {v: label_value(v, cohort["trait"]) for v in view["values"]}
        labs = list(mapping.values())
        n_lab = sum(l != "unknown" for l in labs)
        if n_lab == 0:
            continue
        both = "disease" in labs and "control" in labs
        key = (both, n_lab / len(labs), -_ROW_PRIORITY.get(row["row_id"], 0), -len(labs))
        if best_key is None or key > best_key:
            best, best_key = {"row": row["row_id"], "mapping": mapping}, key
    if best is None:
        return {"row": None, "mapping": {}, "cannot_determine": True}
    return {**best, "cannot_determine": False}
