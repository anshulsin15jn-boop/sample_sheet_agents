"""Phase 0 smoke test: check the model answers and measure its speed in tokens per second.

Run from the project root:  python -m scripts.smoke_test
Writes results/metrics/smoke_test.json
"""
import json
import platform
import time

import psutil

from src.llm import LLMClient, ROOT, load_config

PROMPT = ("Write a short Python function `mean(xs)` that returns the average of a list of numbers, "
          "then one sentence explaining it.")


def main():
    cfg = load_config()
    client = LLMClient(cfg, log_path=ROOT / "results/logs/smoke_test.jsonl")
    vm = psutil.virtual_memory()
    runs = []
    for i in range(3):   # the first call includes loading the model into memory
        r = client.chat([{"role": "user", "content": PROMPT}], role="smoke", seed=i)
        runs.append({"seconds": round(r.seconds, 2), "prompt_tokens": r.prompt_tokens,
                     "completion_tokens": r.completion_tokens,
                     "tokens_per_second_overall": round(r.completion_tokens / r.seconds, 2)})
        print(runs[-1])
    warm = runs[1:]
    out = {
        "date": time.strftime("%Y-%m-%d %H:%M"),
        "machine": {"os": platform.platform(), "cpu": platform.processor(),
                    "total_ram_gb": round(vm.total / 2**30, 1),
                    "free_ram_gb_at_test": round(vm.available / 2**30, 1)},
        "backend": cfg["backend"], "model": client.model,
        "runs": runs,
        "warm_mean_tokens_per_second": round(
            sum(r["completion_tokens"] for r in warm) / sum(r["seconds"] for r in warm), 2),
        "sample_answer": r.text[:500],
    }
    path = ROOT / "results/metrics/smoke_test.json"
    path.write_text(json.dumps(out, indent=2))
    print(json.dumps({k: out[k] for k in ("model", "warm_mean_tokens_per_second")}))


if __name__ == "__main__":
    main()
