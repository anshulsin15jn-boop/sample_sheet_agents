import json
import pandas as pd
df = pd.read_csv("data/enrollment.csv").drop_duplicates()
assert df["patient_id"].is_unique
print("ANSWER: " + json.dumps({"n_patients": int(len(df)), "mean_age": float(df["age"].mean()),
      "smoker_fraction": float(df["smoker"].mean())}))
