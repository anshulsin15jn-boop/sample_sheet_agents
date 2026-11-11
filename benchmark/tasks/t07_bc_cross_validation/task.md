# Breast cancer cross validation

Estimate how well a logistic regression separates malignant from benign tumors. Use all 30
feature columns to predict `target`. Use 5 fold cross validation with
`StratifiedKFold(n_splits=5, shuffle=True, random_state=0)` on a pipeline of
`StandardScaler()` then `LogisticRegression(max_iter=5000)`, and report the mean accuracy.

The data files are in the `data/` folder of the current working directory.

At the end, your program must print exactly one line that starts with `ANSWER:` followed by a JSON object with these keys:

- `mean_cv_accuracy`: mean accuracy over the 5 folds
