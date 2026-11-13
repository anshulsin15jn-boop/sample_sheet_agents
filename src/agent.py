"""Method F: a tool calling agent.

Instead of reading all metadata in one prompt, the model works through tools (Ollama's native
`tools` parameter):

    list_rows()                       every row id, its number of distinct values, 3 example values
    get_row_values(row_id)            the distinct values of one row with per value sample counts
    check_mapping(row_id, mapping)    values still unlabelled, labels for values not in the row,
                                      and a warning if the row has only one distinct value
    submit_answer(row_id, mapping)    the final answer, validated like every other method

The tools target the two largest error types of methods A to E: values left unlabelled and a
wrong row (for example a row whose single value is the disease name, as in GSE174570).

Error handling in the loop:
  * at most MAX_TOOL_CALLS tool calls per cohort; a turn without any tool call also uses one step,
    so a model that only writes text cannot loop forever
  * an unknown tool, malformed arguments, or a rejected tool call is answered with an error message
    as the tool result, and the model may continue
  * every model call has its own timeout; a timeout is reported to the model like an error
  * a tool call written as text instead of through the tool interface (qwen2.5-coder:3b writes
    them as JSON in a code block, which Ollama does not parse) is recovered from the text, run,
    and flagged as "recovered", so its share can be reported per model
  * a submit_answer that fails validation is answered with the reason, and the model may retry
  * if no valid answer is submitted within the budget, the attempt is invalid
Every model call and every tool execution is logged to calls.jsonl.
"""
from __future__ import annotations

import json
import re
import time
from collections import Counter

from .cohort import row_view, sample_key
from .methods import MethodResult, parse_answer, resolve_keys
from .prompts import LABEL_DEFS

MAX_TOOL_CALLS = 8
LABELS_OK = ("disease", "control", "unknown")

TOOLS = [
    {"type": "function", "function": {
        "name": "list_rows",
        "description": "List every metadata row of the study: its row_id, a short description, the number "
                       "of distinct values, and up to 3 example values.",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "get_row_values",
        "description": "Get all distinct values of one metadata row, with how many samples have each value.",
        "parameters": {"type": "object", "properties": {
            "row_id": {"type": "string", "description": "a row id from list_rows, for example char_0"}},
            "required": ["row_id"]}}},
    {"type": "function", "function": {
        "name": "check_mapping",
        "description": "Check a draft answer before submitting it. Reports values of the row that have no "
                       "label yet, labels given to values that are not in the row, and whether the row can "
                       "separate samples at all.",
        "parameters": {"type": "object", "properties": {
            "row_id": {"type": "string", "description": "the chosen row id"},
            "mapping": {"type": "object", "description": "value -> label, where label is disease, control, "
                                                         "or unknown. Keys are values copied exactly from the row.",
                        "additionalProperties": {"type": "string", "enum": list(LABELS_OK)}}},
            "required": ["row_id", "mapping"]}}},
    {"type": "function", "function": {
        "name": "submit_answer",
        "description": "Submit the final answer: the chosen row and a label for every value of that row. "
                       "This ends the task.",
        "parameters": {"type": "object", "properties": {
            "row_id": {"type": "string", "description": "the chosen row id"},
            "mapping": {"type": "object", "description": "value -> label (disease, control, or unknown) "
                                                         "for every value of the row",
                        "additionalProperties": {"type": "string", "enum": list(LABELS_OK)}}},
            "required": ["row_id", "mapping"]}}},
]
TOOL_NAMES = {t["function"]["name"] for t in TOOLS}

SYSTEM_F = ("You are a careful biomedical data curator. You read the sample metadata of a public gene "
            "expression study and decide which samples have a given trait. You work only by calling the "
            "tools you are given.")

TASK_F = """Trait: {trait}
Study title: {title}

Task:
1. Find the ONE metadata row whose values tell whether a sample has the trait "{trait}".
2. Label every value of that row.

{label_defs}

Use the tools: call list_rows first, then get_row_values for the rows that look relevant, then
check_mapping on your draft, fix any problem it reports, and finally call submit_answer. Copy values
exactly as the tools show them. You can make at most {budget} tool calls in total."""


def agent_messages(cohort: dict) -> list[dict]:
    return [{"role": "system", "content": SYSTEM_F},
            {"role": "user", "content": TASK_F.format(trait=cohort["trait"], title=cohort["series_title"],
                                                      label_defs=LABEL_DEFS, budget=MAX_TOOL_CALLS)}]


# ----------------------------------------------------------------------------- the tools
class ToolError(Exception):
    """A problem with a tool call that is reported back to the model."""


def _rows(cohort):
    return {r["row_id"]: r for r in cohort["rows"]}


def _row(cohort, row_id):
    if not isinstance(row_id, str) or row_id.strip() not in _rows(cohort):
        raise ToolError(f"row_id {row_id!r} does not exist. Call list_rows to see the valid row ids.")
    return _rows(cohort)[row_id.strip()]


def _value_counts(row: dict) -> Counter:
    return Counter(sample_key(row, v) for v in row["values"])


