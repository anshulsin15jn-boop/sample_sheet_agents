import json
import pandas as pd
df = pd.read_csv("data/wine_missing.csv")
n = int(df.isna().any(axis=1).sum())
filled = df.fillna(df.median())
print("ANSWER: " + json.dumps({"n_rows_with_missing": n,
      "mean_magnesium_after_impute": float(filled["magnesium"].mean())}))
