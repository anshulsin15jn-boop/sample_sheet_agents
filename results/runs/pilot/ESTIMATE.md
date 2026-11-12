# Pilot timing and the main run plan

Pilot: methods R and A to E on 5 development cohorts (GSE120490, GSE123088, GSE131282, GSE135589,
GSE212866), model qwen2.5:3b, 1 repeat, max 1500 tokens. Measured from `attempts.jsonl`:

* LLM time per cohort (A to E together): 187 s. Per method: A 35 s, B 44 s, C 33 s, D 29 s, E 46 s.
* Two of 33 calls ran to the 1500 token cap without finishing the JSON (invalid). The longest valid
  answer was 575 tokens, so a 1000 token cap changes no valid answer and saves about 8% of time.

Full plan (40 test cohorts, 2 models, 3 repeats, A to E): 40 x 2 x 3 x 187 s = about 12.5 hours.
Scaled down in the order the plan sets:
1. 2 repeats: about 8.3 hours, still over 6.
2. Drop method B: (35 + 33 + 29 + 46) s x 0.92 = about 132 s per cohort, so
   40 x 2 x 2 x 132 s = about 5.9 hours. This is what the main run uses, with all 40 test cohorts.

Consequence: the main run cannot separate "examples alone" (B) from "examples plus reasoning" (C).
The pilot B number is reported, clearly marked as 5 development cohorts and 1 repeat.