def list_rows(cohort: dict) -> dict:
    out = []
    for r in cohort["rows"]:
        v = row_view(r)
        out.append({"row_id": r["row_id"], "description": r["name"],
                    "n_distinct_values": len(v["values"]) + v["n_hidden"], "examples": v["values"][:3]})
    return {"rows": out}


def get_row_values(cohort: dict, row_id) -> dict:
    row = _row(cohort, row_id)
    v = row_view(row)
    counts = _value_counts(row)
    out = {"row_id": row["row_id"], "description": row["name"],
           "values": [{"value": x, "n_samples": counts.get(x, 0)} for x in v["values"]]}
    if v["collapsed"]:
        out["note"] = 'numbers in this row were replaced by "#"; use the values exactly as shown'
    if v["n_hidden"]:
        out["note"] = (out.get("note", "") + f"; {v['n_hidden']} more values not shown").lstrip("; ")
    return out


def coerce_mapping(mapping) -> dict:
    """Accept the shapes small models produce: an object, a JSON string of one, or a list of pairs."""
    if isinstance(mapping, str):
        try:
            mapping = json.loads(mapping)
        except json.JSONDecodeError:
            raise ToolError("mapping must be a JSON object of value -> label, not a plain string.")
    if isinstance(mapping, list):
        out = {}
        for item in mapping:
            if isinstance(item, dict) and "value" in item and "label" in item:
                out[str(item["value"])] = item["label"]
            else:
                raise ToolError("mapping must be an object like {\"value\": \"disease\"}.")
        mapping = out
    if not isinstance(mapping, dict) or not mapping:
        raise ToolError("mapping must be a non empty object of value -> label.")
    return {str(k): v for k, v in mapping.items()}


def check_mapping(cohort: dict, row_id, mapping) -> dict:
    row = _row(cohort, row_id)
    mapping = coerce_mapping(mapping)
    v = row_view(row)
    res = resolve_keys(v["values"], list(mapping))
    labelled = {res[k] for k in mapping if res[k] is not None}
    not_in_row = [k for k in mapping if res[k] is None]
    bad_labels = [k for k, lab in mapping.items() if str(lab).strip().lower() not in LABELS_OK]
    unlabelled = [x for x in v["values"] if x not in labelled]
    problems = []
    if len(v["values"]) + v["n_hidden"] <= 1:
        problems.append("this row has only one distinct value, so it cannot separate samples with the trait "
                        "from the others; choose a row whose values differ between samples")
    if unlabelled:
        problems.append(f"{len(unlabelled)} values of the row have no label yet")
    if not_in_row:
        problems.append(f"{len(not_in_row)} labels are for values that are not in this row")
    if bad_labels:
        problems.append("labels must be disease, control, or unknown")
    return {"row_id": row["row_id"], "ok": not problems, "problems": problems,
            "unlabelled_values": unlabelled, "values_not_in_row": not_in_row,
            "invalid_labels": bad_labels}


def run_tool(cohort: dict, name, args) -> tuple[dict, dict | None]:
    """Execute one tool call. Returns (result for the model, parsed answer if submit_answer succeeded)."""
    if name not in TOOL_NAMES:
        raise ToolError(f"unknown tool {name!r}. Available tools: {', '.join(sorted(TOOL_NAMES))}.")
    if isinstance(args, str):
        try:
            args = json.loads(args) if args.strip() else {}
        except json.JSONDecodeError:
            raise ToolError("the tool arguments are not valid JSON.")
    if args is None:
        args = {}
    if not isinstance(args, dict):
        raise ToolError("the tool arguments must be a JSON object.")
    if name == "list_rows":
        return list_rows(cohort), None
    if "row_id" not in args:
        raise ToolError(f"{name} needs the argument row_id.")
    if name == "get_row_values":
        return get_row_values(cohort, args["row_id"]), None
    if "mapping" not in args:
        raise ToolError(f"{name} needs the arguments row_id and mapping.")
    if name == "check_mapping":
        return check_mapping(cohort, args["row_id"], args["mapping"]), None
    # submit_answer: validate with the same parser as every other method
    _row(cohort, args["row_id"])
    mapping = coerce_mapping(args["mapping"])
    p = parse_answer(json.dumps({"row": str(args["row_id"]).strip(), "mapping": mapping}, ensure_ascii=False),
                     cohort)
    if not p.valid:
        raise ToolError(f"answer rejected: {p.reason}. Fix it and call submit_answer again.")
    return {"status": "accepted"}, {"parsed": p, "row_id": p.row, "mapping": mapping}


# ----------------------------------------------------------------------------- recovery
def _json_objects(text: str) -> list:
    """Every top level JSON object in a text (inside code fences or not)."""
    out, dec, i = [], json.JSONDecoder(), 0
    t = re.sub(r"```(?:json)?", " ", text or "")
    while True:
        j = t.find("{", i)
        if j < 0:
            return out
        try:
            obj, end = dec.raw_decode(t, j)
            out.append(obj)
            i = end
        except json.JSONDecodeError:
            i = j + 1


