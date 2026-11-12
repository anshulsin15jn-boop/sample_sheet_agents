# Error examples

Real failed cohorts from this run, grouped by error type. For each: the trait, the row the method chose, and the values of that row with the method's label and the expert label (majority of the expert labels of its samples).

## wrong row (3 failed cohort attempts)

**GSE120490**, trait *Endometrioid Cancer*, method E, qwen2.5:3b, accuracy 68%. Study title: Improving Risk Assessment for Metastatic Disease in Endometrioid Endometrial Cancer Patients Using Molecular and Clinical Features: an NRG Oncology / Gynecologic Oncology Group Study
(Expert judgment call: all samples are endometrioid cancer; experts used metastasis yes/no as the label.)

Chosen row `char_1`; expert row `char_0`.

Values of the chosen row and the method's labels: `grade: No` -> control; `grade: Yes` -> disease

Expert row values: `matastasis: No` -> control; `matastasis: Yes` -> disease

**GSE131282**, trait *Multiple sclerosis*, method B, qwen2.5:3b, accuracy 42%. Study title: Multiple sclerosis cortical normal-appearing grey matter, grey matter lesions, and control grey matter

Chosen row `char_4`; expert row `char_0`.

Values of the chosen row and the method's labels: `ms type: PPMS` -> disease; `ms type: SPMS` -> disease; `ms type: PRMS` -> disease; `pm simple: short` -> missing; `pm simple: long` -> missing; `pm simple: medium` -> missing

Expert row values: `patient id: M#` -> disease; `patient id: C#` -> control

## synonym or code missed (1 failed cohort attempts)

**GSE135589**, trait *Huntingtons Disease*, method E, qwen2.5:3b, accuracy 61%. Study title: 2-year Longitudinal Analyses of Peripheral Blood RNA in Huntington's Disease gene-positive and control subjects

Chosen row `char_4`; expert row `char_4`.

| Value | Method | Expert |
|---|---|---|
| `disease stage: Control` | control (no disease) | control |
| `disease stage: preHD A` | disease (early pre-Huntington's) | disease |
| `disease stage: preHD B` | disease (late pre-Huntington's) | disease |
| `disease stage: zHD stage1` | control (very early HD onset) | disease **x** |
| `disease stage: zHD stage2` | control (very early HD onset) | disease **x** |

## values left unlabelled (8 failed cohort attempts)

**GSE123088**, trait *Eczema*, method C, qwen2.5:3b, accuracy 81%. Study title: A validated single-cell-based strategy to identify diagnostic and therapeutic targets in complex diseases

Chosen row `char_1`; expert row `char_1`.

| Value | Method | Expert |
|---|---|---|
| `primary diagnosis: ASTHMA` | control (primary diagnosis is asthma, not eczema) | control |
| `primary diagnosis: ATHEROSCLEROSIS` | control (primary diagnosis is atherosclerosis, not eczema) | control |
| `primary diagnosis: BREAST_CANCER` | control (primary diagnosis is breast cancer, not eczema) | control |
| `primary diagnosis: CHRONIC_LYMPHOCYTIC_LEUKEMIA` | control (primary diagnosis is chronic lymphocytic leukemia, not eczema) | control |
| `primary diagnosis: CROHN_DISEASE` | control (primary diagnosis is crohn disease, not eczema) | control |
| `primary diagnosis: ATOPIC_ECZEMA` | disease (primary diagnosis is atopic eczema) | disease |
| `primary diagnosis: HEALTHY_CONTROL` | control (primary diagnosis is healthy control, not eczema) | control |
| `primary diagnosis: INFLUENZA` | control (primary diagnosis is influenza, not eczema) | control |
| `primary diagnosis: OBESITY` | control (primary diagnosis is obesity, not eczema) | control |
| `primary diagnosis: PSORIASIS` | control (primary diagnosis is psoriasis, not eczema) | control |

**GSE212866**, trait *COVID-19*, method A, qwen2.5:3b, accuracy 63%. Study title: Dynamics of gene expression profiling by microarrays and identification of high-risk patients for severe COVID-19

Chosen row `char_0`; expert row `char_0`.

| Value | Method | Expert |
|---|---|---|
| `disease state: Control` | missing | control **x** |
| `disease state: Covid19` | disease | disease |
| `disease state: Covid19_SDRA` | disease | disease |

## invalid output (3 failed cohort attempts)

## abstained (2 failed cohort attempts)

