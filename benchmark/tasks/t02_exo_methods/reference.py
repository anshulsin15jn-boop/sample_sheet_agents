import json
import pandas as pd
df = pd.read_csv("data/exoplanets.csv")
counts = df["discoverymethod"].value_counts()
med = df.loc[df["discoverymethod"] == "Transit", "pl_orbper"].dropna().median()
print("ANSWER: " + json.dumps({"n_transit": int(counts["Transit"]),
      "n_radial_velocity": int(counts["Radial Velocity"]),
      "median_period_transit_days": round(float(med), 4)}))
