# Summary: Why Can't Agents Read the Sample Sheet?

**Pitch.** GenoTEX and GenoMAS, two LLM agent systems for gene expression analysis, were both held
back by one step: reading the free text description of each sample to decide whether it is a
disease case or a control (about 32% on their metric). I built a 50 cohort benchmark for that step
from public GEO data and the GenoTEX expert labels, then compared a keyword rule with six LLM
strategies, including a tool calling agent, on two small free models. Zero shot prompting gave the
best of the configurations tested, a checker agent made answers worse, and the tool agent fixed the
errors it targeted for one model while adding new failures in its own loop. Most failures came from
values left unlabelled, the wrong metadata row, and medical codes the model did not connect to the
trait.

## What I did

* 40 test cohorts across 15 traits. Input: GEO sample metadata. Answer key: GenoTEX expert labels
  (CC BY 4.0). 10 more cohorts used only for prompt examples and pilots.
* The agent picks one metadata row and labels each of its values; code grades every sample.
* Models: `qwen2.5:3b` and `qwen2.5-coder:3b`, run locally with Ollama. 2 repeats, temperature 0.3,
  fixed seeds. 920 test attempts in three runs, about 6 hours of model time.
* Metric: mean per sample accuracy over cohorts. It is not the papers' CSC metric, so it is not
  comparable to their 32%.

## Results (mean accuracy %, ± spread over 2 repeats)

| Method | qwen2.5:3b | qwen2.5-coder:3b |
|---|---|---|
| R keyword rule (no LLM) | 55.8 | 55.8 |
| A zero shot | 71.7 ± 2.9 | **76.3 ± 5.4** |
| B few shot | not run | 75.5 ± 1.5 |
| C examples plus reasoning | 58.8 ± 0.6 | 73.5 ± 2.8 |
| D C plus abstention | 63.1 ± 1.2 | 75.5 ± 4.4 |
| E C plus checker agent | 55.2 ± 4.9 | 67.6 ± 0.6 |
| F tool calling agent | 72.3 ± 12.6 | 64.5 ± 13.5 |

Bold is the best of the configurations tested; several rows are within its spread.

## Findings

1. **Zero shot beat structured reasoning for `qwen2.5:3b` only.** For that model the reasoning
   format made it leave 29% of values unlabelled (11% with zero shot). For `qwen2.5-coder:3b`, A,
   B, C, and D were within noise of each other, so examples and reasoning neither helped nor hurt.
2. **The coding model scored higher with methods A to E,** clearly so for C, D, and E. For zero
   shot the gap is within the repeat spread.
3. **Abstention traded coverage for precision.** `qwen2.5:3b` was right on 95.8% of what it labelled
   but labelled only 66% of samples.
4. **The checker hurt.** It asked for a revision in 137 of 146 reviews; revisions made 47 answers
   worse (23 of them already correct) and 19 better. GenoMAS found review useful, so my hypothesis
   is that a 3B checker is too weak. I have not tested that yet.
5. **The tool agent (F) moved errors around instead of removing them.** Against zero shot, by the
   rule I fixed before running it, neither model shows a clear accuracy difference. For
   `qwen2.5:3b` it cut attempts failing on unlabelled values from 22.5% to 10.0% and on the wrong
   row from 10.0% to 6.2%, and solved 23 cohorts against 19. For `qwen2.5-coder:3b` it was worse on
   19 cohorts and better on 7. Invalid answers rose to 13.8% and 18.8%, all from attempts that used
   the 8 tool calls without submitting. The coding model often wrote its whole plan, including a
   `submit_answer` with placeholder values, before seeing any tool output; this happened in 26 of
   40 cohorts with one seed and 1 of 40 with the other, which explains most of its spread.
6. **Main failure types across all runs:** values left unlabelled (165 failed attempts), wrong row
   (82), invalid output (78), missed synonym or code such as `STEMI` (74).

## Caveats

Two small models, 40 cohorts, 2 repeats. B was run only on `qwen2.5-coder:3b`, so for
`qwen2.5:3b` the drop from A to C still cannot be split between examples and reasoning. F's
result depends on an untuned budget of 8 tool calls and, for the coding model, on a parser that
recovers tool calls written as text. A few expert labels are judgment calls; I flag them.

## Next

Make the agent loop stricter (one tool call per message, no submit before reading the row); run B
on `qwen2.5:3b`; try a larger checker; try a larger extractor; score with CSC.

Paper version: [`report/report.md`](../report/report.md).

Credits: GenoTEX (arXiv 2406.15341, data CC BY 4.0), GenoMAS (arXiv 2507.21035), NCBI GEO.
