# Summary: Why Can't Agents Read the Sample Sheet?

**Pitch.** GenoTEX and GenoMAS, two LLM agent systems for gene expression analysis, were both held
back by one step: reading the free text description of each sample to decide whether it is a
disease case or a control (about 32% on their metric). I built a 50 cohort benchmark for that step
from public GEO data and the GenoTEX expert labels, then compared a keyword rule with LLM prompting
strategies on two small free models. The simplest prompt did best, a checker agent made answers
worse, and most failures came from values left unlabelled, the wrong metadata row, and medical codes
the model did not connect to the trait.

## What I did

* 40 test cohorts across 15 traits. Input: GEO sample metadata. Answer key: GenoTEX expert labels
  (CC BY 4.0). 10 more cohorts used only for prompt examples.
* The agent picks one metadata row and labels each of its values; code grades every sample.
* Models: `qwen2.5:3b` and `qwen2.5-coder:3b`, run locally with Ollama. 2 repeats, temperature 0.3,
  fixed seeds. 680 attempts, about 3.7 hours of model time.
* Metric: mean per sample accuracy over cohorts. It is not the papers' CSC metric, so it is not
  comparable to their 32%.

## Results (mean accuracy %, ± spread over 2 repeats)

| Method | qwen2.5:3b | qwen2.5-coder:3b |
|---|---|---|
| R keyword rule (no LLM) | 55.8 | 55.8 |
| A zero shot | **71.7 ± 2.9** | **76.3 ± 5.4** |
| C examples plus reasoning | 58.8 ± 0.6 | 73.5 ± 2.8 |
| D C plus abstention | 63.1 ± 1.2 | 75.5 ± 4.4 |
| E C plus checker agent | 55.2 ± 4.9 | 67.6 ± 0.6 |

## Findings

1. **Simplest was best.** With `qwen2.5:3b`, zero shot beat every longer prompt clearly; the
   reasoning format made the model leave 29% of values unlabelled (11% with zero shot). With the
   coding model, A, C, and D were within noise of each other.
2. **The coding model scored higher with every method,** clearly so for C, D, and E. For zero shot
   the gap is within the repeat spread.
3. **Abstention traded coverage for precision.** `qwen2.5:3b` was right on 95.8% of what it labelled
   but labelled only 66% of samples.
4. **The checker hurt.** It asked for a revision in 137 of 146 reviews; revisions made 47 answers
   worse (23 of them already correct) and 19 better. GenoMAS found review useful, so my hypothesis
   is that a 3B checker is too weak. I have not tested that yet.
5. **Main failure types:** values left unlabelled (130 failed attempts), wrong row (68), missed
   synonym or code such as `STEMI` (52), invalid output (51).

## Caveats

Two small models, 40 cohorts, 2 repeats. Method B (examples only) was not run in the main
experiment, so the drop from A to C cannot be split between examples and reasoning. A few expert
labels are judgment calls; I flag them.

## Next

Run method B; try a larger checker; try a larger extractor; force complete mappings; score with CSC.

Credits: GenoTEX (arXiv 2406.15341, data CC BY 4.0), GenoMAS (arXiv 2507.21035), NCBI GEO.
