# Diabetes linear regression

Predict `target` from all 10 features with ordinary least squares `LinearRegression()`.
Split with `train_test_split(X, y, test_size=0.2, random_state=42)`. Report R squared
and root mean squared error on the test part.

The data files are in the `data/` folder of the current working directory.

At the end, your program must print exactly one line that starts with `ANSWER:` followed by a JSON object with these keys:

- `test_r2`: R squared on the test part
- `test_rmse`: RMSE on the test part
