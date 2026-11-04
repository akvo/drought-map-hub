# -*- coding: utf-8 -*-
import time
import sys

# from netCDF4 import Dataset
from STEP_0100_ingest_ndmc_geotiffs import main as step_0100
from STEP_0301_CDI_weighted_sum import main as step_0301
from STEP_0302_rank_cdi_pooled import main as step_0302
from STEP_0303_export_ranking_data_rasters import main as step_0303
from argparse import ArgumentParser

"""
Use anaconda 3.7 virtual environment
Packages:
    conda: h5py
    conda: netCDF4
    conda: imageio
    conda: scipy
    conda: rasterio
"""


def log_time(step_name, func, *args):
    # log the time taken to execute the function
    # if any error occured, exit the program with sys.exit(1)
    start_time = time.time()
    try:
        print(f"Executing {step_name}...")
        func(*args)
    except Exception as e:
        print(f"Error in {step_name}: {e}")
        sys.exit(1)
    finally:
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"{step_name} completed in {elapsed_time:.2f} seconds.\n")


def main(args):
    # STEP_0100 ingests the pre-ranked NDMC GeoTIFFs into ranked NetCDF files,
    # replacing the old STEP_0101/0102/0103 + STEP_0201/0202/0203 chain.
    #
    # STEP_0302 is a no-op unless cdi_ranking is "pooled". It is NOT the step
    # that was deleted: that one ranked each calendar month against the same
    # month in other years - 2-4 samples, which published 2026-05 as D4
    # nationwide. This one ranks the blend against the whole record, which is
    # what makes the hub's USDM thresholds meaningful. See its docstring and
    # docs/cdi-ranking-scale-fix.md.
    log_time("Step 0100", step_0100, args)
    log_time("Step 0301", step_0301)
    log_time("Step 0302", step_0302)
    log_time("Step 0303", step_0303, args)
    print("Finished processing CDI data")


if __name__ == '__main__':
    # set up the command line argument parser
    parser = ArgumentParser()
    parser.add_argument(
        "-m", "--mode", default="recent",
        help="Export mode: 'recent' (latest month only) or 'all' (every "
             "month). Ingestion and analysis always use the full staged "
             "history regardless of this flag. Default is recent")
    # execute the programs with the supplied options
    main(parser.parse_args())
