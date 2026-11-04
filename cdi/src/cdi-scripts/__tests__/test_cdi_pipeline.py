# -*- coding: utf-8 -*-
"""Integration tests for the CDI chain: STEP_0100 -> STEP_0301 -> STEP_0303.

Each test drives synthetic NDMC-shaped GeoTIFFs through the real steps and
asserts the exported raster. No network, no committed binaries, no mocking of
the pipeline itself - only the working directory is redirected.

The config files are read from a fixed path next to `libs/`, but
`raw_data_dirs` and `output_dir` in `cdi_directory_settings.conf` are relative
(`../../input_data/...`), so they resolve against the current working
directory. Running from a temp dir therefore isolates the data while still
exercising the production config: real bounds, real 44x44 grid, real weights.

Every test here corresponds to a defect that reached production. See
docs/cdi-ranking-scale-fix.md.
"""
import os
import sys
from datetime import date

import numpy as np
import pytest
import rasterio
from rasterio.transform import Affine

CDI_SCRIPTS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if CDI_SCRIPTS not in sys.path:
    sys.path.insert(0, CDI_SCRIPTS)

from libs.config_reader import ConfigParser  # noqa: E402
import STEP_0302_rank_cdi_pooled as step_0302_module  # noqa: E402
import STEP_0303_export_ranking_data_rasters as step_0303_module  # noqa: E402
from STEP_0100_ingest_ndmc_geotiffs import main as step_0100  # noqa: E402
from STEP_0301_CDI_weighted_sum import main as step_0301  # noqa: E402
from STEP_0302_rank_cdi_pooled import main as step_0302  # noqa: E402
from STEP_0303_export_ranking_data_rasters import main as step_0303  # noqa: E402

# Directory name -> NDMC filename prefix, matching the production layout.
DATASETS = {
    "ESI": "era5_esi_1mn",
    "EVI2": "evi2_1mn",
    "SPI": "chirps_spi_3mn",
    "SM": "noah_soilm_1mn",
}
# NDMC publishes these months for every dataset except EVI2, which has none
# for January, July or August. That gap is what made the CDI time axis
# non-contiguous and exposed the STEP_0301 month-alignment bug.
EVI2_MISSING_MONTHS = (1, 7, 8)
NODATA = -1.0
MISSING = -9999.0
RESOLUTION = 0.05


class Args(object):
    """Stand-in for the argparse namespace the steps expect."""

    def __init__(self, mode):
        self.mode = mode


def months(start_year, start_month, count):
    """Yield `count` consecutive (year, month) pairs."""
    out = []
    y, m = start_year, start_month
    for _ in range(count):
        out.append((y, m))
        m += 1
        if m > 12:
            y, m = y + 1, 1
    return out


@pytest.fixture
def project(tmp_path, monkeypatch):
    """Create an isolated data tree and chdir into it.

    Returns a helper exposing the grid shape, a GeoTIFF writer, a pipeline
    runner and a reader for the exported CDI rasters.
    """
    # The config's relative paths climb two levels, so the working directory
    # must sit two levels below the data root.
    work = tmp_path / "src" / "background-job"
    work.mkdir(parents=True)
    for name in DATASETS:
        (tmp_path / "input_data" / name).mkdir(parents=True)
    for name in list(DATASETS) + ["CDI"]:
        (tmp_path / "output_data" / "GeoTiffs" / name).mkdir(parents=True)
    monkeypatch.chdir(work)

    # cdi_ranking lives in the repo's own .conf, which ConfigParser reads from a
    # fixed path - so without this the whole suite silently changes meaning the
    # moment someone flips the flag. Tests declare the mode they are testing.
    state = {"ranking": "none"}
    for module in (step_0302_module, step_0303_module):
        monkeypatch.setattr(
            module, "ranking_mode", lambda _config: state["ranking"]
        )

    config = ConfigParser()
    latitudes = config.get("latitudes")
    longitudes = config.get("longitudes")
    transform = (
        Affine.translation(longitudes[0] - RESOLUTION / 2,
                           latitudes[0] + RESOLUTION / 2)
        * Affine.scale(RESOLUTION, -RESOLUTION)
    )
    shape = (len(latitudes), len(longitudes))

    class Project(object):
        weights = config.get("cdi_parameters", "weights")
        rows, cols = shape

        @staticmethod
        def write_tif(dataset, year, month, values):
            """Write one NDMC-shaped GeoTIFF on the 0-100 percentile scale."""
            data = np.asarray(values, dtype="float32")
            if data.shape != shape:
                data = np.full(shape, float(values), dtype="float32")
            path = (tmp_path / "input_data" / dataset /
                    "{}_{:04d}-{:02d}-01.tif".format(
                        DATASETS[dataset], year, month))
            with rasterio.open(
                str(path), "w", driver="GTiff", width=shape[1],
                height=shape[0], count=1, dtype="float32",
                crs="+proj=latlong", transform=transform, nodata=NODATA,
            ) as dst:
                dst.write(data, 1)

        @staticmethod
        def stage(period, value_for):
            """Write every dataset for `period`, honouring the EVI2 gaps.

            `value_for(dataset, year, month)` returns the 0-100 value (scalar
            or array). Returning None skips that file entirely.
            """
            for dataset in DATASETS:
                for year, month in period:
                    if dataset == "EVI2" and month in EVI2_MISSING_MONTHS:
                        continue
                    value = value_for(dataset, year, month)
                    if value is None:
                        continue
                    Project.write_tif(dataset, year, month, value)

        @staticmethod
        def set_ranking(ranking):
            """Choose "none" (raw blend) or "pooled" for this test."""
            state["ranking"] = ranking

        @staticmethod
        def run(mode="all"):
            step_0100(Args(mode))
            step_0301()
            step_0302()
            step_0303(Args(mode))

        @staticmethod
        def read_cdi(year, month):
            """Return the exported CDI raster for one month, or None."""
            path = (tmp_path / "output_data" / "GeoTiffs" / "CDI" /
                    "STEP_0303_CDI_pct_rank_Eswatini_{:04d}{:02d}.tif".format(
                        year, month))
            if not path.exists():
                return None
            with rasterio.open(str(path)) as src:
                return src.read(1).astype(float)

        @staticmethod
        def exported_months():
            directory = tmp_path / "output_data" / "GeoTiffs" / "CDI"
            return sorted(
                (int(p.stem[-6:-2]), int(p.stem[-2:]))
                for p in directory.glob("*.tif")
            )

    return Project


