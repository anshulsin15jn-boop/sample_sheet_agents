# Error type rates and tool use

Share of all attempts (cohort x repeat) whose main error is each type; attempts with accuracy of at least 95% count as solved and have no error type.

| Model | Method | Attempts | Values left unlabelled % | Wrong row % | Invalid output % |
|---|---|---|---|---|---|
| qwen2.5-coder:3b | F | 80 | 13.8 | 3.8 | 18.8 |
| qwen2.5:3b | F | 80 | 10.0 | 6.2 | 13.8 |

## Method F tool use

| Model | Attempts | Tool calls per cohort | Steps per cohort | Calls recovered from text % | Submitted | Used check_mapping | check_mapping flagged | Fixed after flag | Final answer passes check | Loop events |
|---|---|---|---|---|---|---|---|---|---|---|
| qwen2.5-coder:3b | 80 | 5.1 | 5.2 | 100 | 65 | 79 | 28 | 13 | 64 | bad arguments 40, no tool call 5, recovered from text 407 |
| qwen2.5:3b | 80 | 4.5 | 5.1 | 0 | 69 | 74 | 8 | 1 | 61 | bad arguments 17, no tool call 45 |
