# Why Can't Agents Read the Sample Sheet?

Work in progress. A focused study of one step in automated gene expression analysis that LLM agents
are known to do badly: **clinical trait extraction**, which means reading the short, messy
descriptions attached to each sample in a public dataset and deciding whether that sample is a
disease case or a control.

## The nuance

Two papers from Haohan Wang's lab built LLM agents that run whole gene expression analyses end to
end. In both, almost every step worked well except this one:

| Paper | Clinical trait extraction | For contrast |
|---|---|---|
| GenoTEX (Liu et al., arXiv 2406.15341) | about 32.28% | |
| GenoMAS (Liu, Li, and Wang, arXiv 2507.21035) | about 32.61% | gene data preprocessing about 91% |

The authors call trait extraction a main bottleneck, and their system level improvements (planning,
review, mixing models) helped the pipeline overall without fixing this step. Both numbers use the
papers' own metric (CSC), which this project does not reimplement, so the numbers here are not
directly comparable to theirs.

## The question

Why do LLM agents fail at reading sample metadata, and which fixes actually help: worked examples,
structured choices, letting the agent abstain, or a checker agent? How do they compare with a simple
rule based baseline?

This is not a reproduction of GenoTEX or GenoMAS. It is a small study of their weakest step, using
free local models (`qwen2.5:3b` and `qwen2.5-coder:3b` through Ollama).

## Status

- [x] Phase 0: pivot and setup
- [ ] Phase 1: benchmark (GEO sample metadata as input, GenoTEX expert labels as the answer key)
- [ ] Phase 2: methods (rule baseline plus five LLM methods)
- [ ] Phase 3: experiments and error analysis
- [ ] Phase 4: writeup

## Credit and data

Answer key labels will come from the GenoTEX release (CC BY 4.0). Sample descriptions come from
public NCBI GEO series matrix files. Full citations and a statement of what is new here will be
added in Phase 4.

## Archived earlier work

An earlier exploration in this repo (does a reviewer agent help a coder agent team?) is kept in
`archive/reviewer_study/`.
