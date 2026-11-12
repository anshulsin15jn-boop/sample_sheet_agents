import json
import numpy as np
import pandas as pd
df = pd.read_csv("data/lipids.csv")
chol = df["cholesterol_mg_dl"].replace(-999, np.nan).dropna()
print("ANSWER: " + json.dumps({"mean_cholesterol": float(chol.mean()),
      "n_above_240": int((chol > 240).sum())}))
