# Data card: sample sheet trait extraction benchmark

Built by `python -m scripts.build_benchmark` (fixed seed 7). Inputs are the sample metadata rows from GEO series matrix headers (NCBI GEO). Labels are the expert trait labels from the GenoTEX release (Liu et al., arXiv 2406.15341, CC BY 4.0), file `output/preprocess/<Trait>/clinical_data/<GSE>.csv`.

* Cohorts: **50** (10 development, 40 test)
* Traits: **15**
* Labelled samples: **9355** (4311 disease, 5044 control)
* Labelled samples per cohort: median 88, smallest 30, largest 3984
* Metadata rows per cohort (title, source, characteristics): median 6, range 3 to 25
* Cohorts where more than one row can explain the labels: 43
* Samples in the GEO files that the experts left unlabelled (not graded): 136

## What counts as disease and control

The label is whatever the GenoTEX experts decided: 1 means the sample has the trait, 0 means it does not. A 0 is often a healthy control, but sometimes it is a sample with a different disease (for example, in GSE123086 every non asthma patient is a 0 for Asthma), a non lesional sample, or a different tumour subtype. This is a real part of why the task is hard: "control" is defined by the study design, not by a word in the metadata.

## Cohorts per trait

| Trait | Cohorts | Dev | Test | Labelled samples | Disease share |
|---|---|---|---|---|---|
| Asthma | 4 | 1 | 3 | 486 | 39% |
| Atrial Fibrillation | 3 | 1 | 2 | 208 | 27% |
| Bipolar disorder | 3 | 0 | 3 | 227 | 54% |
| COVID-19 | 4 | 1 | 3 | 587 | 73% |
| Coronary artery disease | 3 | 0 | 3 | 139 | 58% |
| Eczema | 3 | 1 | 2 | 298 | 18% |
| Endometrioid Cancer | 4 | 1 | 3 | 301 | 26% |
| Huntingtons Disease | 4 | 1 | 3 | 595 | 58% |
| Intellectual Disability | 4 | 0 | 4 | 197 | 53% |
| Liver Cancer | 3 | 0 | 3 | 4180 | 49% |
| Lupus (Systemic Lupus Erythematosus) | 3 | 2 | 1 | 258 | 77% |
| Mesothelioma | 3 | 1 | 2 | 937 | 5% |
| Multiple sclerosis | 3 | 1 | 2 | 340 | 72% |
| Pancreatic Cancer | 3 | 0 | 3 | 308 | 56% |
| Stroke | 3 | 0 | 3 | 294 | 46% |

## How many cohorts a trivial keyword rule already solves

* dev: 3 of 10 cohorts solved (accuracy at least 95%), mean accuracy 0.513
* test: 13 of 40 cohorts solved (accuracy at least 95%), mean accuracy 0.558

The rule is baseline R (`src/rules.py`). So roughly a third of cohorts are easy; the rest need reading and judgment.

## All cohorts

