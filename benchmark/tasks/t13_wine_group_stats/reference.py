import json
import pandas as pd
df = pd.read_csv("data/wine.csv")
n = df["target"].value_counts()
best = int(df.groupby("target")["alcohol"].mean().idxmax())
print("ANSWER: " + json.dumps({"n_class_0": int(n[0]), "n_class_1": int(n[1]),
      "n_class_2": int(n[2]), "highest_alcohol_class": best}))
