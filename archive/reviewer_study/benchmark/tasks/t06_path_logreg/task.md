# PathMNIST logistic regression baseline

Train a simple baseline on the PathMNIST subsample. Flatten each image to a vector of
2352 values, divide by 255, fit `LogisticRegression(max_iter=300)` (scikit-learn defaults
otherwise) on the training split, and report accuracy on the test split. No neural networks.

The data files are in the `data/` folder of the current working directory.

At the end, your program must print exactly one line that starts with `ANSWER:` followed by a JSON object with these keys:

- `test_accuracy`: test accuracy between 0 and 1
