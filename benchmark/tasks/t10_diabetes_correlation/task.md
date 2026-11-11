# Strongest correlate of diabetes progression

Which single feature has the largest absolute Pearson correlation with `target`? Report its
column name and its (signed) correlation.

The data files are in the `data/` folder of the current working directory.

At the end, your program must print exactly one line that starts with `ANSWER:` followed by a JSON object with these keys:

- `feature`: column name, exactly as in the CSV header
- `correlation`: signed Pearson correlation with target
