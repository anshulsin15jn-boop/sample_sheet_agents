# Error examples

Real failed cohorts from this run, grouped by error type. For each: the trait, the row the method chose, and the values of that row with the method's label and the expert label (majority of the expert labels of its samples).

## wrong row (8 failed cohort attempts)

**GSE273225**, trait *Stroke*, method F, qwen2.5-coder:3b, accuracy 0%. Study title: The effect of rewarming ischemia on tissue transcriptome signatures: a clinical observational study in lung transplantation
(Expert judgment call: intracranial bleeding counted as stroke, head trauma as control.)

Chosen row `char_0`; expert row `char_7`.

Values of the chosen row and the method's labels: `tissue: left lung` -> unknown; `tissue: right lung` -> unknown

Expert row values: `donor cause of death: hypoxic-ischemic encefalopathy` -> control; `donor cause of death: intracranial bleeding` -> disease; `donor cause of death: head trauma` -> control; `donor cause of death: ischemic stroke` -> disease

**GSE100680**, trait *Intellectual Disability*, method F, qwen2.5-coder:3b, accuracy 0%. Study title: APP levels mediate beta-amyloid but not tau-related aspects of Alzheimer’s disease in a Down syndrome model of cortical neurogenesis.

Chosen row `char_0`; expert row `char_3`.

Values of the chosen row and the method's labels: `cell type: Neuronal differentiation culture` -> unknown

Expert row values: `description: DS Clone C11 Day 45` -> disease; `description: Euploid Clone C86 Day 45` -> control; `description: DS Clone C11 Day 65` -> disease; `description: Euploid Clone C86 Day 65` -> control; `description: DS Clone C18 Day 45` -> disease; `description: Euploid Clone C87 Day 45` -> control; `description: DS Clone C18 Day 65` -> disease; `description: Euploid Clone C87 Day 65` -> control

## other disease as disease (6 failed cohort attempts)

**GSE148810**, trait *Lupus (Systemic Lupus Erythematosus)*, method F, qwen2.5-coder:3b, accuracy 70%. Study title: Gene expression of skin biopsie samples from juvenile myositis (JM) and childhood-onset lupus (cSLE).
(Expert judgment call: lesional skin of a different disease (juvenile dermatomyositis) labelled control.)

Chosen row `char_1`; expert row `char_1`.

| Value | Method | Expert |
|---|---|---|
| `disease: JM Lesional skin` | disease | control **x** |
| `disease: JM Non-lesional skin` | control | control |
| `disease: cSLE skin lesion` | disease | disease |
| `disease: Normal skin` | control | control |

**GSE236951**, trait *Pancreatic Cancer*, method F, qwen2.5-coder:3b, accuracy 71%. Study title: Gene based immune profiling of vermiform appendix GALT of adult patients with pancreatic cancer or colon diseases.

Chosen row `char_0`; expert row `char_0`.

| Value | Method | Expert |
|---|---|---|
| `disease: Pancreatic ductal adenocarcinoma` | disease | disease |
| `disease: Colon adenocarcinoma` | disease | control **x** |
| `disease: Benign colon disease` | control | control |

## synonym or code missed (15 failed cohort attempts)

**GSE109048**, trait *Coronary artery disease*, method F, qwen2.5-coder:3b, accuracy 67%. Study title: Platelet gene expression profiling of acute myocardial infarction

Chosen row `char_1`; expert row `char_1`.

| Value | Method | Expert |
|---|---|---|
| `diagnosis: sCAD` | disease | disease |
| `diagnosis: healthy` | control | control |
| `diagnosis: STEMI` | unknown | disease **x** |

**GSE227080**, trait *COVID-19*, method F, qwen2.5-coder:3b, accuracy 50%. Study title: Early differentially expressed immunological genes   in mild and severe COVID-19

Chosen row `char_2`; expert row `char_2`.

| Value | Method | Expert |
|---|---|---|
| `severity: MILD` | control | disease **x** |
| `severity: MOD_SEV` | control | disease **x** |
| `severity: NEG` | control | control |

## values left unlabelled (19 failed cohort attempts)

**GSE131281**, trait *Multiple sclerosis*, method F, qwen2.5-coder:3b, accuracy 60%. Study title: Multiple sclerosis cortical normal-appearing grey matter and control grey matter

Chosen row `char_5`; expert row `char_5`.

| Value | Method | Expert |
|---|---|---|
| `ms type: PPMS` | disease | disease |
| `ms type: SPMS` | disease | disease |
| `ms type: ?` | unknown | control **x** |
| `ms type: PRMS` | disease | disease |

**GSE161533**, trait *Stroke*, method F, qwen2.5-coder:3b, accuracy 75%. Study title: Expression data from esophageal squamous cell carcinoma patients
(Expert judgment call: stroke taken from a disease history row in a cancer tissue study.)

Chosen row `char_6`; expert row `char_6`.

| Value | Method | Expert |
|---|---|---|
| `disease history: None` | control | control |
| `disease history: Hypertension` | unknown | control **x** |
| `disease history: Breast cancer` | unknown | control **x** |
| `disease history: Cerebral  infarction` | disease | disease |
| `disease history: Lymphoma` | unknown | control **x** |
| `disease history: Hypertension, coronary heart disease, cerebral  infarction` | unknown | disease **x** |

## invalid output (26 failed cohort attempts)

**GSE131027**, trait *Mesothelioma*, method F, qwen2.5-coder:3b, accuracy 0%. Study title: High frequency of pathogenic germline variants in genes associated with homologous recombination repair in patients with advanced solid cancers

Reason: no valid submit_answer within 8 tool calls. Start of the output: `{"content": "{\"name\": \"list_rows\", \"arguments\": {}}\n{\"name\": \"get_row_values\", \"arguments\": {\"row_id\": \"char_0\"}}\n{\"name\": \"check_mapping\", \"arguments\": {\"row_id\": \"char_0\"`

**GSE32924**, trait *Eczema*, method F, qwen2.5-coder:3b, accuracy 0%. Study title: Nonlesional atopic dermatitis skin is characterized by broad terminal differentiation defects and variable immune abnormalities
(Expert judgment call: non lesional skin (ANL) of eczema patients labelled disease.)

Reason: no valid submit_answer within 8 tool calls. Start of the output: `{"content": "```json\n{\"name\": \"list_rows\", \"arguments\": {}}\n```", "tool_calls": [], "error": ""}`

## other (1 failed cohort attempts)

**GSE178201**, trait *Liver Cancer*, method F, qwen2.5-coder:3b, accuracy 50%. Study title: The Carcinogenome Project
(Expert judgment call: cell lines: HepG2 (liver cancer) vs MCF10A (breast) as control.)

Chosen row `char_0`; expert row `char_0`.

| Value | Method | Expert |
|---|---|---|
| `tissue: HEPG2` | disease | disease |
| `tissue: MCF10A.TP53.M` | disease | control **x** |
| `tissue: MCF10A.WT.HP` | disease | control **x** |

