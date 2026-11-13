# Why Can't Agents Read the Sample Sheet? Clinical Trait Extraction from GEO Metadata with Small Local LLM Agents

Anshul

## Abstract

LLM agents can now run most of a gene expression analysis, but one step has stayed hard: clinical
trait extraction, which reads the free text metadata of each sample and decides whether it is a
disease case or a control. GenoTEX and GenoMAS report about 32% on this step, against about 91% for
gene data preprocessing. I isolate it as a standalone benchmark of 50 GEO cohorts (9355 samples)
with the GenoTEX expert labels as the answer key and per sample grading. On 40 test cohorts I
compare a keyword rule with six LLM strategies (zero shot, few shot, structured reasoning,
abstention, an extractor with a checker, and a tool calling agent) on two free 3B models run
locally, with 2 repeats and fixed seeds, 920 graded attempts in total. The best of the
configurations tested is zero shot with `qwen2.5-coder:3b` at 76.3% mean per sample accuracy,
against 55.8% for the rule. For `qwen2.5:3b`, zero shot beat structured reasoning by more than the
repeat spread; for the coder model the prompt variants were within noise. A 3B checker made
answers worse (47 revisions hurt, 19 helped). A tool calling agent, compared with zero shot under a
plan fixed before it was run, halved the share of attempts that failed by leaving values
unlabelled for `qwen2.5:3b` (22.5% to 10.0%), but added invalid answers in its own loop for both
models, so neither model shows a clear accuracy gain. An error analysis of every failed attempt
shows that most failures are incomplete labelling, the wrong metadata row, and medical codes the
model does not link to the trait.

## 1 Introduction

LLM agents can now carry out most of a gene expression analysis on their own: find datasets,
preprocess them, and test which genes relate to a trait. Two recent systems from the same group
show this, and also show one step that does not work. In the GenoTEX benchmark [1], clinical trait
extraction scored about 32.28%, and in the GenoMAS multi agent system [2] it scored about 32.61%,
while gene data preprocessing in GenoMAS reached about 91%. Clinical trait extraction is the step
that reads the free text metadata of each sample in a GEO study [3] (for example
`diagnosis: STEMI`, `tissue: Non-tumour adjacent (liver)`, or `genotype: T21`) and decides whether
the sample has the trait. Everything after it depends on those labels: a mislabelled group makes
every downstream association test wrong. GenoMAS improved its overall pipeline with planning, code
review, and a mix of models, but this step stayed near 32%.

I isolate this one step. I build a benchmark of 50 GEO cohorts with the GenoTEX expert labels as the
answer key, grade answers per sample, and compare a keyword rule with six LLM strategies on two free
3B parameter models run locally: zero shot, few shot, structured reasoning, abstention, an
extractor with a checker, and a tool calling agent. I then sort every failure into an error type.
My contributions are:

1. a standalone benchmark for clinical trait extraction with per sample grading and per value
   error categories, built only from public metadata and the CC BY 4.0 GenoTEX labels;
2. a controlled comparison of common agent fixes on the same cohorts and seeds, including a tool
   calling agent whose tools target the two most common error types, evaluated against a
   comparison plan written before it was run;
3. an error analysis with real examples, which shows that most failures are incomplete labelling,
   the wrong metadata row, and medical codes the model does not link to the trait, and that the
   tool agent's own failures come from how small models drive the loop.

## 2 Related work

**Agents for gene expression analysis.** GenoTEX [1] is a benchmark in which experts preprocessed
GEO datasets for many traits and recorded which samples are cases; it reports trait extraction as
a main bottleneck for LLM agents. GenoMAS [2] builds a team of agents with planning and code
review on top of it. I reuse the GenoMAS task framing (choose a metadata row, map its values) and
the GenoTEX labels, and study the extraction step alone.

**Metadata curation.** GEO metadata is free text written by thousands of labs without a shared
vocabulary [3, 4]. Earlier work extracted case and control signatures from GEO by crowdsourcing
[5], which shows how much manual effort this labelling has needed.

**Prompting strategies.** Few shot examples [6], step by step reasoning [7, 8], and self review or
refinement [9] often help large models. Self correction without external feedback can also fail or
hurt [10]. Selective prediction lets a model abstain to trade coverage for accuracy [11].

**Tool use.** ReAct [12] interleaves reasoning with actions, and Toolformer [13] trains models to
call tools. My method F uses native tool calling through the Ollama chat API, with tools that
return grounded information (row values and sample counts) and check a draft answer.

## 3 Benchmark

**Cohorts.** I sampled 50 GEO series across 15 traits from the GenoTEX release with a fixed seed,
taking cohorts round robin across traits (at most 4 per trait) and keeping only cohorts with
binary labels, at least 3 samples per class, and samples present in the GEO header. A second seed
split them into 10 development cohorts (used only for prompt examples and pilots) and 40 test
cohorts. The 50 cohorts contain 9355 labelled samples. Cohorts were never chosen by difficulty.

