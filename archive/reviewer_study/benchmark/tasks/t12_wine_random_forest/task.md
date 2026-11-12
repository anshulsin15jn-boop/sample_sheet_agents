# Wine random forest

Classify the wine cultivar (`target`) from all 13 features. Split with
`train_test_split(X, y, test_size=0.3, random_state=1, stratify=y)`, fit
`RandomForestClassifier(n_estimators=200, random_state=0)`, and report test accuracy and the
number of test rows.

The data files are in the `data/` folder of the current working directory.

At the end, your program must print exactly one line that starts with `ANSWER:` followed by a JSON object with these keys:

- `test_accuracy`: test accuracy between 0 and 1
- `n_test`: number of rows in the test part
