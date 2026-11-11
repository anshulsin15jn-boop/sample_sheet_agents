# Discovery methods

Using the NASA exoplanet table, count how many planets were discovered by the "Transit"
method and how many by the "Radial Velocity" method, and compute the median orbital
period (`pl_orbper`, days) of the Transit planets, ignoring missing periods.

The data files are in the `data/` folder of the current working directory.

At the end, your program must print exactly one line that starts with `ANSWER:` followed by a JSON object with these keys:

- `n_transit`: number of Transit planets
- `n_radial_velocity`: number of Radial Velocity planets
- `median_period_transit_days`: median orbital period of Transit planets in days
