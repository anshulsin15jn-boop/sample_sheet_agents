"""Smoke test: check each model answers, returns JSON, and measure its speed.

Run from the project root:  python -m scripts.smoke_test
Writes results/metrics/smoke_test.json and logs every call to results/logs/smoke_test.jsonl.
Models are run one at a time and unloaded afterwards, so only one is in memory at once.
"""
import json
import platform
import time

import psutil
import requests

from src.llm import LLMClient, ROOT, load_config

PROMPT = """Trait: Asthma
Unique values of one sample metadata row: ["disease state: asthma", "disease state: healthy control"]
Map each value to "disease" or "control". Reply with JSON only, like {"value": "label"}."""


def unload(cfg, model):
    try:
        requests.post(f"{cfg['ollama']['url']}/api/generate",
                      json={"model": model, "keep_alive": 0}, timeout=60)
    except requests.RequestException:
        pass


def main():
    cfg = load_config()
    out = {"date": time.strftime("%Y-%m-%d %H:%M"),
           "machine": {"os": platform.platform(), "cpu": platform.processor(),
                       "total_ram_gb": round(psutil.virtual_memory().total / 2**30, 1)},
           "models": {}}
    for model in cfg["models"]:
        client = LLMClient({**cfg, "model": model}, log_path=ROOT / "results/logs/smoke_test.jsonl")
        free_before = round(psutil.virtual_memory().available / 2**30, 1)
        runs = []
        for i in range(3):   # the first call includes loading the model into memory
            r = client.chat([{"role": "user", "content": PROMPT}], role="smoke", seed=i)
            try:
                json.loads(r.text.strip().strip("`").removeprefix("json").strip())
                valid = True
            except json.JSONDecodeError:
                valid = False
            runs.append({"seconds": round(r.seconds, 2), "prompt_tokens": r.prompt_tokens,
                         "completion_tokens": r.completion_tokens, "valid_json": valid})
            print(model, runs[-1], flush=True)
        free_loaded = round(psutil.virtual_memory().available / 2**30, 1)
        warm = runs[1:]
        out["models"][model] = {
            "free_ram_gb_before": free_before, "free_ram_gb_while_loaded": free_loaded,
            "runs": runs,
            "warm_mean_seconds_per_call": round(sum(x["seconds"] for x in warm) / len(warm), 2),
            "warm_tokens_per_second": round(sum(x["completion_tokens"] for x in warm)
                                            / sum(x["seconds"] for x in warm), 2),
            "sample_answer": r.text[:300],
        }
        unload(cfg, model)
        time.sleep(3)
    path = ROOT / "results/metrics/smoke_test.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=2))
    print(json.dumps({m: v["warm_tokens_per_second"] for m, v in out["models"].items()}))


if __name__ == "__main__":
    main()
