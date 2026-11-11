# Small planets in a simple habitable zone

Using the NASA exoplanet table, count the planets that satisfy a simple habitability rule:
radius `pl_rade` at most 1.6 Earth radii AND insolation `pl_insol` between 0.25 and 1.5
(inclusive). Planets missing either value do not count.

The data files are in the `data/` folder of the current working directory.

At the end, your program must print exactly one line that starts with `ANSWER:` followed by a JSON object with these keys:

- `n_planets`: integer number of planets meeting the rule
