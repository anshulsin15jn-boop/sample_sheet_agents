"""Tests for method F: each tool, and the agent loop with a scripted fake tool calling model."""
import pytest

from src.agent import (ToolError, check_mapping, coerce_mapping, get_row_values, list_rows, run_agent,
                       run_tool)
from src.grading import grade
from src.llm import ScriptedToolLLM
from src.methods import run_method

from tests.test_benchmark import toy_cohort

GOOD_MAP = {"disease state: asthma": "disease", "disease state: control": "control"}


def call(name, **args):
    return {"name": name, "arguments": args}


# ----------------------------------------------------------------------------- tools
def test_list_rows():
    rows = {r["row_id"]: r for r in list_rows(toy_cohort())["rows"]}
    assert set(rows) == {"title", "source", "char_0", "char_1"}
    assert rows["char_0"]["n_distinct_values"] == 2
    assert rows["source"]["n_distinct_values"] == 1
    assert rows["char_1"]["examples"] == ["age: 30", "age: 41", "age: 52"]


def test_get_row_values_counts():
    out = get_row_values(toy_cohort(), "char_0")
    assert out["values"] == [{"value": "disease state: asthma", "n_samples": 2},
                             {"value": "disease state: control", "n_samples": 1}]
    with pytest.raises(ToolError, match="does not exist"):
        get_row_values(toy_cohort(), "char_9")


def test_check_mapping_reports_unlabelled_and_unknown_values():
    out = check_mapping(toy_cohort(), "char_0", {"disease state: asthma": "disease", "healthy": "control"})
    assert not out["ok"]
    assert out["unlabelled_values"] == ["disease state: control"]
    assert out["values_not_in_row"] == ["healthy"]
    assert check_mapping(toy_cohort(), "char_0", GOOD_MAP)["ok"]


def test_check_mapping_warns_on_single_value_row():
    out = check_mapping(toy_cohort(), "source", {"blood": "disease"})
    assert not out["ok"] and "only one distinct value" in out["problems"][0]


def test_check_mapping_rejects_bad_labels():
    out = check_mapping(toy_cohort(), "char_0", {"disease state: asthma": "case",
                                                 "disease state: control": "control"})
    assert out["invalid_labels"] == ["disease state: asthma"] and not out["ok"]


def test_coerce_mapping_shapes():
    assert coerce_mapping('{"a": "disease"}') == {"a": "disease"}
    assert coerce_mapping([{"value": "a", "label": "control"}]) == {"a": "control"}
    for bad in ("not json", {}, [1, 2], 5):
        with pytest.raises(ToolError):
            coerce_mapping(bad)


def test_submit_answer_validates_like_other_methods():
    result, ans = run_tool(toy_cohort(), "submit_answer", {"row_id": "char_0", "mapping": GOOD_MAP})
    assert result == {"status": "accepted"} and ans["parsed"].valid
    with pytest.raises(ToolError, match="answer rejected"):
        run_tool(toy_cohort(), "submit_answer", {"row_id": "char_0", "mapping": {"zzz": "disease"}})
    with pytest.raises(ToolError, match="unknown tool"):
        run_tool(toy_cohort(), "delete_everything", {})
    with pytest.raises(ToolError, match="needs the argument"):
        run_tool(toy_cohort(), "get_row_values", {})
    with pytest.raises(ToolError, match="not valid JSON"):
        run_tool(toy_cohort(), "get_row_values", "{row_id: char_0")


# ----------------------------------------------------------------------------- the loop
def test_loop_happy_path_with_flag_and_fix():
    llm = ScriptedToolLLM([
        {"tool_calls": [call("list_rows")]},
        {"tool_calls": [call("get_row_values", row_id="char_0")]},
        {"tool_calls": [call("check_mapping", row_id="char_0", mapping={"disease state: asthma": "disease"})]},
        {"tool_calls": [call("submit_answer", row_id="char_0", mapping=GOOD_MAP)]},
    ])
    res = run_agent(toy_cohort(), llm, seed=1)
    assert res.valid and res.row == "char_0"
    assert grade(toy_cohort(), res.row, res.mapping)["accuracy"] == 1
    a = res.agent
    assert a["n_tool_calls"] == 4 and a["stop"] == "submitted"
    assert a["flagged"] and a["final_check_ok"] and a["fixed_after_flag"]
    assert [t["name"] for t in llm.tool_log] == ["list_rows", "get_row_values", "check_mapping", "submit_answer"]
    # the check result was sent back to the model as a tool message
    assert '"unlabelled_values": ["disease state: control"]' in llm.calls[3]["messages"][-1]["content"]


