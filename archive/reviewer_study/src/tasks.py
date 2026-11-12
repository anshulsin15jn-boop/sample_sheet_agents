"""Load benchmark tasks and build the short data preview that every agent sees.

A separate module because the planner, coder, and reviewer all need the same
view of the task and its data. A human analyst would open the files and look at the first rows;
this preview plays that role. It is also how a prompt injection hidden in the data reaches the
model, exactly as it would in real use.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TASK_DIR = ROOT / "benchmark" / "tasks"


@dataclass
class Task:
    task_id: str
    folder: Path
    prompt: str
    key: dict
    preview: str

    @property
    def data_dir(self) -> Path:
        return self.folder / "data"

    @property
    def category(self) -> str:
        return self.key["category"]


def data_preview(data_dir: Path, max_text_chars: int = 1500, n_rows: int = 5) -> str:
    parts = []
    for p in sorted(data_dir.iterdir()):
        rel = f"data/{p.name}"
        if p.suffix == ".csv":
            df = pd.read_csv(p)
            with open(p, encoding="utf-8") as f:
                lines = [next(f, "").rstrip("\n")[:400] for _ in range(n_rows + 1)]
            parts.append(f"### {rel}  ({df.shape[0]} rows x {df.shape[1]} columns)\n"
                         f"Columns and types: " +
                         ", ".join(f"{c} ({t})" for c, t in df.dtypes.astype(str).items()) +
                         f"\nFirst {n_rows} lines of the raw file (header plus rows):\n" +
                         "\n".join(lines))
        elif p.suffix == ".npz":
            with np.load(p) as z:
                arrs = ", ".join(f"{k}: shape {z[k].shape}, dtype {z[k].dtype}" for k in z.files)
            parts.append(f"### {rel}  (numpy archive)\nArrays: {arrs}")
        elif p.suffix in {".txt", ".md"}:
            text = p.read_text(encoding="utf-8")
            if len(text) > max_text_chars:
                text = text[:max_text_chars] + "\n...(cut)"
            parts.append(f"### {rel}\n{text.strip()}")
        else:
            parts.append(f"### {rel}  ({p.stat().st_size} bytes)")
    return "\n\n".join(parts)


def load_task(task_id: str) -> Task:
    folder = TASK_DIR / task_id
    prompt = (folder / "task.md").read_text(encoding="utf-8")
    key = json.loads((folder / "answer_key.json").read_text(encoding="utf-8"))
    return Task(task_id, folder, prompt, key, data_preview(folder / "data"))


def all_task_ids() -> list[str]:
    return sorted(p.name for p in TASK_DIR.iterdir() if (p / "task.md").exists())
