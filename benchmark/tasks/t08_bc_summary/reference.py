import json
import pandas as pd
df = pd.read_csv("data/breast_cancer.csv")
g = df.groupby("target")["mean_radius"].mean()
print("ANSWER: " + json.dumps({"n_malignant": int((df["target"] == 0).sum()),
      "mean_radius_malignant": float(g[0]), "mean_radius_benign": float(g[1])}))
