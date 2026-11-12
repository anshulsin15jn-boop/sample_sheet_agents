"""One small interface for chat models: a local Ollama server (OpenRouter free models also supported
but unused in this project).

Every call is timed, counted in tokens, and (when a log path is given) written to a JSONL file,
so every number in the study can be traced back to the exact messages that produced it.
"""
from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Callable

import requests
import yaml

ROOT = Path(__file__).resolve().parents[1]


def load_config(path: str | Path | None = None) -> dict:
    path = Path(path) if path else ROOT / "config.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


@dataclass
class LLMResponse:
    text: str
    prompt_tokens: int
    completion_tokens: int
    seconds: float
    model: str
    backend: str


@dataclass
class CallRecord:
    """One logged LLM call."""
    time: float
    backend: str
    model: str
    role: str
    seed: int | None
    messages: list
    response: str
    prompt_tokens: int
    completion_tokens: int
    seconds: float
    meta: dict = field(default_factory=dict)


class LLMClient:
    """Chat client. `chat()` returns an LLMResponse and logs the call."""

    def __init__(self, config: dict, log_path: str | Path | None = None):
        self.config = config
        self.backend = config["backend"]
        gen = config["generation"]
        self.temperature = gen["temperature"]
        self.max_tokens = gen["max_tokens"]
        self.timeout = gen["request_timeout_s"]
        self.log_path = Path(log_path) if log_path else None
        self._last_call = 0.0
        if self.backend == "ollama":
            self.model = config["model"]
        elif self.backend == "openrouter":
            self.model = config["openrouter"]["model"]
            if not self.model.endswith(":free"):
                raise ValueError("Only free OpenRouter models (ending in ':free') are allowed.")
        else:
            raise ValueError(f"Unknown backend {self.backend!r}")

    # ------------------------------------------------------------------ backends
    def _ollama(self, messages: list, seed: int | None, json_mode: bool = False) -> LLMResponse:
        o = self.config["ollama"]
        options = {
            "temperature": self.temperature,
            "num_ctx": o["num_ctx"],
            "num_predict": self.max_tokens,
        }
        if seed is not None:
            options["seed"] = seed
        t0 = time.perf_counter()
        body = {"model": self.model, "messages": messages, "stream": False,
                "options": options, "keep_alive": o.get("keep_alive", "10m")}
        if json_mode:   # Ollama then only lets the model produce syntactically valid JSON
            body["format"] = "json"
        r = requests.post(f"{o['url']}/api/chat", json=body, timeout=self.timeout)
        r.raise_for_status()
        data = r.json()
        return LLMResponse(
            text=data["message"]["content"],
            prompt_tokens=int(data.get("prompt_eval_count", 0)),
            completion_tokens=int(data.get("eval_count", 0)),
            seconds=time.perf_counter() - t0,
            model=self.model,
            backend="ollama",
        )

    def _openrouter(self, messages: list, seed: int | None, json_mode: bool = False) -> LLMResponse:
        o = self.config["openrouter"]
        key = os.environ.get(o["api_key_env"])
        if not key:
            raise RuntimeError(f"Set {o['api_key_env']} to use the OpenRouter backend.")
        wait = o.get("min_seconds_between_calls", 3.5) - (time.time() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        payload = {"model": self.model, "messages": messages,
                   "temperature": self.temperature, "max_tokens": self.max_tokens}
        if seed is not None:
            payload["seed"] = seed
        t0 = time.perf_counter()
        r = requests.post(o["url"], headers={"Authorization": f"Bearer {key}"},
                          json=payload, timeout=self.timeout)
        self._last_call = time.time()
        r.raise_for_status()
        data = r.json()
        usage = data.get("usage", {})
        return LLMResponse(
            text=data["choices"][0]["message"]["content"],
            prompt_tokens=int(usage.get("prompt_tokens", 0)),
            completion_tokens=int(usage.get("completion_tokens", 0)),
            seconds=time.perf_counter() - t0,
            model=self.model,
            backend="openrouter",
        )

    # ------------------------------------------------------------------ public
    def chat(self, messages: list, role: str = "", seed: int | None = None,
             meta: dict | None = None, retries: int = 2, json_mode: bool = False) -> LLMResponse:
        fn: Callable = self._ollama if self.backend == "ollama" else self._openrouter
        last_err = None
        for attempt in range(retries + 1):
            try:
                resp = fn(messages, seed, json_mode)
                break
            except (requests.RequestException, KeyError, ValueError) as e:  # network or server hiccup
                last_err = e
                time.sleep(5 * (attempt + 1))
        else:
            raise RuntimeError(f"LLM call failed after {retries + 1} tries: {last_err}")
        self._log(CallRecord(time=time.time(), backend=resp.backend, model=resp.model, role=role,
                             seed=seed, messages=messages, response=resp.text,
                             prompt_tokens=resp.prompt_tokens,
                             completion_tokens=resp.completion_tokens,
                             seconds=round(resp.seconds, 3), meta=meta or {}))
        return resp

    def _log(self, rec: CallRecord) -> None:
        if self.log_path is None:
            return
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(rec), ensure_ascii=False) + "\n")


class ScriptedLLM:
    """A fake LLM for tests: returns canned responses in order and records the prompts."""

    def __init__(self, responses: list[str]):
        self.responses = list(responses)
        self.calls: list[dict] = []
        self.model = "scripted"
        self.backend = "scripted"

    def chat(self, messages: list, role: str = "", seed: int | None = None,
             meta: dict | None = None, retries: int = 0, json_mode: bool = False) -> LLMResponse:
        self.calls.append({"role": role, "messages": messages, "seed": seed})
        text = self.responses.pop(0) if self.responses else ""
        return LLMResponse(text=text, prompt_tokens=10, completion_tokens=10, seconds=0.0,
                           model="scripted", backend="scripted")
