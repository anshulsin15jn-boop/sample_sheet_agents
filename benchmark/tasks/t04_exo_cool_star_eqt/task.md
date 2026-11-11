# Equilibrium temperature of small planets around cool stars

Among planets with radius `pl_rade` below 2 Earth radii orbiting stars with `st_teff`
below 4000 K, find how many have a known equilibrium temperature `pl_eqt`, and the median
of those temperatures in kelvin.

The data files are in the `data/` folder of the current working directory.

At the end, your program must print exactly one line that starts with `ANSWER:` followed by a JSON object with these keys:

- `n_planets`: number of such planets with a known pl_eqt
- `median_eqt_k`: median pl_eqt in kelvin