**Inputs and answer key.** The input is the header of each GEO series matrix file: sample titles,
source names, and characteristics rows. I stream only the header, so no expression values are
downloaded. The answer key is the GenoTEX expert label (0 or 1) of each sample and the metadata
row the experts used, read from their released code as text.

**Task.** Following GenoMAS, the agent sees the trait and the distinct values of every metadata
row, chooses one row, and maps each value to disease, control, or unknown. Code applies the mapping
to every sample. Rows with more than 30 distinct values are shortened by replacing numbers with
`#`, except purely numeric rows such as a CAG repeat length, which are shown as numbers.

**Metrics.** Per sample accuracy within each cohort, averaged over cohorts (one cohort holds 3984
of the 7362 labelled test samples, so pooling would mostly measure that study); macro F1 over the
disease and control classes; row choice accuracy (whether the chosen row can explain the expert
labels); solved cohorts (accuracy of at least 95%); the invalid answer rate; and, for abstention,
coverage and selective accuracy. I report the mean over 2 repeats with different seeds and their
standard deviation, and I treat any difference smaller than that spread as no difference. This is
not the CSC metric of [1, 2], so the numbers are not directly comparable with theirs.

## 4 Methods

All LLM methods use the same description of the cohort, Ollama's JSON mode (except F, which uses
tool calls), temperature 0.3, and a fixed seed per repeat. Every answer is validated; a row id that
does not exist, or a mapping that matches no value of the row, is an invalid answer.

* **R, rules.** No LLM. Control words first (control, normal, healthy, non, adjacent, ...), then
  words from the trait name, then `trait: yes` rows. It picks the row that gets both labels.
* **A, zero shot.** The task, the cohort, and the answer format.
* **B, few shot.** A plus three solved development cohorts.
* **C, structured reasoning.** B plus a checklist (negation, abbreviations, other diseases count as
  controls) and a short reason written before each label.
* **D, abstention.** C plus permission to answer unsure per value or cannot determine per cohort.
* **E, extractor plus checker.** C, then a second call reviews the answer and may request one
  revision.
* **F, tool calling agent.** The model does not see the metadata up front. It has four tools:
  `list_rows` (row ids, number of distinct values, three examples), `get_row_values` (distinct
  values with sample counts), `check_mapping` (values still unlabelled, labels for values not in
  the row, and a warning when the row has only one distinct value), and `submit_answer` (validated
  like every other method). The loop allows at most 8 tool calls; a turn without a tool call also
  uses one step. Unknown tools, malformed arguments, server rejections, and timeouts are returned
  to the model as error messages so it can continue. If no valid answer is submitted, the attempt
  is invalid. In the development pilot `qwen2.5-coder:3b` wrote its tool calls as JSON text instead
  of using the tool interface, so before any test run I added a recovery step that runs such text
  calls and flags them; I report how often each model needed it.

Models: `qwen2.5:3b` [14] and `qwen2.5-coder:3b` [15], 4 bit, through Ollama on a laptop CPU.
Methods R, A, C, D, and E ran on both models (680 attempts, about 3.7 hours), F on both models
(160 attempts), and B, because of the time budget, on `qwen2.5-coder:3b` only (80 attempts); F and
B together took about 2.2 hours. Before running F on the test cohorts I wrote down its comparison
in the project README: F against A for each model on accuracy, macro F1, row choice, solved
cohorts, and invalid rate; the share of attempts failing by unlabelled values and by wrong row;
and the agent's tool use. Every LLM and tool call is logged.

## 5 Results

Table 1 gives the main results. The best of the configurations tested is zero shot with
`qwen2.5-coder:3b`, at 76.3% accuracy and 24.5 of 40 cohorts solved, against 55.8% and 13 for the
rule. Even this configuration leaves more than a third of the cohorts unsolved.

**Table 1.** Test cohorts (40), mean over cohorts, ± spread over 2 repeats.

