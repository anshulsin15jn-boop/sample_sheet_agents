# Error examples

Real failed cohorts from this run, grouped by error type. For each: the trait, the row the method chose, and the values of that row with the method's label and the expert label (majority of the expert labels of its samples).

## wrong row (6 failed cohort attempts)

**GSE161533**, trait *Stroke*, method B, qwen2.5-coder:3b, accuracy 11%. Study title: Expression data from esophageal squamous cell carcinoma patients
(Expert judgment call: stroke taken from a disease history row in a cancer tissue study.)

Chosen row `char_1`; expert row `char_6`.

Values of the chosen row and the method's labels: `Stage: IB` -> disease; `Stage: I` -> disease; `Stage: IA` -> disease; `Stage: IIA` -> disease; `Stage: IIB` -> disease; `Stage: II` -> disease; `Stage: IIIA` -> disease; `Stage: IIIB` -> disease

Expert row values: `disease history: None` -> control; `disease history: Hypertension` -> control; `disease history: Breast cancer` -> control; `disease history: Cerebral  infarction` -> disease; `disease history: Lymphoma` -> control; `disease history: Hypertension, coronary heart disease, cerebral  infarction` -> disease

**GSE174570**, trait *Liver Cancer*, method B, qwen2.5-coder:3b, accuracy 50%. Study title: Cabozantinib enhances anti-PD1 efficacy and elicits a neutrophil-based immune response in murine models: implications for human HCC

Chosen row `char_0`; expert row `char_1`.

Values of the chosen row and the method's labels: `disease state: HCC` -> disease

Expert row values: `tissue: Tumour (liver)` -> disease; `tissue: Non-tumour adjacent (liver)` -> control

## other disease as disease (5 failed cohort attempts)

**GSE100680**, trait *Intellectual Disability*, method B, qwen2.5-coder:3b, accuracy 46%. Study title: APP levels mediate beta-amyloid but not tau-related aspects of Alzheimer’s disease in a Down syndrome model of cortical neurogenesis.

Chosen row `char_3`; expert row `char_3`.

| Value | Method | Expert |
|---|---|---|
| `description: DS Clone C11 Day 45` | disease | disease |
| `description: Euploid Clone C86 Day 45` | disease | control **x** |
| `description: DS Clone C11 Day 65` | disease | disease |
| `description: Euploid Clone C86 Day 65` | disease | control **x** |
| `description: DS Clone C18 Day 45` | disease | disease |
| `description: Euploid Clone C87 Day 45` | disease | control **x** |
| `description: DS Clone C18 Day 65` | disease | disease |
| `description: Euploid Clone C87 Day 65` | disease | control **x** |
| `description: APP copy number-corrected DS Clone A3 Day 45` | disease | disease |
| `description: Euploid Clone C79 Day 45` | disease | control **x** |

**GSE148810**, trait *Lupus (Systemic Lupus Erythematosus)*, method B, qwen2.5-coder:3b, accuracy 70%. Study title: Gene expression of skin biopsie samples from juvenile myositis (JM) and childhood-onset lupus (cSLE).
(Expert judgment call: lesional skin of a different disease (juvenile dermatomyositis) labelled control.)

Chosen row `char_1`; expert row `char_1`.

| Value | Method | Expert |
|---|---|---|
| `disease: JM Lesional skin` | disease | control **x** |
| `disease: JM Non-lesional skin` | control | control |
| `disease: cSLE skin lesion` | disease | disease |
| `disease: Normal skin` | control | control |

## synonym or code missed (7 failed cohort attempts)

**GSE109048**, trait *Coronary artery disease*, method B, qwen2.5-coder:3b, accuracy 67%. Study title: Platelet gene expression profiling of acute myocardial infarction

Chosen row `char_1`; expert row `char_1`.

| Value | Method | Expert |
|---|---|---|
| `diagnosis: sCAD` | disease | disease |
| `diagnosis: healthy` | control | control |
| `diagnosis: STEMI` | control | disease **x** |

**GSE185658**, trait *Asthma*, method B, qwen2.5-coder:3b, accuracy 79%. Study title: Rhinovirus-induced epithelial RIG-I inflammasome suppresses antiviral immunity and promotes inflammation in asthma and COVID-19

Chosen row `char_1`; expert row `char_1`.

| Value | Method | Expert |
|---|---|---|
| `group: AsthmaHDM` | disease | disease |
| `group: AsthmaHDMNeg` | control | disease **x** |
| `group: Healthy` | control | control |

## values left unlabelled (16 failed cohort attempts)

**GSE131027**, trait *Mesothelioma*, method B, qwen2.5-coder:3b, accuracy 8%. Study title: High frequency of pathogenic germline variants in genes associated with homologous recombination repair in patients with advanced solid cancers

Chosen row `char_1`; expert row `char_1`.

| Value | Method | Expert |
|---|---|---|
| `cancer: Breast cancer` | missing | control **x** |
| `cancer: Colorectal cancer` | missing | control **x** |
| `cancer: Bile duct cancer` | missing | control **x** |
| `cancer: Mesothelioma` | disease | disease |
| `cancer: Urothelial cancer` | missing | control **x** |
| `cancer: Pancreatic cancer` | missing | control **x** |
| `cancer: Melanoma` | missing | control **x** |
| `cancer: Hepatocellular carcinoma` | missing | control **x** |
| `cancer: Ovarian cancer` | missing | control **x** |
| `cancer: Cervical cancer` | missing | control **x** |

**GSE131281**, trait *Multiple sclerosis*, method B, qwen2.5-coder:3b, accuracy 60%. Study title: Multiple sclerosis cortical normal-appearing grey matter and control grey matter

Chosen row `char_5`; expert row `char_5`.

| Value | Method | Expert |
|---|---|---|
| `ms type: PPMS` | disease | disease |
| `ms type: SPMS` | disease | disease |
| `ms type: ?` | unknown | control **x** |
| `ms type: PRMS` | disease | disease |

## invalid output (1 failed cohort attempts)

**GSE285666**, trait *Intellectual Disability*, method B, qwen2.5-coder:3b, accuracy 0%. Study title: Exon- and gene-Level transcriptional profiling in Lymphoblastoid Cell Lines (LCLs) from Williams syndrome patients and controls

Reason: row 'char_1' is not one of the row ids. Start of the output: `{"row": "char_1", "mapping": {"disease state: unaffected parental control": "control", "disease state: Williams syndrome patient": "disease"}}`

## other (2 failed cohort attempts)

**GSE178201**, trait *Liver Cancer*, method B, qwen2.5-coder:3b, accuracy 50%. Study title: The Carcinogenome Project
(Expert judgment call: cell lines: HepG2 (liver cancer) vs MCF10A (breast) as control.)

Chosen row `char_0`; expert row `char_0`.

| Value | Method | Expert |
|---|---|---|
| `tissue: HEPG2` | disease | disease |
| `tissue: MCF10A.TP53.M` | disease | control **x** |
| `tissue: MCF10A.WT.HP` | disease | control **x** |

