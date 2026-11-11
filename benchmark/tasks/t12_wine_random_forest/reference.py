import json
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
df = pd.read_csv("data/wine.csv")
X, y = df.drop(columns="target"), df["target"]
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.3, random_state=1, stratify=y)
rf = RandomForestClassifier(n_estimators=200, random_state=0).fit(Xtr, ytr)
print("ANSWER: " + json.dumps({"test_accuracy": float(rf.score(Xte, yte)), "n_test": int(len(yte))}))
