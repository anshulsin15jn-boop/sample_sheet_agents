# Error examples

Real failed cohorts from this run, grouped by error type. For each: the trait, the row the method chose, and the values of that row with the method's label and the expert label (majority of the expert labels of its samples).

## wrong row (1 failed cohort attempts)

**GSE131282**, trait *Multiple sclerosis*, method F, qwen2.5-coder:3b, accuracy 64%. Study title: Multiple sclerosis cortical normal-appearing grey matter, grey matter lesions, and control grey matter

Chosen row `char_4`; expert row `char_0`.

Values of the chosen row and the method's labels: `ms type: PPMS` -> disease; `ms type: SPMS` -> disease; `ms type: PRMS` -> unknown; `pm simple: short` -> control; `pm simple: long` -> control; `pm simple: medium` -> control

Expert row values: `patient id: M#` -> disease; `patient id: C#` -> control

## synonym or code missed (3 failed cohort attempts)

**GSE123088**, trait *Eczema*, method F, qwen2.5-coder:3b, accuracy 94%. Study title: A validated single-cell-based strategy to identify diagnostic and therapeutic targets in complex diseases

Chosen row `char_2`; expert row `char_1`.

Values of the chosen row and the method's labels: `Sex: Male` -> control; `diagnosis2: ATOPIC_ECZEMA` -> disease; `Sex: Female` -> control; `diagnosis2: ATHEROSCLEROSIS` -> control; `diagnosis2: ASTHMA_OBESITY` -> unknown; `diagnosis2: ASTHMA` -> disease; `diagnosis2: ASTMHA_SEASONAL_ALLERGIC_RHINITIS` -> control; `diagnosis2: OBESITY` -> control

Expert row values: `primary diagnosis: ASTHMA` -> control; `primary diagnosis: ATHEROSCLEROSIS` -> control; `primary diagnosis: BREAST_CANCER` -> control; `primary diagnosis: CHRONIC_LYMPHOCYTIC_LEUKEMIA` -> control; `primary diagnosis: CROHN_DISEASE` -> control; `primary diagnosis: ATOPIC_ECZEMA` -> disease; `primary diagnosis: HEALTHY_CONTROL` -> control; `primary diagnosis: INFLUENZA` -> control

**GSE135589**, trait *Huntingtons Disease*, method F, qwen2.5-coder:3b, accuracy 25%. Study title: 2-year Longitudinal Analyses of Peripheral Blood RNA in Huntington's Disease gene-positive and control subjects

Chosen row `char_4`; expert row `char_4`.

| Value | Method | Expert |
|---|---|---|
| `disease stage: Control` | control | control |
| `disease stage: preHD A` | unknown | disease **x** |
| `disease stage: preHD B` | unknown | disease **x** |
| `disease stage: zHD stage1` | unknown | disease **x** |
| `disease stage: zHD stage2` | unknown | disease **x** |

## values left unlabelled (1 failed cohort attempts)

