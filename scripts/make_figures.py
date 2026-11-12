"""Figures for the README, made from results/runs/<run>/attempts.jsonl.

    python -m scripts.make_figures --run main

Writes results/figures/accuracy_by_method.png and results/figures/error_categories.png.
Colors: the two models use categorical slots 1 and 2 of the reference palette (blue, orange); the
rule baseline is a gray reference line; error counts use one sequential blue ramp.
"""
from __future__ import annotations

import argparse
import statistics
from collections import Counter, defaultdict

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.colors import LinearSegmentedColormap  # noqa: E402

from src.analyze import error_table, load_attempts  # noqa: E402
from src.cohort import ROOT  # noqa: E402

MODEL_COLORS = {"qwen2.5:3b": "#2a78d6", "qwen2.5-coder:3b": "#eb6834"}
TEXT, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
METHOD_NAMES = {"R": "R rules", "A": "A zero shot", "B": "B few shot", "C": "C reasoning",
                "D": "D abstain", "E": "E checker"}
CATEGORIES = ["invalid output", "abstained", "wrong row", "flipped labels", "other disease as disease",
              "negation missed", "synonym or code missed", "values left unlabelled", "other"]


def _style(ax):
    ax.set_facecolor(SURFACE)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def accuracy_figure(atts, split, out):
    atts = [a for a in atts if a["split"] == split]
    per = defaultdict(lambda: defaultdict(list))
    for a in atts:
        per[(a["model"], a["method"])][a["repeat"]].append(a["accuracy"])
    rule = [statistics.mean(v) for v in per[("none", "R")].values()]
    methods = [m for m in "ABCDE" if any(k[1] == m for k in per)]
    models = [m for m in MODEL_COLORS if any(k[0] == m for k in per)]
    fig, ax = plt.subplots(figsize=(7.5, 4), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    _style(ax)
    width = 0.8 / max(1, len(models))
    for j, model in enumerate(models):
        xs, ms, sds = [], [], []
        for i, meth in enumerate(methods):
            reps = [statistics.mean(v) for v in per[(model, meth)].values()]
            if not reps:
                continue
            xs.append(i + (j - (len(models) - 1) / 2) * width)
            ms.append(100 * statistics.mean(reps))
            sds.append(100 * statistics.stdev(reps) if len(reps) > 1 else 0)
        ax.bar(xs, ms, width * 0.92, color=MODEL_COLORS[model], label=model, edgecolor=SURFACE, linewidth=1)
        if any(sds):
            ax.errorbar(xs, ms, yerr=sds, fmt="none", ecolor=TEXT, elinewidth=1, capsize=3)
        for x, m, sd in zip(xs, ms, sds):
            ax.text(x, m + sd + 1.5, f"{m:.0f}", ha="center", va="bottom", fontsize=8, color=TEXT)
    if rule:
        r = 100 * statistics.mean(rule)
        ax.axhline(r, color=MUTED, linestyle="--", linewidth=1.5)
        ax.text(len(methods) - 0.5, r + 1.5, f"R rules {r:.0f}", ha="right", fontsize=8, color=MUTED)
    ax.set_xticks(range(len(methods)), [METHOD_NAMES[m] for m in methods], color=TEXT)
    ax.set_ylim(0, 105)
    ax.set_ylabel("Mean per sample accuracy (%)", color=TEXT, fontsize=9)
    ax.set_title(f"Accuracy by method ({split} cohorts; bars: mean over repeats, lines: spread)",
                 fontsize=10, color=TEXT, loc="left")
    ax.legend(frameon=False, fontsize=8, loc="upper left", labelcolor=TEXT)
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)


def error_figure(atts, split, out):
    errs = error_table(atts, split)
    keys = sorted({(e["model"], e["method"]) for e in errs}, key=lambda k: (k[0] != "none", k[0], k[1]))
    n_rep = defaultdict(set)
    for a in atts:
        n_rep[(a["model"], a["method"])].add(a["repeat"])
    cnt = Counter((e["model"], e["method"], e["category"]) for e in errs)
    cats = [c for c in CATEGORIES if any(cnt[(m, me, c)] for m, me in keys)]
    data = [[cnt[(m, me, c)] / len(n_rep[(m, me)]) for (m, me) in keys] for c in cats]
    fig, ax = plt.subplots(figsize=(2.0 + 0.75 * len(keys), 0.5 + 0.42 * len(cats)), dpi=150)
    fig.patch.set_facecolor(SURFACE)
    cmap = LinearSegmentedColormap.from_list("blue", ["#f3f7fd", "#2a78d6", "#0d3a73"])
    vmax = max(max(r) for r in data) if data else 1
    ax.imshow(data, cmap=cmap, vmin=0, vmax=vmax, aspect="auto")
    for i, row in enumerate(data):
        for j, v in enumerate(row):
            if v:
                ax.text(j, i, f"{v:.1f}".rstrip("0").rstrip("."), ha="center", va="center", fontsize=8,
                        color="white" if v > 0.55 * vmax else TEXT)
    short = {"qwen2.5:3b": "3b", "qwen2.5-coder:3b": "coder"}
    labels = [("R" if m == "none" else f"{me}\n{short.get(m, m)}") for m, me in keys]
    ax.set_xticks(range(len(keys)), labels, fontsize=8, color=TEXT)
    ax.set_yticks(range(len(cats)), cats, fontsize=8, color=TEXT)
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    ax.set_title("Failed cohorts by error type (count per repeat)\n3b = qwen2.5:3b, coder = qwen2.5-coder:3b",
                 fontsize=10, color=TEXT, loc="left")
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", default="main")
    ap.add_argument("--split", default="test")
    a = ap.parse_args()
    atts = load_attempts(a.run)
    d = ROOT / "results" / "figures"
    d.mkdir(parents=True, exist_ok=True)
    tag = "" if a.run == "main" else f"_{a.run}"
    accuracy_figure(atts, a.split, d / f"accuracy_by_method{tag}.png")
    error_figure(atts, a.split, d / f"error_categories{tag}.png")
    print("wrote figures to", d)


if __name__ == "__main__":
    main()