| Model | Method | Accuracy % | Macro F1 % | Row choice % | Solved | Invalid % |
|---|---|---|---|---|---|---|
| none | R | 55.8 | 60.5 | 77.5 | 13.0 | 0.0 |
| qwen2.5:3b | A | 71.7 ± 2.9 | 71.1 ± 2.8 | 85.0 | 19.0 | 5.0 |
| qwen2.5:3b | C | 58.8 ± 0.6 | 57.4 ± 2.2 | 83.7 | 13.0 | 12.5 |
| qwen2.5:3b | D | 63.1 ± 1.2 | 65.4 ± 0.4 | 87.5 | 15.5 | 8.8 |
| qwen2.5:3b | E | 55.2 ± 4.9 | 54.9 ± 3.8 | 67.5 | 11.5 | 10.0 |
| qwen2.5:3b | F | 72.3 ± 12.6 | 74.1 ± 10.8 | 80.0 | 23.0 | 13.8 |
| qwen2.5-coder:3b | A | **76.3 ± 5.4** | 77.0 ± 5.0 | 88.8 | 24.5 | 5.0 |
| qwen2.5-coder:3b | B | 75.5 ± 1.5 | 77.2 ± 0.7 | 91.3 | 21.5 | 1.2 |
| qwen2.5-coder:3b | C | 73.5 ± 2.8 | 75.6 ± 2.5 | 85.0 | 23.0 | 7.5 |
| qwen2.5-coder:3b | D | 75.5 ± 4.4 | 76.2 ± 4.9 | 85.0 | 24.5 | 7.5 |
| qwen2.5-coder:3b | E | 67.6 ± 0.6 | 64.9 ± 0.5 | 75.0 | 18.0 | 7.5 |
| qwen2.5-coder:3b | F | 64.5 ± 13.5 | 64.7 ± 14.3 | 77.5 | 19.5 | 18.8 |

**Prompting effects are model specific.** For `qwen2.5:3b`, zero shot beat C, D, and E by more
than the repeat spread; C was worse than A on 25 cohorts and better on 10, and it left 29% of the
values in the chosen row unlabelled against 11% for A. For `qwen2.5-coder:3b`, A, B, C, and D lie
between 73.5% and 76.3%, all within noise; B was better than A on 10 cohorts and worse on 10. So
the claim that zero shot beats structured reasoning holds for `qwen2.5:3b` only. The coder model
scored higher than the general model with A to E, clearly for C, D, and E.

**Abstention** raised the selective accuracy of `qwen2.5:3b` to 95.8% (zero shot 88.6%) but covered
only 66% of samples, so its total accuracy stayed below zero shot.

**The checker hurt.** In E the checker asked for a revision in 137 of 146 valid reviews. Against the
first answer, 47 revisions were worse (23 of those first answers were fully correct) and 19 were
better. This matches reports that self correction without external feedback can hurt [10], and
contrasts with GenoMAS [2], where review helped; one explanation is that a 3B model is too weak to
judge, which I have not tested.

**The tool agent (Table 2).** Under the planned rule, neither model shows a clear accuracy
difference between F and A, because F's spread (12.6 and 13.5 points) exceeds both gaps. The
direction differs: for `qwen2.5:3b`, F was better than A on 15 cohorts, worse on 11, and solved 23
cohorts against 19; for `qwen2.5-coder:3b`, F was better on 7 and worse on 19. The mechanism
worked as intended for `qwen2.5:3b`: attempts failing by unlabelled values fell from 22.5% to
10.0% and by wrong row from 10.0% to 6.2%. For the coder model only wrong rows fell (6.2% to
3.8%). For both models, invalid answers rose, and every invalid F answer is an attempt that used
all 8 tool calls without a valid submit.

**Table 2.** Method F against A. Error shares are over all 80 attempts per model.

| Model | Method | Unlabelled % | Wrong row % | Invalid % | Tool calls | Flagged | Passed after flag |
|---|---|---|---|---|---|---|---|
| qwen2.5:3b | A | 22.5 | 10.0 | 5.0 | | | |
| qwen2.5:3b | F | 10.0 | 6.2 | 13.8 | 4.5 | 8 | 1 |
| qwen2.5-coder:3b | A | 11.2 | 6.2 | 5.0 | | | |
| qwen2.5-coder:3b | F | 13.8 | 3.8 | 18.8 | 5.1 | 28 | 13 |

`check_mapping` was used in 74 (`qwen2.5:3b`) and 79 (coder) of 80 attempts. When it flagged a
problem, the coder model submitted an answer that then passed the check in 13 of 28 attempts, and
`qwen2.5:3b` in 1 of 8. `qwen2.5:3b` used the native tool interface in every call; the coder model
never did, and all of its calls went through the recovery step.

## 6 Error analysis

I assign each failed attempt (accuracy below 95%) one main error type in a fixed priority order.
Over all runs, methods, models, and repeats, including the rule, the counts are: values left
unlabelled 165, wrong row 82, invalid output 78, synonym or code missed 74, other disease labelled
as disease 39, abstained 28, and other or flipped labels 15. Three examples show the main patterns.

**Wrong row.** In GSE174570 (liver cancer), zero shot `qwen2.5:3b` chose `disease state: HCC`,
which has one value for every sample. The experts used `tissue: Tumour (liver)` against
`tissue: Non-tumour adjacent (liver)`. The model matched the disease word instead of looking for
the row that separates samples.

**Code missed.** In GSE109048 (coronary artery disease), D with `qwen2.5:3b` chose the right row
but labelled `diagnosis: STEMI` as control, with the reason `ST-elevation myocardial infarction`.
It expanded the abbreviation and still did not link a heart attack to the trait.