def test_loop_recovers_from_malformed_and_unknown_calls():
    llm = ScriptedToolLLM([
        {"tool_calls": [{"name": "get_row_values", "arguments": "{row_id: char_0"}]},   # malformed JSON
        {"tool_calls": [call("magic_answer")]},                                         # unknown tool
        {"error": "server error 500: error parsing tool call"},                         # rejected call
        {"content": "The answer is char_0."},                                           # no tool call
        {"tool_calls": [call("submit_answer", row_id="char_0", mapping=GOOD_MAP)]},
    ])
    res = run_agent(toy_cohort(), llm, seed=1)
    assert res.valid and res.agent["n_steps"] == 5
    assert res.agent["errors"] == {"bad arguments": 1, "unknown tool": 1, "call error": 1, "no tool call": 1}
    assert "not valid JSON" in llm.calls[1]["messages"][-1]["content"]
    assert "unknown tool" in llm.calls[2]["messages"][-1]["content"]
    assert llm.calls[4]["messages"][-1]["content"].startswith("Please continue by calling a tool")


def test_loop_budget_exhausted_is_invalid():
    llm = ScriptedToolLLM([{"tool_calls": [call("list_rows")]}] * 20)
    res = run_agent(toy_cohort(), llm, seed=1, max_tool_calls=8)
    assert not res.valid and "no valid submit_answer within 8" in res.invalid_reason
    assert res.agent["n_tool_calls"] == 8 and len(llm.calls) == 8


def test_loop_counts_every_call_in_a_turn_against_the_budget():
    llm = ScriptedToolLLM([{"tool_calls": [call("list_rows")] * 10}])
    res = run_agent(toy_cohort(), llm, seed=1, max_tool_calls=8)
    assert not res.valid and res.agent["n_tool_calls"] == 8 and len(llm.calls) == 1


def test_loop_retry_after_rejected_submit():
    llm = ScriptedToolLLM([
        {"tool_calls": [call("submit_answer", row_id="char_9", mapping=GOOD_MAP)]},
        {"tool_calls": [call("submit_answer", row_id="char_0", mapping=GOOD_MAP)]},
    ])
    res = run_agent(toy_cohort(), llm, seed=1)
    assert res.valid and res.agent["n_tool_calls"] == 2 and not res.agent["flagged"]


def test_run_method_dispatches_F():
    llm = ScriptedToolLLM([{"tool_calls": [call("submit_answer", row_id="char_0", mapping=GOOD_MAP)]}])
    res = run_method("F", toy_cohort(), llm, seed=1)
    assert res.method == "F" and res.valid and res.agent["n_tool_calls"] == 1


def test_recover_tool_calls_written_as_text():
    from src.agent import recover_tool_calls
    text = 'Sure.\n```json\n{"name": "get_row_values", "arguments": {"row_id": "char_0"}}\n```'
    assert recover_tool_calls(text) == [{"name": "get_row_values", "arguments": {"row_id": "char_0"},
                                         "recovered": True}]
    assert recover_tool_calls('{"name": "not_a_tool", "arguments": {}}') == []
    assert recover_tool_calls("no json here {broken") == []


def test_loop_runs_recovered_text_calls_and_flags_them():
    sub = '```json\n{"name": "submit_answer", "arguments": {"row_id": "char_0", "mapping": ' \
          '{"disease state: asthma": "disease", "disease state: control": "control"}}}\n```'
    llm = ScriptedToolLLM([{"content": '```json\n{"name": "list_rows", "arguments": {}}\n```'}, {"content": sub}])
    res = run_agent(toy_cohort(), llm, seed=1)
    assert res.valid and res.agent["n_recovered"] == 2 and res.agent["errors"] == {"recovered from text": 2}
    assert llm.calls[1]["messages"][-1]["role"] == "tool"
