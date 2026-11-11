"""Typed messages passed between the agents.

GenoMAS uses structured message passing between its agents. This is a much simpler version:
each agent produces one of a few message types, and every message is appended to a transcript
so we can replay exactly what happened in any attempt.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Literal


@dataclass
class Plan:
    """Planner -> Coder: numbered steps."""
    text: str


@dataclass
class CodeSubmission:
    """Coder -> Sandbox: a complete Python program."""
    code: str
    reason: Literal["first", "fix_error", "fix_review"]


@dataclass
class ExecutionReport:
    """Sandbox -> Coder/Reviewer: what happened when the code ran."""
    status: str                 # ok, error, timeout, memory, rejected, no_answer
    stdout: str
    stderr: str
    seconds: float
    answer: dict | None = None  # the parsed ANSWER line, if any

    @property
    def good(self) -> bool:
        return self.status == "ok" and self.answer is not None


@dataclass
class Review:
    """Reviewer -> Coder: approve, or a list of specific problems."""
    verdict: Literal["approve", "revise"]
    problems: list[str]
    injection_found: bool
    raw: str


@dataclass
class Message:
    sender: str                 # planner, coder, sandbox, reviewer
    kind: str                   # plan, code, execution, review
    payload: dict
    call_index: int | None = None   # which LLM call produced it (None for the sandbox)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Transcript:
    messages: list[Message] = field(default_factory=list)

    def add(self, sender: str, kind: str, obj, call_index: int | None = None) -> None:
        payload = asdict(obj) if hasattr(obj, "__dataclass_fields__") else dict(obj)
        self.messages.append(Message(sender, kind, payload, call_index))

    def to_list(self) -> list[dict]:
        return [m.to_dict() for m in self.messages]
