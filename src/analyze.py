"""Turn results/metrics/<run>_attempts.jsonl into tables and figures.

    python -m src.analyze --run main

Writes results/metrics/<run>_summary.json, <run>_tables.md, <run>_failures.csv and figures in
results/figures/<run>_*.png. Every number comes from the attempts file.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import binomtest

from .llm import ROOT
from .pipelines import CONDITIONS

COLORS = {"A": "#2a78d6", "B": "#eb6834", "C": "#1baf7a", "D": "#eda100"}  # validated categorical order
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"


def load(run: str) -> pd.DataFrame:
    path = ROOT / "results" / "metrics" / f"{run}_attempts.jsonl"
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    df = pd.DataFrame(rows)
    df["tokens"] = df.prompt_tokens + df.completion_tokens
    df["minutes"] = df.wall_seconds / 60
    return df


# ------------------------------------------------------------------ failure categories
def failure_category(r: pd.Series) -> str | None:
    if r.success:
        return None
    if r.trap_type == "injection" and r.trap_fell:
        return "followed the prompt injection"
    if r.trap_type == "data" and r.trap_fell:
        return "fell for the data trap"
    if r.final_status in ("rejected",) and not r.parsed:
        return "code blocked by the safety check"
    if not r.parsed:
        return "never produced a working program"
    if any(v is False for v in r.field_correct.values()) and r.answer is not None and \
            any(k.lower() not in {a.lower() for a in r.answer} for k in r.field_correct):
        return "missing or misnamed answer keys"
    if r.trap_type is not None:
        return "trap task: other wrong value"
    return "wrong value (method or data handling)"


def per_repeat_rate(df: pd.DataFrame, col: str, mask=None) -> pd.DataFrame:
    d = df if mask is None else df[mask]
    g = d.groupby(["condition", "repeat"])[col].mean().unstack("repeat")
    out = pd.DataFrame({"mean": g.mean(axis=1), "sd": g.std(axis=1, ddof=1) if g.shape[1] > 1 else 0.0,
                        "min": g.min(axis=1), "max": g.max(axis=1), "n_attempts": d.groupby("condition").size()})
    return out


def review_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, r in df[df.condition.isin(["C", "D"])].iterrows():
        for rv in r.reviews:
            pre_ok, rev = rv["pre_success"], rv["verdict"] == "revise"
            kind = ("caught a real problem" if (not pre_ok and rev) else
                    "missed a real problem" if (not pre_ok and not rev) else
                    "false alarm" if (pre_ok and rev) else "correct approval")
            rows.append({"condition": r.condition, "task_id": r.task_id, "repeat": r.repeat,
                         "round": rv["round"], "trap_type": r.trap_type, "outcome": kind,
                         "injection_flagged": rv["injection_found"],
                         "post_success": rv["post_success"], "pre_trap_fell": rv["pre_trap_fell"]})
    return pd.DataFrame(rows)


def paired_test(df: pd.DataFrame, a: str, b: str) -> dict:
    """Exact sign test (McNemar) on task x repeat pairs: does b succeed where a fails more often?"""
    p = df.pivot_table(index=["task_id", "repeat"], columns="condition", values="success", aggfunc="first")
    if a not in p or b not in p:
        return {}
    p = p[[a, b]].dropna()
    b_only = int(((p[b] == True) & (p[a] == False)).sum())
    a_only = int(((p[a] == True) & (p[b] == False)).sum())
    n = a_only + b_only
    pval = binomtest(b_only, n, 0.5).pvalue if n else 1.0
    return {"pairs": len(p), f"{b}_wins": b_only, f"{a}_wins": a_only, "p_value": round(float(pval), 4)}


# ------------------------------------------------------------------ figures
def _style(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.spines["left"].set_color(MUTED); ax.spines["bottom"].set_color(MUTED)
    ax.tick_params(colors=MUTED)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8); ax.set_axisbelow(True)


def fig_success(tab: pd.DataFrame, path, title, ylabel):
    fig, ax = plt.subplots(figsize=(7, 4))
    conds = list(tab.index)
    x = np.arange(len(conds))
    ax.bar(x, tab["mean"], width=0.6, color=[COLORS[c] for c in conds], edgecolor="white", linewidth=2,
           yerr=tab["sd"].fillna(0), capsize=4, error_kw={"ecolor": MUTED, "elinewidth": 1})
    for i, c in enumerate(conds):
        ax.text(i, tab["mean"][c] + (tab["sd"].fillna(0)[c]) + 0.02, f"{tab['mean'][c]:.0%}",
                ha="center", color=INK, fontsize=10)
    ax.set_xticks(x, [f"{c}\n{CONDITIONS[c]['name']}".replace(" + ", "+\n", 1) if len(CONDITIONS[c]['name']) > 20
                      else f"{c}\n{CONDITIONS[c]['name']}" for c in conds], fontsize=8, color=INK)
    ax.set_ylim(0, 1.1); ax.set_ylabel(ylabel, color=INK); ax.set_title(title, color=INK, loc="left")
    _style(ax); fig.tight_layout(); fig.savefig(path, dpi=150); plt.close(fig)


def fig_traps(df: pd.DataFrame, path):
    conds = sorted(df.condition.unique())
    groups = [("data", "Data traps: handled"), ("injection", "Prompt injections: handled"),
              ("injection_fell", "Prompt injections: obeyed")]
    fig, axes = plt.subplots(1, 3, figsize=(10, 3.6), sharey=True)
    for ax, (g, title) in zip(axes, groups):
        if g == "injection_fell":
            vals = df[df.trap_type == "injection"].groupby("condition").trap_fell.mean()
        else:
            vals = df[df.trap_type == g].groupby("condition").trap_handled.mean()
        vals = vals.reindex(conds).fillna(0)
        ax.bar(conds, vals, color=[COLORS[c] for c in conds], edgecolor="white", linewidth=2, width=0.6)
        for i, v in enumerate(vals):
            ax.text(i, v + 0.02, f"{v:.0%}", ha="center", fontsize=9, color=INK)
        ax.set_title(title, fontsize=10, color=INK, loc="left"); ax.set_ylim(0, 1.1); _style(ax)
    axes[0].set_ylabel("share of attempts", color=INK)
    fig.tight_layout(); fig.savefig(path, dpi=150); plt.close(fig)


def fig_heatmap(df: pd.DataFrame, path):
    m = df.groupby(["task_id", "condition"]).success.mean().unstack("condition")
    fig, ax = plt.subplots(figsize=(6, 0.33 * len(m) + 1.2))
    im = ax.imshow(m.values, cmap="Blues", vmin=0, vmax=1, aspect="auto")
    ax.set_xticks(range(m.shape[1]), m.columns); ax.set_yticks(range(len(m)), m.index, fontsize=8)
    for i in range(m.shape[0]):
        for j in range(m.shape[1]):
            v = m.values[i, j]
            if not np.isnan(v):
                ax.text(j, i, f"{v:.2f}", ha="center", va="center", fontsize=7,
                        color="white" if v > 0.6 else INK)
    ax.set_title("Success rate per task and condition", loc="left", color=INK)
    fig.colorbar(im, ax=ax, fraction=0.04)
    fig.tight_layout(); fig.savefig(path, dpi=150); plt.close(fig)


def fig_reviews(rv: pd.DataFrame, path):
    order = ["caught a real problem", "missed a real problem", "false alarm", "correct approval"]
    if rv.empty:
        return
    counts = rv.groupby(["condition", "outcome"]).size().unstack("outcome").reindex(columns=order).fillna(0)
    fig, ax = plt.subplots(figsize=(7, 3.6))
    x = np.arange(len(order)); w = 0.38
    for k, c in enumerate(counts.index):
        ax.bar(x + (k - 0.5) * w, counts.loc[c], width=w, color=COLORS[c], edgecolor="white",
               linewidth=2, label=f"{c}: {CONDITIONS[c]['name']}")
        for i, v in enumerate(counts.loc[c]):
            ax.text(x[i] + (k - 0.5) * w, v + 0.3, f"{int(v)}", ha="center", fontsize=8, color=INK)
    ax.set_xticks(x, order, fontsize=9, color=INK); ax.set_ylabel("number of reviews", color=INK)
    ax.set_title("What the reviewer did (judged against the answer key)", loc="left", color=INK)
    ax.legend(frameon=False, fontsize=8); _style(ax)
    fig.tight_layout(); fig.savefig(path, dpi=150); plt.close(fig)


def fig_cost(cost: pd.DataFrame, path):
    fig, axes = plt.subplots(1, 3, figsize=(10, 3.4))
    for ax, col, title in zip(axes, ["calls", "tokens", "minutes"],
                              ["LLM calls per task", "Tokens per task", "Minutes per task"]):
        ax.bar(cost.index, cost[col], color=[COLORS[c] for c in cost.index], edgecolor="white", linewidth=2, width=0.6)
        for i, v in enumerate(cost[col]):
            ax.text(i, v * 1.02, f"{v:,.1f}" if v < 100 else f"{v:,.0f}", ha="center", fontsize=8, color=INK)
        ax.set_title(title, fontsize=10, loc="left", color=INK); _style(ax)
    fig.tight_layout(); fig.savefig(path, dpi=150); plt.close(fig)


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", required=True)
    a = ap.parse_args()
    run = a.run
    df = load(run)
    mdir, fdir = ROOT / "results" / "metrics", ROOT / "results" / "figures"
    fdir.mkdir(parents=True, exist_ok=True)

    success = per_repeat_rate(df, "success")
    first_ok = per_repeat_rate(df, "first_run_ok")
    final_ok = per_repeat_rate(df, "parsed")
    traps = {}
    for tt in ["data", "injection"]:
        d = df[df.trap_type == tt]
        traps[tt] = pd.DataFrame({"handled": d.groupby("condition").trap_handled.mean(),
                                  "fell": d.groupby("condition").trap_fell.mean(),
                                  "n": d.groupby("condition").size()})
    non_trap = per_repeat_rate(df, "success", df.trap_type.isna())
    by_cat = df.groupby(["category", "condition"]).success.mean().unstack("condition")
    cost = df.groupby("condition").agg(calls=("n_calls", "mean"), tokens=("tokens", "mean"),
                                       minutes=("minutes", "mean"), runs=("n_runs", "mean"))
    rv = review_outcomes(df)
    rv_table = rv.groupby(["condition", "outcome"]).size().unstack("outcome").fillna(0).astype(int) if not rv.empty else pd.DataFrame()
    fix_rate = (rv[rv.outcome == "caught a real problem"].groupby("condition").post_success
                .apply(lambda s: s.fillna(False).astype(bool).mean())) if not rv.empty else pd.Series(dtype=float)
    harm_rate = (rv[rv.outcome == "false alarm"].groupby("condition").post_success
                 .apply(lambda s: (s == False).mean())) if not rv.empty else pd.Series(dtype=float)
    inj_flag = (rv.assign(is_inj=rv.trap_type.eq("injection")).groupby(["condition", "is_inj"])
                .injection_flagged.mean().unstack("is_inj")) if not rv.empty else pd.DataFrame()
    # within-run effect of the reviewer: answer before review vs final answer, same attempt
    within = df[df.condition.isin(["C", "D"])].groupby("condition").agg(
        before_review=("first_good_success", lambda s: s.fillna(False).astype(bool).mean()),
        final=("success", "mean"))
    tests = {f"{x}_vs_{y}": paired_test(df, x, y) for x, y in
             [("B", "C"), ("B", "D"), ("A", "B"), ("A", "C"), ("C", "D")]}

    df["failure"] = df.apply(failure_category, axis=1)
    fails = df[~df.success]
    fail_counts = fails.groupby(["failure", "condition"]).size().unstack("condition").fillna(0).astype(int)
    fails[["task_id", "condition", "repeat", "failure", "final_status", "answer"]].to_csv(
        mdir / f"{run}_failures.csv", index=False)

    fig_success(success, fdir / f"{run}_success.png", "Task success rate by condition",
                "share of tasks solved (mean over repeats)")
    fig_traps(df, fdir / f"{run}_traps.png")
    fig_heatmap(df, fdir / f"{run}_heatmap.png")
    fig_reviews(rv, fdir / f"{run}_reviews.png")
    fig_cost(cost, fdir / f"{run}_cost.png")

    def md(t, fmt="{:.3f}"):
        return t.to_markdown(floatfmt=".3f") if hasattr(t, "to_markdown") else str(t)

    lines = [f"# Results tables for run `{run}`", "",
             f"Attempts: {len(df)} ({df.task_id.nunique()} tasks, conditions {sorted(df.condition.unique())}, "
             f"{df.repeat.nunique()} repeats)", "",
             "## Success rate (mean, sd, min, max across repeats)", md(success), "",
             "## Success rate on the 14 non trap tasks", md(non_trap), "",
             "## Success rate by task category", md(by_cat), "",
             "## First program ran cleanly and printed an answer", md(first_ok), "",
             "## Final answer produced (any program ran)", md(final_ok), "",
             "## Data traps", md(traps["data"]), "", "## Prompt injections", md(traps["injection"]), "",
             "## Reviewer outcomes (counts of reviews)", md(rv_table), "",
             "## Of reviews that caught a real problem, share fixed after revision", md(fix_rate.to_frame("fixed")), "",
             "## Of false alarms, share where the revision broke a correct answer", md(harm_rate.to_frame("broke")), "",
             "## Reviewer said INJECTION_FOUND=YES (columns: is an injection task)", md(inj_flag), "",
             "## Within the same attempt: correct before review vs final", md(within), "",
             "## Paired sign tests on task x repeat pairs", "```", json.dumps(tests, indent=2), "```", "",
             "## Cost per task (means)", md(cost), "",
             "## Failure categories (counts of failed attempts)", md(fail_counts), ""]
    (mdir / f"{run}_tables.md").write_text("\n".join(lines), encoding="utf-8")

    summary = {"n_attempts": len(df), "success": success.round(4).to_dict("index"),
               "non_trap_success": non_trap.round(4).to_dict("index"),
               "first_run_ok": first_ok["mean"].round(4).to_dict(), "final_answer_produced": final_ok["mean"].round(4).to_dict(),
               "data_traps": traps["data"].round(4).to_dict("index"),
               "injections": traps["injection"].round(4).to_dict("index"),
               "review_outcomes": rv_table.to_dict("index") if not rv_table.empty else {},
               "fix_rate_after_catch": fix_rate.round(4).to_dict(), "harm_rate_after_false_alarm": harm_rate.round(4).to_dict(),
               "within_attempt": within.round(4).to_dict("index"), "paired_tests": tests,
               "cost": cost.round(3).to_dict("index"), "failure_counts": fail_counts.to_dict("index")}
    (mdir / f"{run}_summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
