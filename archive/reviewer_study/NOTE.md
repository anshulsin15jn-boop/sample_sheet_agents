# Archived: reviewer agent study (earlier exploration)

This folder holds an earlier exploration from November 2026: a small study of whether a reviewer
agent makes a planner and coder agent team more correct on 20 data analysis tasks, inspired by the
code reviewer ablation in GenoMAS (arXiv 2507.21035).

It was paused after setup, a 20 task benchmark, the agent pipelines, and a short pilot, and the repo was pivoted to a more focused
question: why LLM agents fail at clinical trait extraction from GEO sample metadata (see the main
README). Some ideas from here were reused, mainly the logged LLM client (`src/llm.py`), the
resumable runner pattern, and the idea of a checker agent.

The code is kept as it was. To run it, work from this folder (`archive/reviewer_study`) so its
`src` package and `config.yaml` are used. Its results are pilot only and are not reported anywhere.
