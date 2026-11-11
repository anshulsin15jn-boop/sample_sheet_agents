import json
import pandas as pd
df = pd.read_csv("data/exoplanets.csv")
sel = df[(df["pl_rade"] < 2) & (df["st_teff"] < 4000)]["pl_eqt"].dropna()
print("ANSWER: " + json.dumps({"n_planets": int(len(sel)), "median_eqt_k": float(sel.median())}))