**Agent loop failures.** The two models exhausted the F budget in different ways. `qwen2.5:3b`
often replied in plain text without a tool call (45 times, 22 of them inside the 11 attempts that
ran out) or read the same row again. The coder model often wrote its whole plan in its first
message: `list_rows`, `get_row_values`, `check_mapping` with an empty mapping, and a
`submit_answer` with placeholder keys (`value1`, `value2`, `value3`), all before any tool output.
This used 4 of the 8 calls and the submit was rejected. It occurred in 27 of 80 attempts, which
contain 12 of the model's 15 invalid answers, and it depended strongly on the seed: 1 of 40
cohorts in repeat 0 and 26 of 40 in repeat 1, where those cohorts averaged 40.6% accuracy against
81.4% for the other 14. This one behaviour explains most of F's spread for the coder model. In
GSE131027 (mesothelioma), after the rejected placeholder submit, the model labelled
`tissue: tumor biopsy`, and `check_mapping` warned that the row has one value for all 92 samples.
The model listed the rows again, chose the same row, received the same warning, and ran out of
calls. The check found the problem; the model did not act on it.

A few expert labels involve judgment calls (for example, lesional skin from another disease
labelled control in a lupus study). I flag these cohorts rather than count them silently as model
mistakes.

## 7 Limitations

I used 2 repeats, so the spreads are rough, and F's spread is especially large. B ran only on the
coder model, so for `qwen2.5:3b` the drop from A to C cannot be split between examples and the
reasoning format. F depends on choices I did not tune: the 8 call budget, the tool descriptions,
and, for the coder model, the recovery of tool calls written as text. The benchmark has 40 test
cohorts across 15 traits, covers only disease against control, and only cohorts where one metadata
row explains the labels. I tested only 3B models. My metric is not CSC. GEO text is public, so the
models may have seen some studies in pretraining. Ollama was not fully deterministic with a fixed
seed in one development check. I wrote the rule after seeing the development cohorts.

## 8 Future work

The agent failures suggest two simple loop changes: allow one tool call per message, and refuse
`submit_answer` until the model has read that row's values. Other next steps are running B on
`qwen2.5:3b`, pairing the small extractor with a larger checker to test the weak checker
explanation, running all methods with a larger extractor, and scoring with CSC for a direct
comparison with [1, 2].

## References

[1] H. Liu, S. Chen, Y. Zhang, and H. Wang. GenoTEX: An LLM Agent Benchmark for Automated Gene
Expression Data Analysis. arXiv 2406.15341, 2024. Data released under CC BY 4.0.

[2] H. Liu, Y. Li, and H. Wang. GenoMAS: Guided Multi-Agent Programming for Scientific Discovery
from Genomic Data. arXiv 2507.21035, 2025.

[3] R. Edgar, M. Domrachev, and A. E. Lash. Gene Expression Omnibus: NCBI gene expression and
hybridization array data repository. Nucleic Acids Research, 30(1):207 to 210, 2002.

[4] T. Barrett et al. NCBI GEO: archive for functional genomics data sets, update. Nucleic Acids
Research, 41(D1):D991 to D995, 2013.

[5] Z. Wang et al. Extraction and analysis of signatures from the Gene Expression Omnibus by the
crowd. Nature Communications, 7:12846, 2016.

[6] T. B. Brown et al. Language Models are Few-Shot Learners. arXiv 2005.14165, 2020.

[7] J. Wei et al. Chain-of-Thought Prompting Elicits Reasoning in Large Language Models.
arXiv 2201.11903, 2022.

[8] T. Kojima, S. S. Gu, M. Reid, Y. Matsuo, and Y. Iwasawa. Large Language Models are Zero-Shot
Reasoners. arXiv 2205.11916, 2022.

[9] A. Madaan et al. Self-Refine: Iterative Refinement with Self-Feedback. arXiv 2303.17651, 2023.

[10] J. Huang et al. Large Language Models Cannot Self-Correct Reasoning Yet. arXiv 2310.01798,
2023.

[11] Y. Geifman and R. El-Yaniv. Selective Classification for Deep Neural Networks. NeurIPS, 2017.

[12] S. Yao et al. ReAct: Synergizing Reasoning and Acting in Language Models. arXiv 2210.03629,
2022.

[13] T. Schick et al. Toolformer: Language Models Can Teach Themselves to Use Tools.
arXiv 2302.04761, 2023.

[14] Qwen Team (A. Yang et al.). Qwen2.5 Technical Report. arXiv 2412.15115, 2024.

[15] B. Hui et al. Qwen2.5-Coder Technical Report. arXiv 2409.12186, 2024.

Code, data card, logs, and all results: the project repository (`README.md`, `results/`).
