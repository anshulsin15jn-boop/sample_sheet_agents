# Why Can't Agents Read the Sample Sheet?

A focused study of one step in automated gene expression analysis that LLM agents are known to do
badly: **clinical trait extraction**, which means reading the short, messy descriptions attached to
each sample in a public dataset and deciding whether that sample is a disease case or a control.

**Short answer from this study:** with small free models, the simplest prompt worked best. Adding
worked examples and a reasoning format, or adding a checker agent, made results worse, mostly
because the model stopped labelling every value and the checker rejected answers that were already
right. Wrong row choice and unrecognised codes (such as `STEMI`) explain most of what remains.
A one page version is in [`results/summary.md`](results/summary.md).

## The nuance

Two papers from Haohan Wang's lab built LLM agents that run whole gene expression analyses end to
end. In both, almost every step worked well except this one:

| Paper | Clinical trait extraction | For contrast |
|---|---|---|
| GenoTEX (Liu et al., arXiv 2406.15341) | about 32.28% | |
| GenoMAS (Liu, Li, and Wang, arXiv 2507.21035) | about 32.61% | gene data preprocessing about 91% |

The authors call trait extraction a main bottleneck, and their system level improvements (planning,
review, mixing models) helped the pipeline overall without fixing this step. Both numbers use the
papers' own metric (CSC). This project does not reimplement CSC, so **the numbers here are not
directly comparable to theirs.**

## The question

Why do LLM agents fail at reading sample metadata, and which fixes actually help: worked examples,
structured reasoning, letting the agent abstain, or a checker agent? How do they compare with a
simple rule based baseline?

This is not a reproduction of GenoTEX or GenoMAS. It is a small, controlled study of their weakest
step, using free local models (`qwen2.5:3b` and `qwen2.5-coder:3b` through Ollama).

## Data

* **50 GEO cohorts, 15 traits, 9355 labelled samples** (10 development, 40 test). Details in
  [`benchmark/DATA_CARD.md`](benchmark/DATA_CARD.md); a plain language primer is in
  [`docs/biology_you_need.md`](docs/biology_you_need.md).
* **Inputs:** the sample metadata (title, source name, characteristics rows) from the header of each
  NCBI GEO series matrix file. Only the header is downloaded; the expression values never are.
* **Answer key:** the GenoTEX expert labels (one 0 or 1 per sample) and the metadata row the experts
  used, read from their released code as text.
* **Selection:** seeded and round robin across traits (at most 4 cohorts per trait), with only basic
  checks (binary labels, at least 3 samples per class). Nothing was chosen for difficulty.

## Task and methods

Following how GenoMAS frames the step, the agent sees the trait, the study title, and the distinct
values of every metadata row. It picks **one row** and maps each value to `disease`, `control`, or
`unknown`. Code applies the mapping to every sample and grades each sample against the experts.

| Method | What it adds |
|---|---|
| R rules | No LLM. Control words first, then trait words, then `trait: yes` rows |
| A zero shot | Task, cohort, JSON format |
| B few shot | A plus three solved development examples (pilot only, see below) |
| C structured reasoning | B plus a checklist (negation, codes, other diseases count as controls) and a reason before each label |
| D abstention | C plus permission to answer `unsure` or `cannot determine` |
| E extractor plus checker | C, then a second call reviews the answer; one revision if it asks for one |

All methods use Ollama's JSON mode, temperature 0.3 with a fixed seed per repeat, and the same
cohort description. Every answer is validated; a wrong row id or a mapping with no matching value
counts as invalid. Every LLM call is logged in `results/runs/<run>/calls.jsonl`.

## Results

Main run: 40 test cohorts, both models, 2 repeats, methods R, A, C, D, E (680 attempts, about 3.7
hours of LLM time on a laptop). Accuracy is per sample within each cohort, then averaged over
cohorts; ± is the spread (standard deviation) across the 2 repeats. A cohort is solved at 95%
accuracy or more. Full table: [`results/runs/main/metrics.md`](results/runs/main/metrics.md).

