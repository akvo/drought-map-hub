# -*- coding: utf-8 -*-
"""
STEP_0100 — Ingest NDMC Regional Percentiles GeoTIFFs into ranked NetCDF files.

This single step replaces the old STEP_0101/0102/0103 (HDF/CHIRPS -> anomaly NetCDF)
and STEP_0201/0202/0203 (anomaly -> percent-rank NetCDF). The NDMC data is already
percentile-ranked (0-100 scale), so the only work needed is:

    1. Sample each GeoTIFF onto the config-generated Eswatini grid (44 x 44).
    2. Map NDMC nodata (-1) to the internal missing value (-9999.0).
    3. Divide valid values by 100 so the internal scale is 0-1 (what STEP_0301 expects).
    4. Write a time x lat x lon NetCDF per dataset, using the SAME latitude/longitude
       arrays that STEP_0301 / STEP_0303 read from the config, so shapes line up.

Polarity note: every NDMC percentile is "high = wetter / less drought" (ESI included:
high ESI percentile = low evaporative stress = wet). Do NOT invert any dataset.
"""
import os
import re
from argparse import ArgumentParser
from datetime import date

import numpy as np
import rasterio
from rasterio.windows import Window

from libs.config_reader import ConfigParser
import libs.netcdf_functions as netcdf

# NDMC publishes percentiles on a 0-100 scale; the internal pipeline works in 0-1.
NDMC_SCALE = 100.0
# NDMC nodata value in the source GeoTIFFs.
NDMC_NODATA = -1.0
# Internal missing value used across the CDI pipeline.
MISSING = -9999.0
# Origin for the NetCDF "days since" time axis (matches the rest of the pipeline).
ORIGIN_DATE = date(1900, 1, 1)

# Each CDI key maps to: the config raw-data-dir key, and the NetCDF variable name
# (the variable name must match cdi_parameters.names in cdi_project_settings.conf).
DATASETS = {
    "esi": {"dir_key": "esi_tif", "variable": "esi_pct_rank", "label": "ESI"},
    "evi2": {"dir_key": "evi2_tif", "variable": "evi2_pct_rank", "label": "EVI2"},
    "spi": {"dir_key": "spi_tif", "variable": "spi_pct_rank", "label": "SPI"},
    "sm": {"dir_key": "sm_tif", "variable": "sm_pct_rank", "label": "SM"},
}


class NDMCIngestor:
    """Ingests one NDMC dataset directory into a ranked NetCDF file."""

    def __init__(self, dataset_key):
        self.__key = dataset_key
        self.__meta = DATASETS[dataset_key]
        self.__config = ConfigParser()
        self.__region = self.__config.get("region_name")
        self.__output_dir = self.__config.get("output_dir").replace("\\", "/")
        self.__raw_dir = self.__config.get("raw_data_dirs", self.__meta["dir_key"]).replace("\\", "/")
        # The config GENERATES these inclusive 0.05-degree arrays (44 each). STEP_0301
        # and STEP_0303 use the very same arrays, so the grids match exactly.
        self.__latitudes = self.__config.get("latitudes")
        self.__longitudes = self.__config.get("longitudes")
        self.__rows = len(self.__latitudes)
        self.__cols = len(self.__longitudes)
        # Build the filename regex from the config pattern (dataset prefix is agnostic).
        pattern = self.__config.get("file_patterns")["ndmc_tif_regex"].replace("{dataset}", r".+")
        self.__file_match = re.compile(pattern)

    def __calendar_value(self, year, month):
        """Days since 1900-01-01 for the first of the given month (float)."""
        return float((date(year, month, 1) - ORIGIN_DATE).days)

    def get_tif_files(self):
        """Return a list of (calendar_time, year, month, path) sorted by date.

        Every staged file is ingested, always. This deliberately ignores --mode:
        ranking and the CDI blend are climatological operations, and scoping them
        by the export window is what produced a CDI ranked against 2 samples.
        --mode controls what gets downloaded and exported, never the analysis basis.
        """
        records = []
        if not os.path.isdir(self.__raw_dir):
            print("  Directory not found: {}".format(self.__raw_dir))
            return records
        for name in os.listdir(self.__raw_dir):
            match = self.__file_match.match(name)
            if not match:
                continue
            year, month = int(match.group(1)), int(match.group(2))
            records.append((self.__calendar_value(year, month), year, month,
                            os.path.join(self.__raw_dir, name)))
        records.sort(key=lambda r: r[0])
        return records

    def clip_and_scale(self, tif_path):
        """Read the 44x44 Eswatini block, mask nodata, then scale 0-100 -> 0-1.

        Config cell centres align exactly with NDMC pixel centres, so we can index
        the raster directly by coordinate and read a fixed window (no resampling).
        """
        with rasterio.open(tif_path) as src:
            # North-west corner of the target grid: westmost lon, northmost lat.
            row_off, col_off = src.index(self.__longitudes[0], self.__latitudes[0])
            window = Window(int(col_off), int(row_off), self.__cols, self.__rows)
            data = src.read(1, window=window).astype(float)
            nodata = src.nodata if src.nodata is not None else NDMC_NODATA

        if data.shape != (self.__rows, self.__cols):
            raise ValueError(
                "Clipped grid is {} but expected {} for {}; check bounds vs raster extent".format(
                    data.shape, (self.__rows, self.__cols), os.path.basename(tif_path)
                )
            )

        # Mask nodata BEFORE scaling so -1 never becomes -0.01.
        data[data == nodata] = MISSING
        valid = data != MISSING
        data[valid] = np.round(data[valid] / NDMC_SCALE, 3)
        return data

    def run(self):
        records = self.get_tif_files()
        label = self.__meta["label"]
        if not records:
            print("No {} GeoTIFFs found in {} — skipping.".format(label, self.__raw_dir))
            return

        times = [r[0] for r in records]
        output_file = os.path.join(
            self.__output_dir, "STEP_0100_{}_pct_rank_{}.nc".format(label, self.__region)
        )
        print("Ingesting {} {} file(s) -> {}".format(len(records), label, os.path.basename(output_file)))

        output_data_set = None
        try:
            out_properties = {
                "latitudes": self.__latitudes,
                "longitudes": self.__longitudes,
                "times": times,
                "time_units": "days since 1900-01-01 00:00:00.0 UTC",
            }
            output_data_set = netcdf.initialize_dataset(output_file, out_properties)
            var = output_data_set.createVariable(
                self.__meta["variable"], "float32", ("time", "latitude", "longitude")
            )
            var.units = "1"
            var.missing_value = MISSING
            var.standard_name = self.__meta["variable"]
            var.long_name = "NDMC percentile rank for {} (0-1)".format(label)

            for idx, (_, year, month, path) in enumerate(records):
                var[idx] = self.clip_and_scale(path)
        except IOError:
            raise
        except Exception:
            raise
        finally:
            if output_data_set is not None:
                output_data_set.close()


def main(args=None):
    """Entry point: ingest every staged CDI input dataset.

    `args` is accepted (and ignored) so STEP_0000 can call this uniformly with
    the other steps. Ingestion is never scoped by --mode; see get_tif_files.
    """
    print("Ingesting NDMC GeoTIFFs (full staged history)")
    for dataset_key in DATASETS:
        NDMCIngestor(dataset_key).run()


if __name__ == "__main__":
    parser = ArgumentParser(
        description="Ingest every staged NDMC GeoTIFF into ranked NetCDF "
                    "files. Takes no options: the analysis basis is always "
                    "the full staged history.")
    main(parser.parse_args())
