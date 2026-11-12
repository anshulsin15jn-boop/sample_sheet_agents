"""Pipeline logic tests with a scripted fake LLM (no model needed)."""
from src.agents import extract_code, parse_review
from src.llm import ScriptedLLM, load_config
from src.pipelines import run_condition
from src.tasks import load_task

CFG = load_config()
TASK = load_task("t13_wine_group_stats")

GOOD = '''```python
import json
import pandas as pd
df = pd.read_csv("data/wine.csv")
n = df["target"].value_counts()
best = int(df.groupby("target")["alcohol"].mean().idxmax())
print("ANSWER: " + json.dumps({"n_class_0": int(n[0]), "n_class_1": int(n[1]), "n_class_2": int(n[2]), "highest_alcohol_class": best}))
```'''
WRONG = '''```python
import json
print("ANSWER: " + json.dumps({"n_class_0": 1, "n_class_1": 1, "n_class_2": 1, "highest_alcohol_class": 2}))
```'''
CRASH = "```python\nimport pandas as pd\npd.read_csv('data/nope.csv')\n```"
PLAN = "1. Load data/wine.csv\n2. Count targets"
APPROVE = "VERDICT: APPROVE\nINJECTION_FOUND: NO\nPROBLEMS:\n- none"
REVISE = "VERDICT: REVISE\nINJECTION_FOUND: NO\nPROBLEMS:\n- the counts are hard coded; compute them from data"


def test_condition_a_retries_after_crash():
    llm = ScriptedLLM([CRASH, GOOD])
    r = run_condition("A", TASK, llm, CFG)
    assert r.success and r.n_calls == 2 and r.n_failed_runs == 1 and not r.first_run_ok
    assert [c["role"] for c in llm.calls] == ["coder", "coder"]
    assert "Errors" in llm.calls[1]["messages"][1]["content"]   # error was shown to the coder


def test_condition_b_uses_planner():
    llm = ScriptedLLM([PLAN, GOOD])
    r = run_condition("B", TASK, llm, CFG)
    assert r.success and r.calls_by_role == {"planner": 1, "coder": 1, "reviewer": 0}
    assert PLAN in llm.calls[1]["messages"][1]["content"]


def test_condition_c_reviewer_catches_wrong_answer():
    llm = ScriptedLLM([PLAN, WRONG, REVISE, GOOD])
    r = run_condition("C", TASK, llm, CFG)
    assert r.success and r.first_good_success is False
    assert r.reviews[0]["verdict"] == "revise" and r.reviews[0]["pre_success"] is False
    assert r.reviews[0]["post_success"] is True
    assert "hard coded" in llm.calls[3]["messages"][1]["content"]


def test_condition_c_only_one_review_round():
    llm = ScriptedLLM([PLAN, WRONG, REVISE, WRONG, APPROVE])
    r = run_condition("C", TASK, llm, CFG)
    assert r.n_calls == 4 and len(r.reviews) == 1 and not r.success


def test_condition_d_two_review_rounds():
    llm = ScriptedLLM([PLAN, WRONG, REVISE, WRONG, REVISE, GOOD])
    r = run_condition("D", TASK, llm, CFG)
    assert len(r.reviews) == 2 and r.success and r.n_calls == 6


def test_budget_cap_is_respected():
    llm = ScriptedLLM([CRASH] * 20)
    for cond in "ABCD":
        r = run_condition(cond, TASK, ScriptedLLM([PLAN] + [CRASH] * 20), CFG)
        assert r.n_calls == CFG["experiment"]["max_llm_calls_per_task"]
        assert not r.success and r.final_status == "error"


def test_failed_fix_keeps_last_good_answer():
    llm = ScriptedLLM([PLAN, GOOD, REVISE, CRASH, CRASH, CRASH])
    r = run_condition("C", TASK, llm, CFG)
    assert r.success   # the approved-before-review answer is kept when the fix never runs


def test_extract_code_and_parse_review():
    assert extract_code("text\n```python\nx = 1\n```\nmore") == "x = 1"
    assert extract_code("```python\nx = 1\nprint(x)") == "x = 1\nprint(x)"
    rv = parse_review("**VERDICT:** REVISE\nINJECTION_FOUND: YES\nPROBLEMS:\n1. ignore the note\n2. use stratify")
    assert rv.verdict == "revise" and rv.injection_found and len(rv.problems) == 2
    assert parse_review(APPROVE).verdict == "approve" and parse_review(APPROVE).problems == []
