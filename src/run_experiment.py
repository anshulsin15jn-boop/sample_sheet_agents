"""Resumable experiment runner.

    python -m src.run_experiment --run pilot --tasks t01_exo_hz_count,t07_bc_cross_validation --repeats 1
    python -m src.run_experiment --run main            # all tasks, all conditions, config repeats

Each finished attempt (one task x condition x repeat) is appended as one JSON line to
results/metrics/<run>_attempts.jsonl. On restart, attempts already in that file are skipped,
so a crash or shutdown loses at most the attempt in progress. Every LLM call is logged to
results/logs/<run>_calls.jsonl.
"""
from __future__ import annotations

import argparse
import json
import time
import traceback
from dataclasses import asdict

import psutil

from .llm import LLMClient, ROOT, load_config
from .pipelines import run_condition
from .tasks import all_task_ids, load_task


def done_keys(path) -> set:
    keys = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                keys.add((r["task_id"], r["condition"], r["repeat"]))
    return keys


def wait_for_memory(min_gb: float, max_wait_s: int = 600) -> None:
    t0 = time.time()
    while psutil.virtual_memory().available / 2**30 < min_gb and time.time() - t0 < max_wait_s:
        print(f"  low memory ({psutil.virtual_memory().available / 2**30:.1f} GB free), "
              f"waiting 30 s ...", flush=True)
        time.sleep(30)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True, help="run name, e.g. pilot or main")
    ap.add_argument("--tasks", default="all", help="comma separated task ids, or all")
    ap.add_argument("--conditions", default=None, help="e.g. A,B,C,D (default from config)")
    ap.add_argument("--repeats", type=int, default=None)
    ap.add_argument("--config", default=None)
    a = ap.parse_args()

    cfg = load_config(a.config)
    tasks = all_task_ids() if a.tasks == "all" else a.tasks.split(",")
    conds = a.conditions.split(",") if a.conditions else cfg["experiment"]["conditions"]
    repeats = a.repeats if a.repeats is not None else cfg["experiment"]["repeats"]

    out = ROOT / "results" / "metrics" / f"{a.run}_attempts.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    llm = LLMClient(cfg, log_path=ROOT / "results" / "logs" / f"{a.run}_calls.jsonl")
    done = done_keys(out)
    # repeat is the outer loop, so a run stopped early still has balanced conditions per repeat
    todo = [(t, c, r) for r in range(repeats) for t in tasks for c in conds if (t, c, r) not in done]
    print(f"run={a.run} model={llm.model} tasks={len(tasks)} conditions={conds} repeats={repeats}"
          f" | done={len(done)} todo={len(todo)}", flush=True)

    meta = ROOT / "results" / "metrics" / f"{a.run}_meta.json"
    if not meta.exists():
        meta.write_text(json.dumps({"started": time.strftime("%Y-%m-%d %H:%M:%S"), "model": llm.model,
                                    "backend": cfg["backend"], "config": cfg, "tasks": tasks,
                                    "conditions": conds, "repeats": repeats}, indent=2))

    t_run = time.time()
    for i, (tid, cond, rep) in enumerate(todo, 1):
        wait_for_memory(cfg["experiment"]["min_free_ram_gb"])
        task = load_task(tid)
        try:
            res = asdict(run_condition(cond, task, llm, cfg, repeat=rep))
        except Exception as e:   # record the failure and keep going
            traceback.print_exc()
            print(f"  attempt failed with an exception: {e}", flush=True)
            if "LLM call failed" in str(e):
                print("  the model server seems down; stopping so the run can be resumed later.")
                break
            continue
        res["finished"] = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(out, "a", encoding="utf-8") as f:
            f.write(json.dumps(res, ensure_ascii=False) + "\n")
        el = time.time() - t_run
        eta = el / i * (len(todo) - i)
        print(f"[{i}/{len(todo)}] {tid} {cond} r{rep}: success={res['success']} "
              f"calls={res['n_calls']} {res['wall_seconds']:.0f}s | elapsed {el / 60:.1f} min, "
              f"eta {eta / 60:.0f} min", flush=True)


if __name__ == "__main__":
    main()
