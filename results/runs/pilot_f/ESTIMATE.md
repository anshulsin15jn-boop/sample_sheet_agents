# Method F pilot: timing and the follow up run plan

Pilot: method F on the 5 development pilot cohorts (GSE120490, GSE123088, GSE131282, GSE135589,
GSE212866), both models, 1 repeat, at most 8 tool calls per cohort.

## A finding from the first pilot (kept in `results/runs/pilot_f_native/`)

`qwen2.5-coder:3b` never used Ollama's native tool interface. It wrote every tool call as a JSON
object inside a code block in its text, so Ollama returned no tool calls, all 8 steps were spent,
and all 5 attempts were invalid. `qwen2.5:3b` used the native interface.

Before any test cohort was run, I added a recovery step to the agent loop: a JSON object in the
text that names a known tool is run as a tool call and flagged as "recovered". The pilot below
uses that version.

## Pilot results (this folder)

| Model | Seconds per cohort | Mean accuracy | Tool calls per cohort | Calls recovered from text | check_mapping flagged | Then fixed |
|---|---|---|---|---|---|---|
| qwen2.5:3b | 67 | 81.7% | 4.8 | 0 of 24 | 2 | 1 |
| qwen2.5-coder:3b | 26 | 76.6% | 4.0 | 20 of 20 | 0 | 0 |

Five cohorts and one repeat are far too few to compare methods; these numbers are only for timing.

## Plan

* Method F, 40 test cohorts, 2 repeats: 80 x 67 s (about 1.5 hours) for `qwen2.5:3b` plus 80 x 26 s
  (about 0.6 hours) for `qwen2.5-coder:3b`, about 2.1 hours. Under the 2.5 hour limit, so both
  models are run (`results/runs/main_f/`).
* Method B on `qwen2.5-coder:3b`, 40 test cohorts, 2 repeats: about 15 s per cohort (its zero shot
  calls took 8 s and its reasoning calls 18 s), about 0.3 hours. Total about 2.4 hours, under the
  4 hour limit, so B is run too (`results/runs/main_b/`).
* Same seeds as the main run (base seed + repeat). Results for R, A, C, D, E are not rerun.
