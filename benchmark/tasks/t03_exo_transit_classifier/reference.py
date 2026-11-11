import json
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
df = pd.read_csv("data/exoplanets.csv").dropna(subset=["pl_orbper", "pl_rade", "st_teff"])
X = np.column_stack([np.log10(df["pl_orbper"]), np.log10(df["pl_rade"]), df["st_teff"]])
y = (df["discoverymethod"] == "Transit").astype(int).to_numpy()
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, random_state=0, stratify=y)
model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)).fit(Xtr, ytr)
print("ANSWER: " + json.dumps({"test_accuracy": float(model.score(Xte, yte)),
                               "n_rows_used": int(len(df))}))
