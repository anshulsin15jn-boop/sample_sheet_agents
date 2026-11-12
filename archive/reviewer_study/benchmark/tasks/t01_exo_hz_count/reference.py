import json
import pandas as pd
df = pd.read_csv("data/exoplanets.csv")
ok = (df["pl_rade"] <= 1.6) & (df["pl_insol"] >= 0.25) & (df["pl_insol"] <= 1.5)
print("ANSWER: " + json.dumps({"n_planets": int(ok.sum())}))
