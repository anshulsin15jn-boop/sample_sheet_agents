# Data sources

* `exoplanets.csv`: NASA Exoplanet Archive, Planetary Systems Composite Parameters table (pscomppars), downloaded 2026-10-24 for the exoplanet-habitability project. Selected columns only.
* `pathmnist_small.npz`: random subsample (seed 0) of PathMNIST from MedMNIST v2 (Yang et al. 2023), 1000 train and 300 test images of 28x28x3, as used in the trustworthy_tissue_classifier project. Labels: 0 adipose, 1 background, 2 debris, 3 lymphocytes, 4 mucus, 5 smooth muscle, 6 normal colon mucosa, 7 cancer associated stroma, 8 colorectal adenocarcinoma epithelium.
* Classic datasets (breast cancer, diabetes, wine) come from scikit-learn and are written by build_benchmark.py.
