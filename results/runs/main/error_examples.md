# Error examples

Real failed cohorts from this run, grouped by error type. For each: the trait, the row the method chose, and the values of that row with the method's label and the expert label (majority of the expert labels of its samples).

## wrong row (62 failed cohort attempts)

**GSE125158**, trait *Pancreatic Cancer*, method E, qwen2.5:3b, accuracy 43%. Study title: Development of novel diagnostic system for pancreas cancer including early stages measuring mRNA of whole blood cells

Chosen row `char_1`; expert row `char_0`.

Values of the chosen row and the method's labels: `tissue: whole blood` -> control

Expert row values: `diagnosis: healthy` -> control; `diagnosis: pancreatic cancer` -> disease

**GSE174570**, trait *Liver Cancer*, method A, qwen2.5:3b, accuracy 50%. Study title: Cabozantinib enhances anti-PD1 efficacy and elicits a neutrophil-based immune response in murine models: implications for human HCC

Chosen row `char_0`; expert row `char_1`.

Values of the chosen row and the method's labels: `disease state: HCC` -> disease

Expert row values: `tissue: Tumour (liver)` -> disease; `tissue: Non-tumour adjacent (liver)` -> control

## other disease as disease (28 failed cohort attempts)

**GSE148810**, trait *Lupus (Systemic Lupus Erythematosus)*, method A, qwen2.5:3b, accuracy 50%. Study title: Gene expression of skin biopsie samples from juvenile myositis (JM) and childhood-onset lupus (cSLE).
(Expert judgment call: lesional skin of a different disease (juvenile dermatomyositis) labelled control.)

Chosen row `char_1`; expert row `char_1`.

| Value | Method | Expert |
|---|---|---|
| `disease: JM Lesional skin` | disease | control **x** |
| `disease: JM Non-lesional skin` | disease | control **x** |
| `disease: cSLE skin lesion` | disease | disease |
| `disease: Normal skin` | control | control |

**GSE182798**, trait *Asthma*, method A, qwen2.5:3b, accuracy 84%. Study title: Transcriptomic profiling of adult-onset asthma related to damp and moldy buildings and idiopathic environmental intolerance

Chosen row `char_0`; expert row `char_0`.

| Value | Method | Expert |
|---|---|---|
| `diagnosis: adult-onset asthma` | disease | disease |
| `diagnosis: IEI` | disease | control **x** |
| `diagnosis: healthy` | control | control |

## synonym or code missed (44 failed cohort attempts)

**GSE109048**, trait *Coronary artery disease*, method D, qwen2.5:3b, accuracy 67%. Study title: Platelet gene expression profiling of acute myocardial infarction

Chosen row `char_1`; expert row `char_1`.

| Value | Method | Expert |
|---|---|---|
| `diagnosis: sCAD` | disease (acute myocardial infarction) | disease |
| `diagnosis: healthy` | control (no disease) | control |
| `diagnosis: STEMI` | control (ST-elevation myocardial infarction) | disease **x** |

**GSE185658**, trait *Asthma*, method A, qwen2.5:3b, accuracy 79%. Study title: Rhinovirus-induced epithelial RIG-I inflammasome suppresses antiviral immunity and promotes inflammation in asthma and COVID-19

Chosen row `char_1`; expert row `char_1`.

| Value | Method | Expert |
|---|---|---|
| `group: AsthmaHDM` | disease | disease |
| `group: AsthmaHDMNeg` | control | disease **x** |
| `group: Healthy` | control | control |

## values left unlabelled (120 failed cohort attempts)

**GSE100680**, trait *Intellectual Disability*, method A, qwen2.5:3b, accuracy 55%. Study title: APP levels mediate beta-amyloid but not tau-related aspects of Alzheimer’s disease in a Down syndrome model of cortical neurogenesis.

Chosen row `char_3`; expert row `char_3`.

| Value | Method | Expert |
|---|---|---|
| `description: DS Clone C11 Day 45` | disease | disease |
| `description: Euploid Clone C86 Day 45` | missing | control **x** |
| `description: DS Clone C11 Day 65` | missing | disease **x** |
| `description: Euploid Clone C86 Day 65` | missing | control **x** |
| `description: DS Clone C18 Day 45` | disease | disease |
| `description: Euploid Clone C87 Day 45` | missing | control **x** |
| `description: DS Clone C18 Day 65` | disease | disease |
| `description: Euploid Clone C87 Day 65` | missing | control **x** |
| `description: APP copy number-corrected DS Clone A3 Day 45` | disease | disease |
| `description: Euploid Clone C79 Day 45` | control | control |

