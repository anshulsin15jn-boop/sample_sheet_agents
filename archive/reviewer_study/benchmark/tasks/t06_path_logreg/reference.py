import json
import numpy as np
from sklearn.linear_model import LogisticRegression
z = np.load("data/pathmnist_small.npz")
Xtr = z["x_train"].reshape(len(z["y_train"]), -1) / 255.0
Xte = z["x_test"].reshape(len(z["y_test"]), -1) / 255.0
clf = LogisticRegression(max_iter=300).fit(Xtr, z["y_train"])
print("ANSWER: " + json.dumps({"test_accuracy": float(clf.score(Xte, z["y_test"]))}))