| Model | Method | Accuracy % | Macro F1 % | Row choice % | Solved (of 40) | Invalid % | Coverage % | Selective acc % |
|---|---|---|---|---|---|---|---|---|
| none | R rules | 55.8 | 60.5 | 77.5 | 13 | 0 | 62.8 | 91.5 |
| qwen2.5:3b | A zero shot | **71.7 ± 2.9** | **71.1 ± 2.8** | 85.0 | **19.0** | 5.0 | 81.7 | 88.6 |
| qwen2.5:3b | C reasoning | 58.8 ± 0.6 | 57.4 ± 2.2 | 83.7 | 13.0 | 12.5 | 63.4 | 91.7 |
| qwen2.5:3b | D abstain | 63.1 ± 1.2 | 65.4 ± 0.4 | 87.5 | 15.5 | 8.8 | 66.2 | 95.8 |
| qwen2.5:3b | E checker | 55.2 ± 4.9 | 54.9 ± 3.8 | 67.5 | 11.5 | 10.0 | 67.8 | 83.3 |
| qwen2.5-coder:3b | A zero shot | **76.3 ± 5.4** | **77.0 ± 5.0** | 88.8 | **24.5** | 5.0 | 82.9 | 92.2 |
| qwen2.5-coder:3b | C reasoning | 73.5 ± 2.8 | 75.6 ± 2.5 | 85.0 | 23.0 | 7.5 | 81.1 | 90.4 |
| qwen2.5-coder:3b | D abstain | 75.5 ± 4.4 | 76.2 ± 4.9 | 85.0 | 24.5 | 7.5 | 85.4 | 89.0 |
| qwen2.5-coder:3b | E checker | 67.6 ± 0.6 | 64.9 ± 0.5 | 75.0 | 18.0 | 7.5 | 83.2 | 81.1 |

![Accuracy by method](results/figures/accuracy_by_method.png)

What the numbers say:

1. **Every LLM method beats the rule on average, but not on every cohort.** The rule is precise when
   it answers (91.5% selective accuracy) but labels only 63% of samples. It still beats zero shot
   on 7 (`qwen2.5:3b`) or 8 (`qwen2.5-coder:3b`) of the 40 cohorts.
2. **The longer prompt hurt the smaller general model.** For `qwen2.5:3b`, C was worse than A on 25
   cohorts and better on 10. The cause is visible directly: with the reasoning format the model left
   **29% of the values in its chosen row unlabelled**, against 11% for A. Writing a reason for each
   value seems to make it stop early. `qwen2.5-coder:3b` handled the longer format (12% missing) and
   lost only 3 points.
3. **Abstention worked as designed for `qwen2.5:3b`, and only as a trade.** Selective accuracy rose
   to 95.8%, but coverage stayed at 66%, so total accuracy stayed below zero shot.
4. **The checker made things worse for both models.** It asked for a revision in 137 of 146 valid
   reviews, so it barely discriminated. For `qwen2.5-coder:3b` the revision broke 14 answers that
   were already solved and improved 3. For `qwen2.5:3b` it improved 16 and made 25 worse (9 of them
   already solved). This is the opposite of what a reviewer is for.
5. **Model choice mattered more than prompting.** The coder model was better for every method and
   was also faster (8 s against 13 s per zero shot answer).

## Why the agents fail

Every failed cohort attempt (accuracy below 95%) was sorted into one main error type, in a fixed
priority order (`src/analyze.py`). Counts per repeat:

![Error categories](results/figures/error_categories.png)

| Error type | All failed attempts | What it looks like |
|---|---|---|
| values left unlabelled | 130 | The right row, but some of its values get no label |
| wrong row | 68 | Picks a row with one value (`disease state: HCC`) or a tissue row instead of the case/control row |
| synonym or code missed | 52 | `diagnosis: STEMI` labelled control for coronary artery disease |
| invalid output | 51 | Mostly a row id that does not match the values written (19 times the values came exactly from another real row) |
| abstained | 28 | D said `cannot determine` or `unsure` for most samples |
| other disease as disease | 28 | `diagnosis: IEI` labelled disease in an asthma study |
| other / flipped labels | 12 | |

Two real examples (more in [`results/runs/main/error_examples.md`](results/runs/main/error_examples.md)):