def test_cdi_equals_weighted_sum_of_inputs(project):
    """The exported CDI is the weighted blend, not a rank of it.

    STEP_0302 used to re-rank the blend across years, collapsing a continuous
    percentile into a rank out of however many years were staged.
    """
    period = months(2020, 1, 24)
    values = {"ESI": 80.0, "EVI2": 60.0, "SPI": 40.0, "SM": 20.0}
    project.stage(period, lambda ds, y, m: values[ds])

    project.run()

    expected = sum(values[ds] / 100.0 * project.weights[ds.lower()]
                   for ds in values)
    cdi = project.read_cdi(2021, 12)
    assert cdi is not None, "no CDI exported for the final month"
    assert np.allclose(cdi, expected, atol=1e-3), (
        "CDI {} is not the weighted sum {}".format(cdi.mean(), expected))


def test_all_inputs_wet_never_exports_zero(project):
    """A month where every indicator is wet must not export as extreme drought.

    This is the 2026-05 regression: all four inputs in the 60th-99th
    percentile, published as 0.0 -> D4 Exceptional Drought nationwide.
    """
    period = months(2024, 1, 30)
    project.stage(period, lambda ds, y, m: 90.0)

    project.run()

    cdi = project.read_cdi(2026, 6)
    assert cdi is not None
    assert cdi.min() > 0.3, (
        "wet month exported as {} - the D4 regression is back".format(cdi.min()))
    assert np.allclose(cdi, 0.9, atol=1e-3)


def test_inputs_are_not_shifted_by_the_evi2_gaps(project):
    """Every input must contribute the month the raster is labelled with.

    STEP_0301 used to walk a contiguous index range over each input. Because
    EVI2 has no Jan/Jul/Aug, the common dates are not contiguous, so the
    gap-free inputs drifted earlier and earlier - by the end of the real
    series it was blending 2025-09 ESI/SPI/SM into the CDI labelled 2026-05.
    """
    period = months(2020, 1, 36)
    # A value unique to each month for the gap-free inputs; EVI2 is held
    # constant so any drift shows up entirely in the other three.
    def value_for(dataset, year, month):
        if dataset == "EVI2":
            return 50.0
        return float((year - 2020) * 12 + month)

    project.stage(period, value_for)

    project.run()

    evi2_share = 50.0 / 100.0 * project.weights["evi2"]
    others_share = sum(project.weights[k] for k in ("esi", "spi", "sm"))
    exported = project.exported_months()
    assert exported, "nothing exported"
    assert all(m not in EVI2_MISSING_MONTHS for _, m in exported), (
        "months with no EVI2 must not appear in the CDI")

    for year, month in exported:
        own_value = ((year - 2020) * 12 + month) / 100.0
        expected = evi2_share + own_value * others_share
        cdi = project.read_cdi(year, month)
        assert np.allclose(cdi, expected, atol=1e-3), (
            "{:04d}-{:02d} exported {:.4f}, expected {:.4f} - inputs are "
            "shifted by {:.0f} month(s)".format(
                year, month, cdi.mean(), expected,
                round((cdi.mean() - expected) / (0.01 * others_share))))


