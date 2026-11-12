import json
import numpy as np
z = np.load("data/pathmnist_small.npz")
print("ANSWER: " + json.dumps({"most_common_train_label": int(np.bincount(z["y_train"]).argmax()),
      "adipose_fraction_test": float((z["y_test"] == 0).mean())}))
