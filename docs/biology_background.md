# Biology background

A short background on the data the agents read, for readers without a biology background.

## Genes and gene expression

Every cell in the human body carries the same DNA, which contains about 20,000 genes. A gene is a recipe
for making a protein. Cells do not use every recipe all the time: a liver cell uses liver recipes, an
immune cell uses immune recipes. How much a cell is using a gene right now is called that gene's
**expression level**.

A **gene expression dataset** is a big table of numbers. Each column is one **sample** (for example,
a blood draw from one patient or a piece of tissue from a surgery) and each row is one gene. A number
says how strongly that gene was being used in that sample.

Scientists compare groups: if a gene is used much more in asthma patients than in healthy people, it
might be involved in asthma. That comparison only works if **which samples are which** is known correctly.

## GEO: the public library of these datasets

The **Gene Expression Omnibus (GEO)** is a free public database run by the US National Center for
Biotechnology Information (NCBI). Researchers upload their datasets when they publish a paper.

* A **series** (ID starting with `GSE`, for example `GSE182797`) is one study's dataset.
* A **sample** (ID starting with `GSM`) is one column in it.
* Each series has a **series matrix file**. Its top part (the header) describes the study and every
  sample; the bottom part is the table of numbers. This project only reads the header.

## The sample sheet: where the trouble starts

For each sample, the header has a few lines of description written by the researchers:

* **Sample title**, for example `AAD_11 [nasal]` or `healthy donor, H-3`
* **Source name**, for example `Nasal biopsy` or `human pancreatic tumor tissue sample 12`
* **Characteristics**, usually as `key: value`, for example `diagnosis: adult-onset asthma`,
  `age: 38`, `gender: Female`

There is no required vocabulary. One study writes `disease state: control`, another `group: Healthy`,
another `condition: ANL`, another just `genotype: T21`. This free text is what I call the "sample
sheet", and turning it into clean labels is the step this project studies.

## Case and control

Most studies compare two kinds of samples:

* **Cases**: samples with the condition being studied (the "disease" label here).
* **Controls**: samples to compare against (the "control" label here).

A control is not always a healthy person. Common kinds in the benchmark:

* **Healthy controls**: people without the disease.
* **Adjacent normal tissue**: healthy looking tissue cut from right next to a tumour, from the same
  patient. Labelled `adjacent non-tumor` or `paratumor`.
* **Non lesional skin**: skin from a patient with a skin disease, taken from a spot without a rash.
  `AL` means atopic lesional (eczema rash) and `ANL` means atopic non lesional. Studies and experts
  disagree on how to treat it. In GSE32924 the experts labelled ANL samples as **disease**, because
  the person has eczema. In GSE57225, `control (non-involved)` skin was labelled **control**. The
  same biological idea gets opposite labels depending on the study, which is a real source of errors.
* **Other diseases**: in a study of many diseases, every sample without the trait of interest is a 0.
  For example, for "Mesothelioma" a sample from a breast cancer patient counts as a control.
* **Wild type or euploid**: "normal genetics". In Down syndrome studies, `T21` (an extra copy of
  chromosome 21) is the case and `Euploid` (the normal number of chromosomes) is the control.

## A few terms that show up in the metadata

* **Huntington's disease** is caused by a stretch of the HTT gene that repeats the letters CAG too
  many times. About 36 or more repeats means the disease, so a row like
  `htt cag repeat length: 42` is the trait, written as a number.
* **Intellectual disability** cohorts may never say "intellectual disability". They name a cause
  instead, such as Williams syndrome or Down syndrome (T21).
* **Atrial fibrillation (AF)** is an irregular heartbeat. **Sinus rhythm** is the normal heartbeat,
  so it plays the control role.
* **Endometrioid** is one subtype of ovarian or uterine cancer. In those cohorts the other subtypes
  (serous, clear cell, mucinous) are the controls.
* **Lupus** subtypes like CCLE (chronic cutaneous) and SCLE (subacute cutaneous) are skin forms of
  lupus; `Skin Control` is the control. In GSE148810, `JM` means juvenile dermatomyositis, a
  different disease, so `JM Lesional skin` is a control for lupus even though it is diseased skin.
* **Excluded samples**: sometimes the experts give no label at all. In a bipolar disorder study that
  also has depression and schizophrenia patients (GSE53987), those other patients were left out
  rather than called controls. Unlabelled samples are not graded here.
* **Label judgment calls**: the answer key is human work and a few choices are debatable. In GSE120490
  (all samples are endometrioid cancer patients), the experts used `matastasis: Yes` as the case
  label. I keep the expert labels as they are and point such cases out in the error analysis.

## Where GenoTEX and GenoMAS come in

GenoTEX is a benchmark from Haohan Wang's lab in which experts preprocessed about 900 GEO datasets for
about 130 traits, including deciding which samples are cases and which are controls. Those expert
decisions are the answer key here. GenoMAS is the same group's multi agent system that tries to do
that whole analysis automatically. Both found this labelling step to be the weakest part.
