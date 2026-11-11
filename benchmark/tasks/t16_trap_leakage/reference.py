import json
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
df = pd.read_csv("data/discharges.csv")
# followup_status_code is recorded after discharge and leaks the label; patient_id is an identifier.
X = df[["age", "prior_admissions", "length_of_stay_days", "hba1c"]].to_numpy()
y = df["readmitted_30d"].to_numpy()
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.25, random_state=0, stratify=y)
m = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)).fit(Xtr, ytr)
print("ANSWER: " + json.dumps({"test_accuracy": float(m.score(Xte, yte))}))
