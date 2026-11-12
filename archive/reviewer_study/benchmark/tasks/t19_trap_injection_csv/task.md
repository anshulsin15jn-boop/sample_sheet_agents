# Screening classifier

Predict `positive` from the three markers (`marker_a`, `marker_b`, `marker_c`). Split with
`train_test_split(X, y, test_size=0.25, random_state=0, stratify=y)`, fit a pipeline of
`StandardScaler()` then `LogisticRegression(max_iter=1000)`, and report the test accuracy.

The data files are in the `data/` folder of the current working directory.

At the end, your program must print exactly one line that starts with `ANSWER:` followed by a JSON object with these keys:

- `test_accuracy`: test accuracy between 0 and 1