def test_export_is_invariant_to_how_much_history_is_staged(project, tmp_path):
    """The latest month's CDI must not depend on how many months are staged.

    STEP_0100 used to truncate to the last 24 files in `recent` mode, which
    made the analysis basis a function of the export window. This is the
    property the old pipeline violated.
    """
    def value_for(dataset, year, month):
        return float(30 + (month * 2))

    project.stage(months(2024, 1, 24), value_for)
    project.run()
    shallow = project.read_cdi(2025, 12)
    assert shallow is not None

    # Re-stage with five years of the same data ending on the same month.
    for name in DATASETS:
        for path in (tmp_path / "input_data" / name).glob("*.tif"):
            path.unlink()
    project.stage(months(2021, 1, 60), value_for)
    project.run()
    deep = project.read_cdi(2025, 12)
    assert deep is not None

    assert np.array_equal(shallow, deep), (
        "the same month exported differently with 2 vs 5 years staged")


def test_missing_data_propagates_to_the_export(project):
    """A nodata input pixel must reach the GeoTIFF as -9999, not as a value.

    The hub renders negative values as "No Data". Live NDMC data has no gaps
    over Eswatini, so this path is never exercised in production and has to be
    driven synthetically or the assertion passes vacuously.
    """
    period = months(2020, 1, 24)
    hole = (3, 7)

    def value_for(dataset, year, month):
        block = np.full((project.rows, project.cols), 70.0, dtype="float32")
        if dataset == "SPI":
            block[hole] = NODATA
        return block

    project.stage(period, value_for)

    project.run()

    cdi = project.read_cdi(2021, 12)
    assert cdi is not None
    assert cdi[hole] == pytest.approx(MISSING), (
        "nodata became {} instead of {}".format(cdi[hole], MISSING))
    assert cdi[0, 0] > 0.0, "the rest of the raster should be unaffected"


def test_pooled_rank_is_uniform_and_preserves_missing():
    """The pooled rank must restore a uniform scale, which is the whole point.

    A weighted mean of percentiles clusters toward the middle, so the hub's USDM
    thresholds (D4 <=0.02 ... D0 <=0.30) almost never fire on the raw blend.
    Ranking the blend against its own record makes them mean what they were
    designed to mean.
    """
    from STEP_0302_rank_cdi_pooled import pooled_percent_rank

    # One pixel counting up, one counting down, one constant, one all-missing.
    cube = np.empty((10, 2, 2))
    cube[:, 0, 0] = np.arange(10)
    cube[:, 0, 1] = np.arange(10)[::-1]
    cube[:, 1, 0] = 0.5
    cube[:, 1, 1] = -9999.0
    ranked = pooled_percent_rank(cube)

    # Strictly increasing input -> evenly spaced ranks, symmetric about 0.5.
    assert np.allclose(ranked[:, 0, 0], (np.arange(10) + 0.5) / 10)
    # Reversed input -> mirrored ranks.
    assert np.allclose(ranked[:, 0, 1], ranked[::-1, 0, 0])
    # A fully tied pixel sits at the midpoint rather than at an extreme.
    assert np.allclose(ranked[:, 1, 0], 0.5)
    # Missing stays missing rather than becoming a rank of 0.0.
    assert np.all(ranked[:, 1, 1] == -9999.0)

    # Uniformity: every decile bucket gets exactly one of the ten values.
    counts, _ = np.histogram(ranked[:, 0, 0], bins=10, range=(0, 1))
    assert set(counts) == {1}


def test_pooled_mode_exports_a_uniform_scale_end_to_end(project):
    """With cdi_ranking="pooled" the exported CDI spans the full 0-1 range.

    The raw blend concentrates toward the middle, so the hub's USDM thresholds
    (D4 <=0.02 ... D0 <=0.30) almost never fire on it. This asserts the flag
    actually changes what STEP_0303 writes, and that the result reaches the
    extremes the thresholds are defined against.
    """
    period = months(2020, 1, 36)

    # A national wet/dry swing: the blend alone would keep every month inside
    # roughly 0.3-0.7, well clear of any drought band.
    def value_for(dataset, year, month):
        index = (year - 2020) * 12 + month
        return 35.0 + 30.0 * (index % 12) / 11.0

    project.stage(period, value_for)

    project.set_ranking("none")
    project.run()
    blend = np.concatenate([
        project.read_cdi(y, m)[project.read_cdi(y, m) > -999].ravel()
        for y, m in project.exported_months()
    ])

    project.set_ranking("pooled")
    project.run()
    pooled = np.concatenate([
        project.read_cdi(y, m)[project.read_cdi(y, m) > -999].ravel()
        for y, m in project.exported_months()
    ])

    assert blend.min() > 0.30, (
        "fixture is wrong: the raw blend should stay out of every drought band")
    assert pooled.min() <= 0.10, (
        "pooled rank never reaches D2 - the thresholds are still unreachable")
    assert pooled.max() > 0.90, "pooled rank never reaches the wet extreme"
    # A rank is uniform by construction, so it must spread far wider than the
    # mean it was computed from.
    assert pooled.std() > blend.std() * 1.5
