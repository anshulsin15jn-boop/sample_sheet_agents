# Diabetes ridge regression cross validation

Estimate the R squared of `Ridge(alpha=1.0)` (no scaling) predicting `target` from all 10
features, using 5 fold cross validation with `KFold(n_splits=5, shuffle=True, random_state=0)`.
Report the mean R squared over the folds.

The data files are in the `data/` folder of the current working directory.

At the end, your program must print exactly one line that starts with `ANSWER:` followed by a JSON object with these keys:

- `mean_cv_r2`: mean R squared over the 5 folds
