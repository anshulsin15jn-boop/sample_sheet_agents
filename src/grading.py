"""Grade an answer for one cohort against the GenoTEX expert labels.

Only samples the experts labelled (0 or 1) are graded. A sample the method left as unknown or
unsure counts as wrong for accuracy and F1, and as "not covered" for coverage.

Metrics for one cohort:
  accuracy            correct samples / labelled samples
  macro_f1            mean of the F1 for disease and the F1 for control
  coverage            share of labelled samples that got a disease or control label
  selective_accuracy  accuracy on the covered samples only (None if nothing was covered)
  row_correct         the chosen row can explain the expert labels (it is in the cohort's
                      valid_rows, see the data card), or the answer solved the cohort with it
  solved              accuracy >= 0.95, our cohort level pass mark
"""
from __future__ import annotations

from .cohort import apply_mapping

SOLVED_AT = 0.95


def _f1(tp: int, fp: int, fn: int) -> float:
    return 0.0 if tp == 0 else 2 * tp / (2 * tp + fp + fn)


def grade(cohort: dict, row: str | None, mapping: dict, cannot_determine: bool = False) -> dict:
    labels = cohort["labels"]
    preds = {s: None for s in labels} if cannot_determine else apply_mapping(cohort, row, mapping)
    n = len(labels)
    correct = covered = 0
    tp = {0: 0, 1: 0}
    fp = {0: 0, 1: 0}
    fn = {0: 0, 1: 0}
    for s, y in labels.items():
        p = preds.get(s)
        if p is not None:
            covered += 1
            if p != y:
                fp[p] += 1
        if p == y:
            correct += 1
            tp[y] += 1
        else:
            fn[y] += 1
    acc = correct / n
    return {
        "accuracy": acc,
        "macro_f1": (_f1(tp[0], fp[0], fn[0]) + _f1(tp[1], fp[1], fn[1])) / 2,
        "coverage": covered / n,
        "selective_accuracy": (correct / covered) if covered else None,
        "row_correct": (not cannot_determine) and (row in cohort["valid_rows"] or acc >= SOLVED_AT),
        "solved": acc >= SOLVED_AT,
        "n_graded": n,
    }
