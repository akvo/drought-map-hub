# -*- coding: utf-8 -*-
"""
STEP_0302 — percent-rank the CDI weighted sum against its own record.

Optional. Runs only when `cdi_ranking` is "pooled" in cdi_project_settings.conf;
the default "none" exports the raw blend and skips this step entirely.

WHY THIS EXISTS (and why it is not the step that was deleted)
-------------------------------------------------------------
A weighted mean of percentiles is NOT itself a percentile. Averaging the NDMC
inputs concentrates the result toward the middle: measured on the live series
the components each have std ~0.27 while the blend has std ~0.168. The hub
applies US Drought Monitor percentile thresholds (D4 <=0.02 ... D0 <=0.30),
which assume a uniform 0-1 input. Applied to the blend they almost never fire:
D3 and D4 became arithmetically unreachable and no month reached any drought
category once aggregated to Inkhundla level.

Ranking the blend restores a uniform scale, so the thresholds mean what they
were designed to mean.

The DELETED step ranked each calendar month against the same month in other
years. With NDMC's SPI starting in 2023 that was 2-4 samples, giving a rank out
of 2-4 - which is what published 2026-05 as D4 nationwide. This step instead
pools every month together, so N is the whole series length rather than the
number of years.

Pooling is legitimate here precisely because the inputs arrive deseasonalised:
NDMC already percentile-ranks each index against its own calendar-month
climatology, so the blend carries no seasonal cycle to preserve. Measured
seasonal spread on the live series is 0.097 against a within-month spread of
0.079 - consistent with sampling noise at n=3.

RESOLUTION CEILING: ranking against N months resolves percentiles no finer than
1/N. At 34 months that is 2.9%, marginal against the 2% D4 band. NDMC extending
the SPI export back to 2012 would give ~168 months (0.6%) and resolve it
cleanly. Until then, treat D4 as indicative.
"""
import os

import numpy as np

from libs.config_reader import ConfigParser
import libs.netcdf_functions as netcdf

MISSING = -9999.0


def ranking_mode(config):
    """Return the configured ranking mode, defaulting to "none".

    Kept tolerant so an older cdi_project_settings.conf without the key keeps
    working and simply exports the raw blend.
    """
    try:
        return str(config.get("cdi_ranking")).lower()
    except KeyError:
        return "none"


def pooled_percent_rank(cube):
    """Percent-rank each pixel across the whole time axis.

    Uses the mid-rank plotting position. For a value with `less` observations
    below it and `equal` observations tied with it (itself included), the
    average rank is `less + (equal + 1) / 2`, and the plotting position
    `(rank - 0.5) / n` reduces to:

        (less + equal / 2) / n

    which is symmetric about 0.5 and splits ties evenly. Done directly in numpy
    rather than via scipy.stats.rankdata - it is two lines, and scipy is
    otherwise only referenced by the dormant CHIRPS SPI code.

    Args:
        cube: (time, lat, lon) array using MISSING for absent data.

    Returns:
        Array of the same shape holding percent ranks, MISSING preserved.
    """
    valid = cube != MISSING
    counts = valid.sum(axis=0)
    safe_counts = np.where(counts == 0, 1, counts)
    ranked = np.full(cube.shape, MISSING, dtype=float)
    for t in range(cube.shape[0]):
        current = cube[t]
        less = ((cube < current) & valid).sum(axis=0)
        equal = ((cube == current) & valid).sum(axis=0)
        pct = (less + equal / 2.0) / safe_counts
        ranked[t] = np.where(valid[t] & (counts > 0), np.round(pct, 3), MISSING)
    return ranked


def main():
    config = ConfigParser()
    mode = ranking_mode(config)
    if mode != "pooled":
        print("cdi_ranking={} - skipping pooled rank.".format(mode))
        return

    output_dir = config.get("output_dir").replace("\\", "/")
    region = config.get("region_name")
    source = os.path.join(
        output_dir, "STEP_0301_CDI_weighted_sum_{}.nc".format(region)
    )
    target = os.path.join(
        output_dir, "STEP_0302_CDI_pooled_rank_{}.nc".format(region)
    )

    input_data_set = netcdf.open_dataset(source)
    try:
        times = np.array(input_data_set.variables["time"][:])
        cube = netcdf.extract_data(input_data_set, "cdi_weighted_sum", -1)
    finally:
        input_data_set.close()

    if len(times) < 20:
        print(
            "WARNING: ranking against only {} months. Percentiles are resolved "
            "no finer than {:.1f}%, so the extreme categories are not "
            "meaningful yet.".format(len(times), 100.0 / max(len(times), 1))
        )

    print("Pooled percent-rank of {} CDI month(s)...".format(len(times)))
    ranked = pooled_percent_rank(cube)

    output_data_set = None
    try:
        output_data_set = netcdf.initialize_dataset(target, {
            "latitudes": config.get("latitudes"),
            "longitudes": config.get("longitudes"),
            "times": times,
            "time_units": "days since 1900-01-01 00:00:00.0 UTC",
        })
        variable = output_data_set.createVariable(
            "cdi_pooled_rank", "float32", ("time", "latitude", "longitude")
        )
        variable.units = "1"
        variable.missing_value = MISSING
        variable.standard_name = "cdi_pooled_rank"
        variable.long_name = (
            "CDI weighted sum percent-ranked against the full record"
        )
        variable[:] = ranked
    finally:
        if output_data_set is not None:
            output_data_set.close()


if __name__ == "__main__":
    main()