**GSE115574**, trait *Atrial Fibrillation*, method C, qwen2.5:3b, accuracy 48%. Study title: Gene expression data from human left and right atrial tissues in patients with degenerative MR in SR and AFib.

Chosen row `char_0`; expert row `char_0`.

| Value | Method | Expert |
|---|---|---|
| `disease state: atrial fibrillation patient with severe mitral regurgitation` | disease (directly states patient has atrial fibrillation) | disease |
| `disease state: sinus rhythm patient with severe mitral regurgitation` | missing | control **x** |

## flipped labels (3 failed cohort attempts)

**GSE227080**, trait *COVID-19*, method A, qwen2.5-coder:3b, accuracy 0%. Study title: Early differentially expressed immunological genes   in mild and severe COVID-19

Chosen row `char_2`; expert row `char_2`.

| Value | Method | Expert |
|---|---|---|
| `severity: MILD` | control | disease **x** |
| `severity: MOD_SEV` | control | disease **x** |
| `severity: NEG` | disease | control **x** |

**GSE228782**, trait *Liver Cancer*, method E, qwen2.5-coder:3b, accuracy 29%. Study title: Inter-patient heterogeneity in the hepatic ischemia-reperfusion injury transcriptome: implications for research and diagnostics [MUG data]

Chosen row `char_2`; expert row `char_2`.

| Value | Method | Expert |
|---|---|---|
| `disease: CCC` | control (chronic hepatitis C) | disease **x** |
| `disease: CRC Met` | disease (colorectal cancer) | control **x** |
| `disease: HCC` | disease (hepatocellular carcinoma) | disease |
| `disease: other` | control (other liver diseases) | control |

## invalid output (51 failed cohort attempts)

**GSE131281**, trait *Multiple sclerosis*, method A, qwen2.5:3b, accuracy 0%. Study title: Multiple sclerosis cortical normal-appearing grey matter and control grey matter

Reason: not valid JSON. Start of the output: `{"row": "char_6", "mapping": {"disease duration: ?": "unknown", "disease duration: 0": "unknown", "disease duration: 1": "unknown", "disease duration: 10": "unknown", "disease duration: 11": "unknown"`

**GSE161533**, trait *Stroke*, method C, qwen2.5:3b, accuracy 0%. Study title: Expression data from esophageal squamous cell carcinoma patients
(Expert judgment call: stroke taken from a disease history row in a cancer tissue study.)

Reason: no mapping key matches a value of the chosen row. Start of the output: `{"row": "char_1", "row_reason": "tumor tissue from patient # indicates presence of tumor, which is not related to stroke", "mapping": {"tumor tissue from patient #": {"reason": "tumor tissue, not stro`

## abstained (25 failed cohort attempts)

**GSE123086**, trait *Asthma*, method D, qwen2.5:3b, accuracy 7%. Study title: A validated single-cell-based strategy to identify diagnostic and therapeutic targets in complex diseases [study of 13 diseases]

The method answered cannot determine or unsure for most samples.

**GSE131027**, trait *Mesothelioma*, method D, qwen2.5:3b, accuracy 8%. Study title: High frequency of pathogenic germline variants in genes associated with homologous recombination repair in patients with advanced solid cancers

The method answered cannot determine or unsure for most samples.

## other (9 failed cohort attempts)

**GSE178201**, trait *Liver Cancer*, method C, qwen2.5-coder:3b, accuracy 50%. Study title: The Carcinogenome Project
(Expert judgment call: cell lines: HepG2 (liver cancer) vs MCF10A (breast) as control.)

Chosen row `char_0`; expert row `char_0`.

| Value | Method | Expert |
|---|---|---|
| `tissue: HEPG2` | disease (liver cancer cell line) | disease |
| `tissue: MCF10A.TP53.M` | disease (liver cancer cell line) | control **x** |
| `tissue: MCF10A.WT.HP` | disease (liver cancer cell line) | control **x** |

**GSE117668**, trait *Mesothelioma*, method E, qwen2.5-coder:3b, accuracy 75%. Study title: Expression data from in vitro healthy cells and malignant pleural mesothelioma cell lines infected by oncolytic attenuated measles virus or treated by exogenous type I interferon

Chosen row `char_1`; expert row `char_1`.

| Value | Method | Expert |
|---|---|---|
| `diagnosis: healthy` | disease (normal cells) | control **x** |
| `diagnosis: malignant pleural mesothelioma` | disease (mesothelioma) | disease |