def recover_tool_calls(text: str) -> list[dict]:
    """Tool calls the model wrote as text: JSON objects that name a known tool."""
    calls = []
    for obj in _json_objects(text):
        if not isinstance(obj, dict):
            continue
        fn = obj.get("function") if isinstance(obj.get("function"), dict) else obj
        name = fn.get("name")
        if name in TOOL_NAMES:
            args = fn.get("arguments", fn.get("parameters", {}))
            calls.append({"name": name, "arguments": args, "recovered": True})
    return calls


# ----------------------------------------------------------------------------- the loop
def run_agent(cohort: dict, llm, seed: int | None = None, meta: dict | None = None,
              max_tool_calls: int = MAX_TOOL_CALLS, call_timeout_s: float | None = None) -> MethodResult:
    t0 = time.perf_counter()
    meta = {**(meta or {}), "cohort": cohort["cohort_id"], "method": "F"}
    msgs = agent_messages(cohort)
    steps, n_model_calls, pt, ct = 0, 0, 0, 0
    raw, trace, checks = [], [], []
    errors = Counter()
    final = None
    stop = "budget"
    while steps < max_tool_calls and final is None:
        resp = llm.chat_tools(msgs, TOOLS, role="agent_F", seed=seed, meta={**meta, "step": steps},
                              timeout_s=call_timeout_s)
        n_model_calls += 1
        pt += resp.prompt_tokens
        ct += resp.completion_tokens
        raw.append(json.dumps({"content": resp.text, "tool_calls": resp.tool_calls, "error": resp.error},
                              ensure_ascii=False))
        if resp.error:
            steps += 1
            errors["call error"] += 1
            trace.append({"tool": None, "error": resp.error})
            msgs.append({"role": "user", "content": f"Error: {resp.error}. Please call one tool at a time, "
                                                    "with valid JSON arguments."})
            continue
        tool_calls = resp.tool_calls or recover_tool_calls(resp.text)
        if not tool_calls:
            steps += 1
            errors["no tool call"] += 1
            trace.append({"tool": None, "error": "no tool call"})
            msgs.append({"role": "assistant", "content": resp.text})
            msgs.append({"role": "user", "content": "Please continue by calling a tool. No tool was called "
                                                    "in your last message. When your answer is ready, call "
                                                    "submit_answer."})
            continue
        msgs.append({"role": "assistant", "content": resp.text,
                     "tool_calls": [{"function": {"name": c["name"], "arguments": c["arguments"]}}
                                    for c in tool_calls]})
        for call in tool_calls:
            if steps >= max_tool_calls:
                break
            steps += 1
            name, args = call.get("name"), call.get("arguments")
            ts = time.perf_counter()
            try:
                result, answer = run_tool(cohort, name, args)
                entry = {"tool": name, "ok": True}
                if name == "check_mapping":
                    checks.append({"ok": result["ok"], "problems": result["problems"]})
                    entry["check_ok"] = result["ok"]
            except ToolError as e:
                result, answer = {"error": str(e)}, None
                errors["unknown tool" if str(e).startswith("unknown tool") else "bad arguments"] += 1
                entry = {"tool": name, "ok": False, "error": str(e)}
            except Exception as e:   # a bug in a tool must not end the run; report it like a tool error
                result, answer = {"error": f"tool failed: {e}"}, None
                errors["tool exception"] += 1
                entry = {"tool": name, "ok": False, "error": f"tool failed: {e}"}
            text = json.dumps(result, ensure_ascii=False)
            if hasattr(llm, "log_tool"):
                llm.log_tool(str(name), args, text, time.perf_counter() - ts, meta={**meta, "step": steps})
            if call.get("recovered"):
                entry["recovered"] = True
                errors["recovered from text"] += 1
            trace.append(entry)
            msgs.append({"role": "tool", "content": text, "tool_name": str(name)})
            if answer is not None:
                final = answer
                stop = "submitted"
                break

    agent = {"n_tool_calls": sum(1 for t in trace if t["tool"] is not None), "n_steps": steps,
             "n_recovered": sum(1 for t in trace if t.get("recovered")),
             "n_model_calls": n_model_calls, "errors": dict(errors), "stop": stop, "trace": trace,
             "checks": checks, "flagged": any(not c["ok"] for c in checks)}
    if final is None:
        return MethodResult("F", None, {}, False, False, f"no valid submit_answer within {max_tool_calls} "
                            "tool calls", n_model_calls, time.perf_counter() - t0, pt, ct, [], 0, {}, {},
                            raw, agent)
    p = final["parsed"]
    after = check_mapping(cohort, final["row_id"], final["mapping"])
    agent["final_check_ok"] = after["ok"]
    agent["final_problems"] = after["problems"]
    agent["fixed_after_flag"] = agent["flagged"] and after["ok"]
    return MethodResult("F", p.row, p.mapping, False, True, "", n_model_calls, time.perf_counter() - t0,
                        pt, ct, p.unmatched_keys, p.bad_labels, {}, {}, raw, agent)
