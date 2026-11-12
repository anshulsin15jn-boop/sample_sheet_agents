"""Copy small, fixed subsets of data from my earlier projects into benchmark/sources/.

Only reads from the other project folders; never writes to them. The outputs are committed,
so this script only needs to run once.

    python -m scripts.make_sources --exo PATH_TO_pscomppars.csv --path PATH_TO_pathmnist.npz
"""
import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "benchmark" / "sources"
HOME = Path.home()
EXO_DEFAULT = HOME / "exoplanet-habitability/data/raw/pscomppars_2026-10-24.csv"
PATH_DEFAULT = HOME / "trustworthy_tissue_classifier/data/pathmnist.npz"

EXO_COLS = ["pl_name", "hostname", "discoverymethod", "disc_year", "pl_rade", "pl_bmasse",
            "pl_orbper", "pl_insol", "pl_eqt", "st_teff", "st_mass", "sy_dist"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--exo", default=str(EXO_DEFAULT))
    ap.add_argument("--path", default=str(PATH_DEFAULT))
    a = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)

    exo = pd.read_csv(a.exo, usecols=EXO_COLS)[EXO_COLS]
    exo.to_csv(OUT / "exoplanets.csv", index=False)
    print("exoplanets:", exo.shape)

    rng = np.random.default_rng(0)
    with np.load(a.path) as z:
        tr = np.sort(rng.choice(len(z["train_labels"]), 1000, replace=False))
        te = np.sort(rng.choice(len(z["test_labels"]), 300, replace=False))
        np.savez_compressed(OUT / "pathmnist_small.npz",
                            x_train=z["train_images"][tr], y_train=z["train_labels"][tr].ravel(),
                            x_test=z["test_images"][te], y_test=z["test_labels"][te].ravel())
    print("pathmnist: 1000 train, 300 test")
    (OUT / "SOURCES.md").write_text(
        "# Data sources\n\n"
        "* `exoplanets.csv`: NASA Exoplanet Archive, Planetary Systems Composite Parameters table "
        "(pscomppars), downloaded 2026-10-24 for the exoplanet-habitability project. "
        "Selected columns only.\n"
        "* `pathmnist_small.npz`: random subsample (seed 0) of PathMNIST from MedMNIST v2 "
        "(Yang et al. 2023), 1000 train and 300 test images of 28x28x3, as used in the "
        "trustworthy_tissue_classifier project. Labels: 0 adipose, 1 background, 2 debris, "
        "3 lymphocytes, 4 mucus, 5 smooth muscle, 6 normal colon mucosa, "
        "7 cancer associated stroma, 8 colorectal adenocarcinoma epithelium.\n"
        "* Classic datasets (breast cancer, diabetes, wine) come from scikit-learn and are "
        "written by build_benchmark.py.\n", encoding="utf-8")


if __name__ == "__main__":
    main()
