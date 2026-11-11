"""Every reference solution must pass its own grader when run inside the sandbox,
and the 'naive' answers recorded for traps must actually be graded as wrong."""
import copy

import pytest

from src.grader import grade, parse_answer
from src.sandbox import run_code
from src.tasks import all_task_ids, load_task

TASK_IDS = all_task_ids()


def test_benchmark_has_20_tasks_with_6_traps():
    assert len(TASK_IDS) == 20
    keys = [load_task(t).key for t in TASK_IDS]
    traps = [k for k in keys if k["trap"]]
    assert len(traps) == 6
    assert sum(k["trap"]["type"] == "injection" for k in traps) == 2


@pytest.mark.parametrize("task_id", TASK_IDS)
def test_reference_solution_passes(task_id):
    task = load_task(task_id)
    code = (task.folder / "reference.py").read_text()
    res = run_code(code, data_dir=task.data_dir, timeout_s=120)
    assert res.ok, res.stderr
    g = grade(res.stdout, task.key)
    assert g.parsed and g.success, (g.field_correct, g.answer)
    assert not g.trap_fell
    if g.is_trap:
        assert g.trap_handled


@pytest.mark.parametrize("task_id", [t for t in TASK_IDS if "trap" in t])
def test_naive_trap_answer_is_flagged(task_id):
    key = load_task(task_id).key
    check = key["trap"]["checks"][0]
    ans = {name: spec["value"] for name, spec in key["fields"].items()}
    ans[check["field"]] = check["naive_value"]
    import json
    g = grade("ANSWER: " + json.dumps(ans), key)
    assert g.trap_fell and not g.success and not g.trap_handled


def test_parse_answer_variants():
    assert parse_answer("x\nANSWER: {\"a\": 1}\n") == {"a": 1}
    assert parse_answer("ANSWER: {'a': 0.5, 'b': True}") == {"a": 0.5, "b": True}
    assert parse_answer("ANSWER: {'a': np.float64(0.5)}") == {"a": 0.5}
    assert parse_answer("no answer here") is None
    # the last ANSWER line wins
    assert parse_answer("ANSWER: {\"a\": 1}\nANSWER: {\"a\": 2}") == {"a": 2}


def test_grader_tolerance_and_labels():
    key = {"fields": {"x": {"type": "number", "value": 1.0, "tol": 0.01},
                      "f": {"type": "label", "value": "bmi"}}, "trap": None}
    assert grade('ANSWER: {"x": 1.005, "f": "BMI"}', key).success
    assert not grade('ANSWER: {"x": 1.02, "f": "bmi"}', key).success
    assert not grade('ANSWER: {"x": 1.0}', key).success          # missing key
    assert grade('ANSWER: {"X": "1.0", "F": "bmi"}', key).success  # case insensitive keys


def test_parse_answer_doubled_braces():
    assert parse_answer('ANSWER: {{"n": 32}}') == {"n": 32}
