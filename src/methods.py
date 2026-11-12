"""The six methods: R (rules) and the LLM methods A to E.

    R  keyword rule, no LLM
    A  zero shot: trait plus unique values, return row and mapping
    B  few shot: A plus three worked examples from the development set
    C  structured reasoning: B plus a short reason per value and a checklist
    D  abstention: C plus "unsure" per value and "cannot determine" for the whole cohort
    E  extractor plus checker: C, then a checker agent reviews it and can send it back once

Every LLM answer must be one JSON object. It is checked here; an answer that cannot be parsed or
has the wrong structure counts as invalid (a failure) and is logged with the reason.

Matching the model's value keys to the real values: keys are matched exactly, then ignoring case
and surrounding spaces, then (if the model dropped the "key: " prefix) by the part after the colon
when that is unique. Keys that still match nothing are counted as unmatched, and the samples with
those values stay unknown.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass, field

from .cohort import row_view
from .prompts import build_messages, checker_messages, revise_message
from .rules import rule_answer

LLM_METHODS = ["A", "B", "C", "D", "E"]
ALL_METHODS = ["R"] + LLM_METHODS
OK_LABELS = {"disease", "control", "unknown", "unsure"}


@dataclass
class Parsed:
    valid: bool
    reason: str = ""                       # why it is invalid, if it is
    row: str | None = None
    mapping: dict = field(default_factory=dict)   # shown value -> label
    cannot_determine: bool = False
    unmatched_keys: list = field(default_factory=list)
    bad_labels: int = 0
    reasons: dict = field(default_factory=dict)   # shown value -> model's reason (methods C to E)


def _load_json(text: str):
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", t, flags=re.S)   # a JSON object with chatter around it
        if m:
            return json.loads(m.group(0))
        raise


def resolve_keys(view_values: list[str], keys: list[str]) -> dict:
    """Map each model key to a shown value (or None)."""
    exact = {v: v for v in view_values}
    folded = {v.strip().casefold(): v for v in view_values}
    after: dict[str, list[str]] = {}
    for v in view_values:
        if ":" in v:
            after.setdefault(v.split(":", 1)[1].strip().casefold(), []).append(v)
    out = {}
    for k in keys:
        ks = str(k)
        if ks in exact:
            out[k] = ks
        elif ks.strip().casefold() in folded:
            out[k] = folded[ks.strip().casefold()]
        elif len(after.get(ks.strip().casefold(), [])) == 1:
            out[k] = after[ks.strip().casefold()][0]
        else:
            out[k] = None
    return out


def parse_answer(text: str, cohort: dict, allow_abstain: bool = False) -> Parsed:
    try:
        obj = _load_json(text)
    except (json.JSONDecodeError, ValueError):
        return Parsed(False, "not valid JSON")
    if not isinstance(obj, dict):
        return Parsed(False, "JSON is not an object")
    cd = obj.get("cannot_determine") is True
    if cd:
        if not allow_abstain:
            return Parsed(False, "cannot_determine used where not allowed")
        return Parsed(True, cannot_determine=True)
    rows = {r["row_id"]: r for r in cohort["rows"]}
    row = obj.get("row")
    if not isinstance(row, str) or row.strip() not in rows:
        return Parsed(False, f"row {row!r} is not one of the row ids")
    row = row.strip()
    raw = obj.get("mapping")
    if not isinstance(raw, dict) or not raw:
        return Parsed(False, "mapping missing or empty")
    view = row_view(rows[row])
    res = resolve_keys(view["values"], list(raw))
    mapping, reasons, unmatched, bad = {}, {}, [], 0
    for k, v in raw.items():
        reason = ""
        if isinstance(v, dict):
            reason = str(v.get("reason", ""))
            v = v.get("label")
        lab = str(v).strip().lower() if v is not None else ""
        if lab not in OK_LABELS or (lab == "unsure" and not allow_abstain):
            bad += 1
            lab = "unknown"
        if res[k] is None:
            unmatched.append(str(k))
            continue
        mapping[res[k]] = lab
        if reason:
            reasons[res[k]] = reason
    if not mapping:
        return Parsed(False, "no mapping key matches a value of the chosen row", row=row,
                      unmatched_keys=unmatched)
    return Parsed(True, row=row, mapping=mapping, unmatched_keys=unmatched, bad_labels=bad,
                  reasons=reasons)


@dataclass
class MethodResult:
    method: str
    row: str | None
    mapping: dict
    cannot_determine: bool
    valid: bool
    invalid_reason: str
    n_calls: int
    seconds: float
    prompt_tokens: int
    completion_tokens: int
    unmatched_keys: list
    bad_labels: int
    reasons: dict = field(default_factory=dict)
    checker: dict = field(default_factory=dict)   # method E only
    raw: list = field(default_factory=list)       # raw model outputs, in order

    def to_dict(self) -> dict:
        return asdict(self)


def _call(llm, messages, role, seed, meta, acc):
    r = llm.chat(messages, role=role, seed=seed, meta=meta, json_mode=True)
    acc["n"] += 1
    acc["pt"] += r.prompt_tokens
    acc["ct"] += r.completion_tokens
    acc["raw"].append(r.text)
    return r.text


def run_method(method: str, cohort: dict, llm=None, seed: int | None = None, meta: dict | None = None
               ) -> MethodResult:
    t0 = time.perf_counter()
    if method == "R":
        a = rule_answer(cohort)
        return MethodResult("R", a["row"], a["mapping"], a["cannot_determine"], True, "", 0,
                            time.perf_counter() - t0, 0, 0, [], 0)
    acc = {"n": 0, "pt": 0, "ct": 0, "raw": []}
    meta = {**(meta or {}), "cohort": cohort["cohort_id"], "method": method}
    msgs = build_messages(method, cohort)
    text = _call(llm, msgs, f"extractor_{method}", seed, meta, acc)
    p = parse_answer(text, cohort, allow_abstain=(method == "D"))
    checker = {}
    if method == "E" and p.valid:
        ctext = _call(llm, checker_messages(cohort, text), "checker", seed, meta, acc)
        verdict, problems, cvalid = "accept", [], True
        try:
            cobj = _load_json(ctext)
            verdict = str(cobj.get("verdict", "accept")).strip().lower()
            problems = [str(x) for x in (cobj.get("problems") or []) if str(x).strip()]
        except (json.JSONDecodeError, ValueError, AttributeError):
            cvalid = False   # an unreadable review is treated as "accept"
        checker = {"valid": cvalid, "verdict": verdict, "problems": problems, "revised": False,
                   "revision_valid": None, "first_row": p.row, "first_mapping": p.mapping}
        if cvalid and verdict == "revise" and problems:
            msgs2 = msgs + [{"role": "assistant", "content": text}, revise_message(problems)]
            rtext = _call(llm, msgs2, "extractor_E_revision", seed, meta, acc)
            p2 = parse_answer(rtext, cohort)
            checker["revised"] = True
            checker["revision_valid"] = p2.valid
            if p2.valid:   # an invalid revision falls back to the first answer
                p = p2
    return MethodResult(method, p.row, p.mapping, p.cannot_determine, p.valid, p.reason, acc["n"],
                        time.perf_counter() - t0, acc["pt"], acc["ct"], p.unmatched_keys, p.bad_labels,
                        p.reasons, checker, acc["raw"])
