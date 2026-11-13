# Error type rates and tool use

Share of all attempts (cohort x repeat) whose main error is each type; attempts with accuracy of at least 95% count as solved and have no error type.

| Model | Method | Attempts | Values left unlabelled % | Wrong row % | Invalid output % |
|---|---|---|---|---|---|
| qwen2.5-coder:3b | F | 5 | 0.0 | 20.0 | 0.0 |
| qwen2.5:3b | F | 5 | 20.0 | 0.0 | 0.0 |

## Method F tool use

| Model | Attempts | Tool calls per cohort | Steps per cohort | Calls recovered from text % | Submitted | Used check_mapping | check_mapping flagged | Fixed after flag | Final answer passes check | Loop errors |
|---|---|---|---|---|---|---|---|---|---|---|
| qwen2.5-coder:3b | 5 | 4.0 | 4.0 | 100 | 5 | 5 | 0 | 0 | 5 | recovered from text 20 |
| qwen2.5:3b | 5 | 4.8 | 5.4 | 0 | 5 | 5 | 2 | 1 | 4 | no tool call 3 |