| Cohort | Split | Trait | Disease | Control | Expert row | Rows that explain labels | Example values of expert row | Rule solves |
|---|---|---|---|---|---|---|---|---|
| GSE270312 | dev | Asthma | 51 | 39 | char_3 | char_3 | asthma status: No; asthma status: Yes | yes |
| GSE143924 | dev | Atrial Fibrillation | 15 | 15 | char_1 | source, char_1 | patient diagnosis: sinus rhythm after surgery; patient diagnosis: postoperative atrial fib | no |
| GSE212866 | dev | COVID-19 | 86 | 51 | char_0 | title, source, char_0, char_1 | disease state: Control; disease state: Covid19; disease state: Covid19_SDRA | yes |
| GSE123088 | dev | Eczema | 7 | 197 | char_1 | title, char_1, char_2, char_3, char_4 | primary diagnosis: ASTHMA; primary diagnosis: ATHEROSCLEROSIS; primary diagnosis: BREAST_C | no |
| GSE120490 | dev | Endometrioid Cancer | 45 | 100 | char_0 | char_0 | matastasis: No; matastasis: Yes | no |
| GSE135589 | dev | Huntingtons Disease | 134 | 44 | char_4 | title, char_4, char_5 | disease stage: Control; disease stage: preHD A; disease stage: preHD B | no |
| GSE112943 | dev | Lupus (Systemic Lupus Erythematosus) | 30 | 17 | char_0 | title, char_0 | tissue: CCLE; tissue: SCLE; tissue: Skin Control | no |
| GSE200306 | dev | Lupus (Systemic Lupus Erythematosus) | 162 | 19 | char_0 | title, source, char_0, char_1, char_2, char_3, char_4, char_5 | ln class: Class IV; ln class: Mixed (III/IV+V); ln class: Class III | yes |
| GSE68950 | dev | Mesothelioma | 6 | 791 | char_1 | title, char_0, char_1, char_2, char_3, char_6, char_7, char_8 | disease state: L# Acute Lymphoblastic Leukemia; disease state: NS Acute Lymphoblastic Leuk | no |
| GSE131282 | dev | Multiple sclerosis | 142 | 42 | char_0 | title, char_0, char_2, char_5, char_6, char_10 | patient id: M#; patient id: C# | no |
| GSE123086 | test | Asthma | 11 | 155 | char_1 | title, char_1 | primary diagnosis: ASTHMA; primary diagnosis: ATHEROSCLEROSIS; primary diagnosis: BREAST_C | no |
| GSE182798 | test | Asthma | 95 | 87 | char_0 | title, char_0 | diagnosis: adult-onset asthma; diagnosis: IEI; diagnosis: healthy | no |
| GSE185658 | test | Asthma | 34 | 14 | char_1 | title, char_1, char_2 | group: AsthmaHDM; group: AsthmaHDMNeg; group: Healthy | no |
| GSE115574 | test | Atrial Fibrillation | 28 | 31 | char_0 | title, source, char_0 | disease state: atrial fibrillation patient with severe mitral regurgitation; disease state | no |
| GSE235307 | test | Atrial Fibrillation | 13 | 106 | char_5 | char_5 | cardiac rhythm after 1 year follow-up: Sinus rhythm; cardiac rhythm after 1 year follow-up | no |
| GSE46416 | test | Bipolar disorder | 22 | 10 | char_1 | title, source, char_1, char_2, char_3 | disease status: bipolar disorder (BD); disease status: control | yes |
| GSE46449 | test | Bipolar disorder | 49 | 39 | char_1 | title, source, char_1 | genotype: bipolar patient; genotype: control subject | yes |
| GSE53987 | test | Bipolar disorder | 52 | 55 | char_7 | title, source, char_7 | disease state: bipolar disorder; disease state: control; disease state: major depressive d | yes |
| GSE213313 | test | COVID-19 | 83 | 11 | char_1 | title, char_0, char_1, char_2, char_3 | disease state: COVID-19; disease state: Healthy | yes |
| GSE227080 | test | COVID-19 | 60 | 59 | char_2 | char_2 | severity: MILD; severity: MOD_SEV; severity: NEG | no |
| GSE243348 | test | COVID-19 | 200 | 37 | char_0 | title, source, char_0, char_1, char_5, char_6, char_7 | disease status: COVID-19+; disease status: Healthy uninfected | yes |
| GSE109048 | test | Coronary artery disease | 38 | 19 | char_1 | title, char_1 | diagnosis: sCAD; diagnosis: healthy; diagnosis: STEMI | no |
| GSE120774 | test | Coronary artery disease | 17 | 19 | char_2 | title, source, char_2 | disease: None; disease: coronary disease | yes |
| GSE64554 | test | Coronary artery disease | 26 | 20 | char_2 | title, char_0, char_2 | disease state: control; disease state: coronary artery disease | yes |
| GSE32924 | test | Eczema | 24 | 8 | char_2 | title, source, char_2 | condition: ANL; condition: AL; condition: Normal | no |
| GSE57225 | test | Eczema | 23 | 39 | char_1 | source, char_1 | disease state: psoriasis; disease state: eczema; disease state: control (non-involved) | no |
| GSE65986 | test | Endometrioid Cancer | 14 | 40 | char_0 | title, char_0 | histology: Clear; histology: Endometrioid; histology: Serous | no |
| GSE73551 | test | Endometrioid Cancer | 9 | 41 | char_0 | title, char_0 | cell type: MUCINOUS; cell type: CLEAR CELL; cell type: SEROUS LOW-GRADE | no |
| GSE73637 | test | Endometrioid Cancer | 9 | 43 | char_3 | source, char_1, char_3 | histopathology: Serous; histopathology: Endometrioid; histopathology: Poorly differentiate | no |
| GSE26927 | test | Huntingtons Disease | 20 | 98 | char_0 | title, source, char_0 | disease: Alzheimer's disease; disease: Amyotrophic lateral sclerosis; disease: Huntington' | no |
| GSE34201 | test | Huntingtons Disease | 42 | 30 | char_1 | title, source, char_0, char_1 | hd genotype: wild type; hd genotype: HD | no |
| GSE34721 | test | Huntingtons Disease | 150 | 77 | char_1 | char_1 | htt cag repeat length (longer allele): 15; htt cag repeat length (longer allele): 17; htt  | no |
| GSE100680 | test | Intellectual Disability | 15 | 18 | char_3 | char_1, char_3 | description: DS Clone C11 Day 45; description: Euploid Clone C86 Day 45; description: DS C | no |
| GSE273850 | test | Intellectual Disability | 23 | 28 | char_0 | title, char_0 | genotype: T21; genotype: Euploid | no |
| GSE285666 | test | Intellectual Disability | 34 | 17 | char_0 | title, source, char_0 | disease state: unaffected parental control; disease state: Williams syndrome patient | no |
| GSE89594 | test | Intellectual Disability | 32 | 30 | char_0 | title, source, char_0 | diagnosis: control; diagnosis: autism spectrum disorder (ASD); diagnosis: Williams Syndrom | no |
| GSE174570 | test | Liver Cancer | 57 | 57 | char_1 | title, source, char_1 | tissue: Tumour (liver); tissue: Non-tumour adjacent (liver) | yes |
| GSE178201 | test | Liver Cancer | 1972 | 2012 | char_0 | title, source, char_0 | tissue: HEPG2; tissue: MCF10A.TP53.M; tissue: MCF10A.WT.HP | no |
| GSE228782 | test | Liver Cancer | 19 | 63 | char_2 | char_1, char_2 | disease: CCC; disease: CRC Met; disease: HCC | no |
| GSE148810 | test | Lupus (Systemic Lupus Erythematosus) | 7 | 23 | char_1 | char_1 | disease: JM Lesional skin; disease: JM Non-lesional skin; disease: cSLE skin lesion | no |
| GSE117668 | test | Mesothelioma | 36 | 12 | char_1 | title, source, char_0, char_1 | diagnosis: healthy; diagnosis: malignant pleural mesothelioma | yes |
| GSE131027 | test | Mesothelioma | 7 | 85 | char_1 | title, char_1 | cancer: Breast cancer; cancer: Colorectal cancer; cancer: Bile duct cancer | no |
| GSE131281 | test | Multiple sclerosis | 64 | 42 | char_5 | title, char_0, char_2, char_5, char_6, char_10 | ms type: PPMS; ms type: SPMS; ms type: ? | no |
| GSE135511 | test | Multiple sclerosis | 40 | 10 | char_0 | title, source, char_0, char_1, char_2 | disease state: Healthy Control; disease state: Multiple Sclerosis | yes |
| GSE125158 | test | Pancreatic Cancer | 17 | 13 | char_0 | char_0 | diagnosis: healthy; diagnosis: pancreatic cancer | yes |
| GSE183795 | test | Pancreatic Cancer | 139 | 105 | char_0 | source, char_0 | tissue: Tumor; tissue: adjacent non-tumor; tissue: Normal pancreas | yes |
| GSE236951 | test | Pancreatic Cancer | 16 | 18 | char_0 | title, char_0 | disease: Pancreatic ductal adenocarcinoma; disease: Colon adenocarcinoma; disease: Benign  | no |
| GSE161533 | test | Stroke | 9 | 75 | char_6 | char_2, char_6 | disease history: None; disease history: Hypertension; disease history: Breast cancer | no |
| GSE273225 | test | Stroke | 58 | 60 | char_7 | char_7, char_8, char_9 | donor cause of death: hypoxic-ischemic encefalopathy; donor cause of death: intracranial b | no |
| GSE58294 | test | Stroke | 69 | 23 | char_0 | title, char_0, char_1, char_2 | group: Control; group: Cardioembolic Stroke | yes |

## Notes and caveats

* Rows that explain the labels: a row counts if the best possible value to label mapping on it reaches at least 95% agreement with the expert labels and it has at most half as many distinct (displayed) values as labelled samples. The expert's own row is always included.
* Long rows: a row with more than 30 distinct values is shown with digit runs replaced by #, unless it is purely numeric (then up to 60 raw numbers are shown).
* Labels are inherited from GenoTEX and may contain the occasional expert judgment call that others would make differently.
* GEO text is public, so the models may have seen some of it during training.
