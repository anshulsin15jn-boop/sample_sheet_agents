import json
import pandas as pd
df = pd.read_csv("data/anthropometry.csv")
# Site B wrote heights in meters (values around 1.7) although the column says cm.
h = df["height_cm"].where(df["height_cm"] > 3, df["height_cm"] * 100)
bmi = df["weight_kg"] / (h / 100) ** 2
print("ANSWER: " + json.dumps({"mean_height_cm": float(h.mean()), "mean_bmi": float(bmi.mean())}))
