import json
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold, cross_val_score
df = pd.read_csv("data/diabetes.csv")
s = cross_val_score(Ridge(alpha=1.0), df.drop(columns="target"), df["target"], scoring="r2",
                    cv=KFold(n_splits=5, shuffle=True, random_state=0))
print("ANSWER: " + json.dumps({"mean_cv_r2": float(s.mean())}))
