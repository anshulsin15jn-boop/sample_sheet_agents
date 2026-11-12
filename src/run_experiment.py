"""Resumable experiment runner.

    python -m src.run_experiment --run pilot --cohorts pilot --models qwen2.5:3b --repeats 1
    python -m src.run_experiment --run main --cohorts test

Each finished attempt (model x cohort x method x repeat) is appended as one JSON line to
results/runs/<run>/attempts.jsonl. On restart, attempts already in that file are skipped, so a
crash or shutdown loses at most the attempt in progress. Every LLM call is logged to
results/runs/<run>/calls.jsonl. Method R has no model and runs once per cohort.

Order: model is the outer loop (only one model is in memory at a time), then repeat, then cohort,
then method, so a run that stops early still has every method on the same cohorts.
While running, Windows is asked not to sleep; that request is released at the end.
"""
from __future__ import annotations

import argparse
import ctypes
import json
import sys
import time
import traceback

import psutil
import requests

from .cohort import ROOT, all_cohorts, load_cohort
from .grading import grade
from .llm import LLMClient, load_config
from .methods import ALL_METHODS, run_method

PILOT_COHORTS = ["GSE120490", "GSE123088", "GSE131282", "GSE135589", "GSE212866"]  # dev, not examples

ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001


def keep_awake(on: bool) -> None:
    if sys.platform == "win32":
        flags = ES_CONTINUOUS | ES_SYSTEM_REQUIRED if on else ES_CONTINUOUS
        ctypes.windll.kernel32.SetThreadExecutionState(flags)


def done_keys(path) -> set:
    keys = set()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                r = json.loads(line)
                keys.add((r["model"], r["cohort_id"], r["method"], r["repeat"]))
    return keys


def wait_for_memory(min_gb: float, max_wait_s: int = 900) -> None:
    t0 = time.time()
    while psutil.virtual_memory().available / 2**30 < min_gb and time.time() - t0 < max_wait_s:
        print(f"  low memory ({psutil.virtual_memory().available / 2**30:.1f} GB free), waiting 30 s",
              flush=True)
        time.sleep(30)


def unload(cfg: dict, model: str) -> None:
    try:
        requests.post(f"{cfg['ollama']['url']}/api/generate", json={"model": model, "keep_alive": 0},
                      timeout=60)
    except requests.RequestException:
        pass


def pick_cohorts(spec: str) -> list[str]:
    if spec == "pilot":
        return PILOT_COHORTS
    if spec in ("dev", "test"):
        return [c["cohort_id"] for c in all_cohorts(spec)]
    if spec == "all":
        return [c["cohort_id"] for c in all_cohorts()]
    return spec.split(",")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    ap.add_argument("--cohorts", default="test", help="pilot, dev, test, all, or comma separated ids")
    ap.add_argument("--methods", default=",".join(ALL_METHODS))
    ap.add_argument("--models", default=None, help="comma separated (default: config models)")
    ap.add_argument("--repeats", type=int, default=None)
    ap.add_argument("--config", default=None)
    a = ap.parse_args()

    cfg = load_config(a.config)
    cohorts = pick_cohorts(a.cohorts)
    methods = a.methods.split(",")
    models = a.models.split(",") if a.models else cfg["models"]
    repeats = a.repeats if a.repeats is not None else cfg["experiment"]["repeats"]
    run_dir = ROOT / "results" / "runs" / a.run
    run_dir.mkdir(parents=True, exist_ok=True)
    out = run_dir / "attempts.jsonl"
    done = done_keys(out)

    todo = []
    if "R" in methods:
        todo += [("none", c, "R", 0) for c in cohorts]
    for m in models:
        for r in range(repeats):
            for c in cohorts:
                for meth in methods:
                    if meth != "R":
                        todo.append((m, c, meth, r))
    todo = [t for t in todo if t not in done]
    print(f"run={a.run} cohorts={len(cohorts)} methods={methods} models={models} repeats={repeats} "
          f"| done={len(done)} todo={len(todo)}", flush=True)
    meta_path = run_dir / "meta.json"
    if not meta_path.exists():
        meta_path.write_text(json.dumps({"started": time.strftime("%Y-%m-%d %H:%M:%S"), "config": cfg,
                                         "cohorts": cohorts, "methods": methods, "models": models,
                                         "repeats": repeats}, indent=2))

    keep_awake(True)
    clients: dict[str, LLMClient] = {}
    current = None
    t_run = time.time()
    try:
        for i, (model, cid, meth, rep) in enumerate(todo, 1):
            cohort = load_cohort(cid)
            llm = None
            if model != "none":
                if current and current != model:
                    unload(cfg, current)
                current = model
                if model not in clients:
                    clients[model] = LLMClient({**cfg, "model": model}, log_path=run_dir / "calls.jsonl")
                llm = clients[model]
                wait_for_memory(cfg["experiment"]["min_free_ram_gb"])
            seed = cfg["generation"]["base_seed"] + rep
            try:
                res = run_method(meth, cohort, llm, seed=seed,
                                 meta={"run": a.run, "model": model, "repeat": rep})
            except Exception as e:   # record the failure and keep going
                traceback.print_exc()
                if "LLM call failed" in str(e):
                    print("  the model server seems down; stopping so the run can be resumed later.")
                    break
                continue
            g = grade(cohort, res.row if res.valid else None, res.mapping if res.valid else {},
                      res.cannot_determine)
            rec = {"model": model, "cohort_id": cid, "trait": cohort["trait"], "split": cohort["split"],
                   "method": meth, "repeat": rep, "seed": seed, **g, "result": res.to_dict(),
                   "finished": time.strftime("%Y-%m-%d %H:%M:%S")}
            with open(out, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            el = time.time() - t_run
            print(f"[{i}/{len(todo)}] {model} {cid} {meth} r{rep}: acc={g['accuracy']:.2f} "
                  f"row={'ok' if g['row_correct'] else 'X'} valid={res.valid} calls={res.n_calls} "
                  f"{res.seconds:.0f}s | {el / 60:.1f} min, eta {el / i * (len(todo) - i) / 60:.0f} min",
                  flush=True)
    finally:
        keep_awake(False)
        if current:
            unload(cfg, current)


if __name__ == "__main__":
    main()
