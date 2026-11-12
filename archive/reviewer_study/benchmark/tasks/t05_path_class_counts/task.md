# PathMNIST class balance

Using the PathMNIST subsample, find the most common tissue label in the training split and
the fraction of test images that are adipose tissue (label 0).

The data files are in the `data/` folder of the current working directory.

At the end, your program must print exactly one line that starts with `ANSWER:` followed by a JSON object with these keys:

- `most_common_train_label`: integer label that appears most often in y_train
- `adipose_fraction_test`: fraction of y_test equal to 0, between 0 and 1
