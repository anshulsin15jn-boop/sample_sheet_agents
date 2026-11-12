# Summary: Why Can't Agents Read the Sample Sheet?

**Pitch.** GenoTEX and GenoMAS, two agent systems for gene expression analysis from Haohan Wang's
lab, were both held back by one step: reading free text sample descriptions to decide which samples
are disease cases (about 32% on their metric). I built a 50 cohort benchmark for that step from GEO
and the GenoTEX expert labels, then compared a keyword rule with five LLM strategies on two small
free models. The simplest prompt won; examples plus step by step reasoning and a checker agent made
things worse, and the failures come mostly from incomplete labelling, wrong row choice, and
unrecognised medical codes.

## Setup

* 40 test cohorts (15 traits, binary case versus control), GEO sample metadata as input, GenoTEX
  expert labels as the answer key. 10 more cohorts for development and examples.
* The agent picks one metadata row and labels each of its values; code grades every sample.
* Models: `qwen2.5:3b` and `qwen2.5-coder:3b` (Ollama, local). 2 repeats, temperature 0.3, fixed
  seeds. 680 attempts, about 3.7 hours of LLM time.
* Metric: mean per sample accuracy over cohorts. Not the papers' CSC metric, so not comparable to 32%.

## Results (mean accuracy %, ± spread over 2 repeats)

| Method | qwen2.5:3b | qwen2.5-coder:3b |
|---|---|---|
| R keyword rule (no LLM) | 55.8 | 55.8 |
| A zero shot | **71.7 ± 2.9** | **76.3 ± 5.4** |
| C examples plus reasoning | 58.8 ± 0.6 | 73.5 ± 2.8 |
| D C plus abstention | 63.1 ± 1.2 (95.8% accurate on 66% answered) | 75.5 ± 4.4 |
| E C plus checker agent | 55.2 ± 4.9 | 67.6 ± 0.6 |

## Findings

1. **Simple beats elaborate for small models.** With the reasoning format `qwen2.5:3b` left 29% of
   values unlabelled (11% in zero shot) and was worse on 25 of 40 cohorts.
2. **The checker does not check.** It asked for a revision in 137 of 146 reviews and made 47 answers
   worse (23 of them already correct) and 19 better.
3. **Abstention trades coverage for precision**, as intended, but did not raise total accuracy.
4. **Failure types:** values left unlabelled (130 failed attempts), wrong row (68), missed synonym
   or code such as `STEMI` (52), invalid output (51), other disease labelled as the trait (28).
5. **The rule is precise but incomplete** (91.5% accurate on the 63% it labels) and still beats the
   LLM on 7 or 8 cohorts.

## Caveats

Two small models, 40 cohorts, 2 repeats. Method B (examples only) was cut for time, so the drop from
A to C cannot be split between examples and reasoning. Expert labels include a few judgment calls,
which are flagged.

## Next

Larger hosted model; add B back; force complete mappings; give the agent per value sample counts;
score with CSC.

Credit: GenoTEX (arXiv 2406.15341, data CC BY 4.0), GenoMAS (arXiv 2507.21035), NCBI GEO.
