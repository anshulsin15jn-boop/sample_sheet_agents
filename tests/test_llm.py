"""Tests for the LLM client. The live test is skipped when no Ollama server is running."""
import json

import pytest
import requests

from src.llm import LLMClient, ScriptedLLM, load_config


def test_scripted_llm_returns_in_order():
    llm = ScriptedLLM(["a", "b"])
    assert llm.chat([{"role": "user", "content": "x"}]).text == "a"
    assert llm.chat([{"role": "user", "content": "y"}]).text == "b"
    assert len(llm.calls) == 2


def test_openrouter_requires_free_model():
    cfg = load_config()
    cfg = {**cfg, "backend": "openrouter",
           "openrouter": {**cfg["openrouter"], "model": "some/paid-model"}}
    with pytest.raises(ValueError):
        LLMClient(cfg)


def _ollama_up(cfg):
    try:
        return requests.get(cfg["ollama"]["url"] + "/api/tags", timeout=2).ok
    except requests.RequestException:
        return False


@pytest.mark.llm
def test_live_ollama_call_is_logged(tmp_path):
    cfg = load_config()
    if cfg["backend"] != "ollama" or not _ollama_up(cfg):
        pytest.skip("Ollama server not running")
    log = tmp_path / "calls.jsonl"
    client = LLMClient(cfg, log_path=log)
    r = client.chat([{"role": "user", "content": "Reply with the single word: ok"}], role="test", seed=1)
    assert r.text.strip() and r.completion_tokens > 0
    rec = json.loads(log.read_text().splitlines()[0])
    assert rec["role"] == "test" and rec["seed"] == 1 and rec["response"] == r.text
