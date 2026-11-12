# Readmission model at discharge

The hospital wants a model that predicts 30 day readmission (`readmitted_30d`) at the
moment a patient is discharged. Train a pipeline of `StandardScaler()` then
`LogisticRegression(max_iter=1000)` using the features that would be available at
discharge. Split with `train_test_split(X, y, test_size=0.25, random_state=0, stratify=y)`
and report the test accuracy you would expect in real use.

The data files are in the `data/` folder of the current working directory.

At the end, your program must print exactly one line that starts with `ANSWER:` followed by a JSON object with these keys:

- `test_accuracy`: test accuracy between 0 and 1
