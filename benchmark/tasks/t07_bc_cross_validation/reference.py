import json
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
df = pd.read_csv("data/breast_cancer.csv")
X, y = df.drop(columns="target"), df["target"]
s = cross_val_score(make_pipeline(StandardScaler(), LogisticRegression(max_iter=5000)), X, y,
                    cv=StratifiedKFold(n_splits=5, shuffle=True, random_state=0))
print("ANSWER: " + json.dumps({"mean_cv_accuracy": float(s.mean())}))
