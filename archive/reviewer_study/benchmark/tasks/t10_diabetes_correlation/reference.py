import json
import pandas as pd
df = pd.read_csv("data/diabetes.csv")
c = df.drop(columns="target").corrwith(df["target"])
best = c.abs().idxmax()
print("ANSWER: " + json.dumps({"feature": best, "correlation": float(c[best])}))