* **GSE174570, liver cancer, zero shot, `qwen2.5:3b`, 50%.** The model chose the row
  `disease state: HCC`, which has the same value for every sample, so it cannot separate anything.
  The experts used `tissue: Tumour (liver)` against `tissue: Non-tumour adjacent (liver)`. The model
  matched the trait word instead of looking for the row that splits the samples.
* **GSE109048, coronary artery disease, abstention, `qwen2.5:3b`, 67%.** Right row, but
  `diagnosis: STEMI` was labelled control with the reason "ST-elevation myocardial infarction". The
  model expanded the abbreviation correctly and still did not connect a heart attack to coronary
  artery disease.

Seven test and development cohorts contain expert labels that are debatable (for example, lesional
skin from a different disease labelled control in a lupus study). They are flagged in
`src/analyze.py` and in the error examples instead of being silently counted as model mistakes.

## Limitations

* **Small models only.** Two 3 billion parameter models on a laptop. Larger models may behave very
  differently, especially with the reasoning format and the checker.
* **40 test cohorts and 2 repeats.** Differences of a few points (for example A against D for the
  coder model) are within noise. The large gaps (A against C and E for `qwen2.5:3b`) are consistent
  across cohorts.
* **Method B was dropped from the main run** to fit the time budget (see
  [`results/runs/pilot/ESTIMATE.md`](results/runs/pilot/ESTIMATE.md)). So the main run cannot say
  whether the drop from A to C comes from the examples, the reasoning format, or both. In the 5
  cohort pilot, B scored 68.5% against 44.3% for A, but that is too small to settle it.
* **Binary traits only,** and only cohorts where a single metadata row explains the expert labels.
* **The answer key is inherited** from GenoTEX and includes judgment calls.
* **The metric is not CSC,** so nothing here should be compared number for number with the papers.
* **The rule was written by the same person who built the benchmark** and had seen the development
  cohorts, which may flatter it slightly.
* **GEO text is public,** so the models may have seen some of these studies during training.
* **Pooled accuracy** (in `metrics.md`) is dominated by GSE178201, which holds 3984 of the 7362
  labelled test samples. The per cohort mean is the main number for that reason.

## What is new here

GenoTEX and GenoMAS report this step as one number inside a full pipeline. This project isolates it:
a standalone benchmark with per value grading, a rule baseline, a controlled comparison of common
fixes, and an error taxonomy with real examples. The practical lessons for small models: keep the
output format short, require a label for every value, and do not add a checker unless it can be
shown to reject wrong answers more often than right ones.

## Next steps

* Run the same benchmark with a larger hosted model to see whether the reasoning and checker
  results reverse.
* Add B back to separate the effect of examples from the effect of the reasoning format.
* Enforce complete mappings (ask again for missing values) and give the agent a tool that shows how
  many samples each value covers, aimed at the two largest error types.
* Score with the papers' CSC metric for a direct comparison.

## Reproduce

```bash
python -m venv .venv && .venv/Scripts/pip install -r requirements.txt   # Windows path shown
ollama pull qwen2.5:3b && ollama pull qwen2.5-coder:3b
python -m scripts.build_benchmark          # downloads headers and labels, writes benchmark/cohorts
python -m pytest                           # 24 tests
python -m src.run_experiment --run main --cohorts test --methods R,A,C,D,E --repeats 2
python -m src.analyze --run main
python -m scripts.make_figures --run main
```

The runner is resumable: stop it with Ctrl+C and run the same command again to continue. Settings
(model context 8192, temperature 0.3, seeds, token cap 1000) are in `config.yaml`.

## Credit and licensing

* **GenoTEX:** Liu et al., arXiv 2406.15341. The expert labels and trait rows used as the answer key come from the
  GenoTEX release (Hugging Face `Liu-Hy/GenoTEX`), licensed **CC BY 4.0**. This project uses a
  small subset and changes only its format.
* **GenoMAS:** Liu, Li, and Wang, arXiv 2507.21035. The task framing (choose a row, map its
  values) follows this work.
* **NCBI GEO:** sample metadata comes from public GEO series matrix files.
* Models: Qwen2.5 3B and Qwen2.5 Coder 3B, run locally through Ollama.
