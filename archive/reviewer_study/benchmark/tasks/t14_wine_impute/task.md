# Wine missing value cleanup

Some measurements in wine_missing.csv are missing (empty cells). Count the rows that have at
least one missing value. Then fill every missing value with the median of its column
(computed from the observed values) and report the mean of `magnesium` after filling.

The data files are in the `data/` folder of the current working directory.

At the end, your program must print exactly one line that starts with `ANSWER:` followed by a JSON object with these keys:

- `n_rows_with_missing`: rows with at least one missing value
- `mean_magnesium_after_impute`: mean magnesium after median filling
