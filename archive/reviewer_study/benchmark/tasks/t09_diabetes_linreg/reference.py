import json
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
df = pd.read_csv("data/diabetes.csv")
X, y = df.drop(columns="target"), df["target"]
Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42)
p = LinearRegression().fit(Xtr, ytr).predict(Xte)
print("ANSWER: " + json.dumps({"test_r2": float(r2_score(yte, p)),
      "test_rmse": float(np.sqrt(mean_squared_error(yte, p)))}))
