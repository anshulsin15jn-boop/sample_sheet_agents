# Wine group statistics

How many wines belong to each cultivar (target 0, 1, 2), and which cultivar has the highest
average `alcohol`?

The data files are in the `data/` folder of the current working directory.

At the end, your program must print exactly one line that starts with `ANSWER:` followed by a JSON object with these keys:

- `n_class_0`: number of wines with target 0
- `n_class_1`: number of wines with target 1
- `n_class_2`: number of wines with target 2
- `highest_alcohol_class`: the target value (0, 1, or 2) with the highest mean alcohol
