"""The four experimental conditions.

A. Coder only: the coder writes code and retries when it crashes.
B. Planner + coder.
C. Planner + coder + reviewer, one review round.
D. Planner + coder + reviewer, up to two review rounds.

Every condition gets the SAME cap on LLM calls per task (config: max_llm_calls_per_task).
Conditions without a reviewer can spend the spare calls on more retries, so a reviewer only
"wins" if reviewing is a better use of a call than another retry.

The final answer is the output of the most recent program that ran without error and printed
an ANSWER line. A review is only requested when there is room left in the budget for the coder
to act on it.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict

from . import agents
from .grader import grade, parse_answer
from .protocol import CodeSubmission, ExecutionReport, Plan, Review, Transcript
from .sandbox import run_code
from .tasks import Task

CONDITIONS = {
    "A": {"planner": False, "reviews": 0, "name": "Coder only"},
    "B": {"planner": True, "reviews": 0, "name": "Planner + coder"},
    "C": {"planner": True, "reviews": 1, "name": "Planner + coder + reviewer (1 round)"},
    "D": {"planner": True, "reviews": 2, "name": "Planner + coder + reviewer (2 rounds)"},
}


@dataclass
class ReviewEvent:
    round: int
    verdict: str
    injection_found: bool
    n_problems: int
    pre_success: bool               # was the answer the reviewer saw correct?
    pre_trap_fell: bool
    post_success: bool | None = None   # correctness of the next good answer after a revise
    post_trap_fell: bool | None = None
    problems: list = field(default_factory=list)


@dataclass
class AttemptResult:
    task_id: str
    condition: str
    repeat: int
    category: str
    trap_type: str | None
    success: bool
    parsed: bool
    trap_fell: bool
    trap_handled: bool
    answer: dict | None
    field_correct: dict
    final_status: str
    first_run_ok: bool              # did the coder's very first program run cleanly with an answer?
    n_runs: int
    n_failed_runs: int
    n_rejected_runs: int
    n_calls: int
    calls_by_role: dict
    prompt_tokens: int
    completion_tokens: int
    llm_seconds: float
    sandbox_seconds: float
    wall_seconds: float
    first_good_success: bool | None   # correctness of the first good answer (before any review)
    reviews: list
    transcript: list
    error: str | None = None


def _execute(code: str, task: Task, cfg: dict) -> ExecutionReport:
    s = cfg["sandbox"]
    r = run_code(code, data_dir=task.data_dir, timeout_s=s["timeout_s"],
                 max_memory_mb=s["max_memory_mb"], max_output_chars=s["max_output_chars"])
    ans = parse_answer(r.stdout) if r.ok else None
    status = r.status if not (r.ok and ans is None) else "no_answer"
    return ExecutionReport(status, r.stdout, r.stderr, r.seconds, ans)


def run_condition(condition: str, task: Task, llm, cfg: dict, repeat: int = 0) -> AttemptResult:
    spec = CONDITIONS[condition]
    max_calls = cfg["experiment"]["max_llm_calls_per_task"]
    base_seed = cfg["generation"]["base_seed"]
    tr = Transcript()
    stats = {"calls": 0, "pt": 0, "ct": 0, "llm_s": 0.0, "sb_s": 0.0,
             "by_role": {"planner": 0, "coder": 0, "reviewer": 0}}
    t_start = time.perf_counter()

    def call(role: str, messages: list) -> str:
        k = stats["calls"]
        resp = llm.chat(messages, role=role, seed=base_seed + 1000 * repeat + k,
                        meta={"task": task.task_id, "condition": condition, "repeat": repeat,
                              "call_index": k})
        stats["calls"] += 1
        stats["by_role"][role] += 1
        stats["pt"] += resp.prompt_tokens
        stats["ct"] += resp.completion_tokens
        stats["llm_s"] += resp.seconds
        return resp.text

    plan = None
    if spec["planner"]:
        plan = Plan(call("planner", agents.planner_messages(task.prompt, task.preview)))
        tr.add("planner", "plan", plan, stats["calls"] - 1)

    reviews: list[ReviewEvent] = []
    good: tuple[str, ExecutionReport] | None = None   # latest program that produced an answer
    last: ExecutionReport | None = None
    prev_code: str | None = None
    pending_review: Review | None = None
    pending_exec: ExecutionReport | None = None
    first_run_ok = None
    first_good_success = None
    n_runs = n_failed = n_rejected = 0

    while stats["calls"] < max_calls:
        # ---- coder writes (or fixes) a program
        if prev_code is None:
            msgs, reason = agents.coder_messages(task.prompt, task.preview, plan), "first"
        elif pending_review is not None:
            msgs, reason = agents.coder_messages(task.prompt, task.preview, plan, prev_code,
                                                 pending_exec, pending_review), "fix_review"
        else:
            msgs, reason = agents.coder_messages(task.prompt, task.preview, plan, prev_code,
                                                 pending_exec), "fix_error"
        code = agents.extract_code(call("coder", msgs))
        tr.add("coder", "code", CodeSubmission(code, reason), stats["calls"] - 1)

        # ---- sandbox runs it
        ex = _execute(code, task, cfg)
        stats["sb_s"] += ex.seconds
        n_runs += 1
        n_failed += 0 if ex.good else 1
        n_rejected += ex.status == "rejected"
        tr.add("sandbox", "execution", ex)
        last, prev_code = ex, code
        if first_run_ok is None:
            first_run_ok = ex.good

        if not ex.good:
            pending_exec, pending_review = ex, None
            continue

        good = (code, ex)
        g = grade(ex.stdout, task.key)
        if first_good_success is None:
            first_good_success = g.success
        if reviews and reviews[-1].verdict == "revise" and reviews[-1].post_success is None:
            reviews[-1].post_success, reviews[-1].post_trap_fell = g.success, g.trap_fell

        # ---- reviewer, if this condition has review rounds left and the coder could still act
        if len(reviews) < spec["reviews"] and stats["calls"] <= max_calls - 2:
            rv = agents.parse_review(call("reviewer", agents.reviewer_messages(
                task.prompt, task.preview, plan, code, ex)))
            tr.add("reviewer", "review", rv, stats["calls"] - 1)
            reviews.append(ReviewEvent(len(reviews) + 1, rv.verdict, rv.injection_found,
                                       len(rv.problems), g.success, g.trap_fell,
                                       problems=rv.problems[:10]))
            if rv.verdict == "approve":
                break
            pending_exec, pending_review = ex, rv
            continue
        break   # a good answer and no more reviews: done

    final = good[1] if good else last
    g = grade(final.stdout if final and final.good else "", task.key)
    return AttemptResult(
        task_id=task.task_id, condition=condition, repeat=repeat, category=task.category,
        trap_type=g.trap_type, success=g.success, parsed=g.parsed, trap_fell=g.trap_fell,
        trap_handled=g.trap_handled, answer=g.answer, field_correct=g.field_correct,
        final_status=final.status if final else "no_run", first_run_ok=bool(first_run_ok),
        n_runs=n_runs, n_failed_runs=n_failed, n_rejected_runs=n_rejected,
        n_calls=stats["calls"], calls_by_role=stats["by_role"], prompt_tokens=stats["pt"],
        completion_tokens=stats["ct"], llm_seconds=round(stats["llm_s"], 2),
        sandbox_seconds=round(stats["sb_s"], 2),
        wall_seconds=round(time.perf_counter() - t_start, 2),
        first_good_success=first_good_success, reviews=[asdict(r) for r in reviews],
        transcript=tr.to_list())
