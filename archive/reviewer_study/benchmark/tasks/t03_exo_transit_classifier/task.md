# Predict the transit method from planet properties

Build a classifier that predicts whether a planet was discovered by the "Transit" method
(1) or any other method (0). Steps:
1. Keep only rows where `pl_orbper`, `pl_rade`, and `st_teff` are all present.
2. Features: log10(pl_orbper), log10(pl_rade), st_teff (in that order).
3. Split with sklearn `train_test_split(X, y, test_size=0.25, random_state=0, stratify=y)`.
4. Fit a pipeline of `StandardScaler()` then `LogisticRegression(max_iter=1000)` on the
   training part and report accuracy on the test part.

The data files are in the `data/` folder of the current working directory.

At the end, your program must print exactly one line that starts with `ANSWER:` followed by a JSON object with these keys:

- `test_accuracy`: test accuracy between 0 and 1
- `n_rows_used`: number of rows kept after step 1
