"""Tests for answer parsing, key matching, and the method pipelines (with a scripted fake LLM)."""
import json

from src.cohort import load_cohort
from src.grading import grade
from src.llm import ScriptedLLM
from src.methods import parse_answer, resolve_keys, run_method
from src.prompts import EXAMPLE_IDS, build_messages, gold_answer

from tests.test_benchmark import toy_cohort

GOOD = json.dumps({"row": "char_0", "mapping": {"disease state: asthma": "disease",
                                                "disease state: control": "control"}})


def test_parse_valid_simple():
    p = parse_answer(GOOD, toy_cohort())
    assert p.valid and p.row == "char_0" and p.mapping["disease state: control"] == "control"


def test_parse_reasoned_format_and_code_fence():
    text = "```json\n" + json.dumps({"row": "char_0", "row_reason": "x", "mapping": {
        "disease state: asthma": {"reason": "asthma", "label": "disease"},
        "disease state: control": {"reason": "ctrl", "label": "Control"}}}) + "\n```"
    p = parse_answer(text, toy_cohort())
    assert p.valid and p.mapping == {"disease state: asthma": "disease", "disease state: control": "control"}
    assert p.reasons["disease state: asthma"] == "asthma"


def test_parse_invalid_cases():
    c = toy_cohort()
    assert parse_answer("not json", c).reason == "not valid JSON"
    assert not parse_answer(json.dumps({"row": "char_9", "mapping": {"a": "disease"}}), c).valid
    assert not parse_answer(json.dumps({"row": "char_0", "mapping": {}}), c).valid
    assert not parse_answer(json.dumps({"row": "char_0", "mapping": {"zzz": "disease"}}), c).valid
    assert not parse_answer(json.dumps({"cannot_determine": True}), c).valid          # not allowed
    assert parse_answer(json.dumps({"cannot_determine": True, "row": None}), c, allow_abstain=True).cannot_determine


def test_bad_labels_and_unsure():
    c = toy_cohort()
    t = json.dumps({"row": "char_0", "mapping": {"disease state: asthma": "case",
                                                 "disease state: control": "unsure"}})
    p = parse_answer(t, c)
    assert p.valid and p.bad_labels == 2 and set(p.mapping.values()) == {"unknown"}
    p = parse_answer(t, c, allow_abstain=True)
    assert p.bad_labels == 1 and p.mapping["disease state: control"] == "unsure"


def test_resolve_keys_tolerates_case_and_missing_prefix():
    vals = ["disease state: asthma", "disease state: control"]
    r = resolve_keys(vals, ["Disease State: Asthma ", "control", "other"])
    assert r == {"Disease State: Asthma ": "disease state: asthma", "control": "disease state: control",
                 "other": None}


def test_method_A_with_scripted_llm():
    llm = ScriptedLLM([GOOD])
    res = run_method("A", toy_cohort(), llm, seed=1)
    assert res.valid and res.n_calls == 1
    assert grade(toy_cohort(), res.row, res.mapping)["accuracy"] == 1
    assert "Trait: Asthma" in llm.calls[0]["messages"][1]["content"]


def test_method_E_revision_flow():
    wrong = json.dumps({"row": "char_0", "mapping": {"disease state: asthma": "control",
                                                     "disease state: control": "disease"}})
    review = json.dumps({"verdict": "revise", "problems": ["labels are flipped"]})
    llm = ScriptedLLM([wrong, review, GOOD])
    res = run_method("E", toy_cohort(), llm, seed=1)
    assert res.n_calls == 3 and res.checker["revised"] and res.checker["revision_valid"]
    assert grade(toy_cohort(), res.row, res.mapping)["accuracy"] == 1
    assert "labels are flipped" in llm.calls[2]["messages"][-1]["content"]


def test_method_E_accept_and_bad_revision():
    llm = ScriptedLLM([GOOD, json.dumps({"verdict": "accept", "problems": []})])
    res = run_method("E", toy_cohort(), llm, seed=1)
    assert res.n_calls == 2 and not res.checker["revised"]
    llm = ScriptedLLM([GOOD, json.dumps({"verdict": "revise", "problems": ["x"]}), "garbage"])
    res = run_method("E", toy_cohort(), llm, seed=1)
    assert res.valid and res.checker["revision_valid"] is False and res.row == "char_0"


def test_method_R_needs_no_llm():
    res = run_method("R", toy_cohort())
    assert res.valid and res.n_calls == 0 and res.row == "char_0"


def test_examples_are_dev_and_gold_is_perfect():
    for cid in EXAMPLE_IDS:
        c = load_cohort(cid)
        assert c["split"] == "dev"
        g = gold_answer(c)
        assert grade(c, g["row"], g["mapping"])["accuracy"] == 1


def test_prompts_contain_examples_only_when_expected():
    c = load_cohort("GSE120490")
    assert "Example 1" not in build_messages("A", c)[1]["content"]
    for m in "BCDE":
        assert "Example 3" in build_messages(m, c)[1]["content"]
    assert "unsure" in build_messages("D", c)[1]["content"]
    assert "unsure" not in build_messages("C", c)[1]["content"]
