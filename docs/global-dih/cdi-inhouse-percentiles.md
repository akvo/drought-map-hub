# Feature Design Document

## Feature: In-house CDI input percentiles — any-country CDI pipeline

**Task ID**: MC-2
**Author**: Iwan Firmawan (with Claude)
**Date**: 2026-09-30
**Status**: Draft. D-1 and D-2 are decided (2026-09-30), so the spike can start.
**Repo affected**: `drought-map-hub/cdi` (generic hub), after the [CDP-0](1-cdi-data-pipeline/CDP-0_port-eswatini-pipeline.md) port of `eswatini-droughtmap-hub-cdi`. Not this repo. The design lives here because it is the prerequisite of [`multi-country-deployment.md`](multi-country-deployment.md) (MC-1).
**Builds on**: `eswatini-droughtmap-hub-cdi/docs/cdi-scale-fix-requirements.md`, `docs/lst-ndvi-retirement-mail.md`, and the generic hub `akvo/drought-map-hub` (`cdi/`).

---

## 1. Context & Problem Statement

```
Currently:
- The live pipeline never computes a percentile. The steps are:
    STEP_0100  download NDMC percentile GeoTIFF → clip to bbox → ÷100
    STEP_0301  weighted sum
    STEP_0302  pooled rank
    STEP_0303  GeoTIFF export
- NDMC publishes these percentiles for exactly one extent:
  https://droughtcenter.unl.edu/Outgoing/Regional_Percentiles/ lists only
  Southern_Africa (checked 2026-09-30). The grid covers 12–43°E, 18–36°S.
- Any country outside that box cannot get a CDI today.

Goal:
- For any country bbox, produce the same four inputs STEP_0100 produces now:
  output_data/STEP_0100_{ESI,EVI2,SPI,SM}_pct_rank_{region}.nc
  (0–1 percentiles, 0.05° grid, −9999 nodata).
- STEP_0301 → 0303, the GeoNode upload and the hub then run unchanged.
```

### 1.1 Three generations of this pipeline, and what each taught

| Generation | Inputs | Percentiles | What went wrong |
|---|---|---|---|
| **1. Generic hub** (`akvo/drought-map-hub/cdi`, 2025; Kenya and Eswatini) | Raw MODIS LST (MOD21C3), MODIS NDVI (MOD13C2), CHIRPS-2.0 global → SPI, FLDAS SM | In-house: per calendar month over **all years on disk, including the current one**, recomputed on every run | ~100 GB of global rasters downloaded to cut out one country (LST 39 G, NDVI 30 G, CHIRPS 29 G). HDF4→HDF5 through a bundled binary. A `+12` index stride assumed no gaps, while duplicate MODIS granules existed. SM steps were disabled and buggy (unsorted files). Published values drifted because history was re-ranked every run. Then **NDMC retired LST/NDVI** (MODIS end-of-life). |
| **2. Current** (`eswatini-droughtmap-hub-cdi`, 2026) | NDMC percentiles: `era5_esi_1mn`, `evi2_1mn`, `chirps_spi_3mn`, `noah_soilm_1mn` | NDMC's: **40-year rolling histories, true percentiles**, calibrated to 5 km (mail, lines 113–129) | Only Southern Africa. Single source: the 2026 LST feed disruption was exactly this risk. EVI2 had no Jan/Jul/Aug until NDMC re-published all 12 months on 11 Aug 2026; SPI was backfilled to 2012 at the same time (verified 2026-10-06). |
| **3. This design** | Raw ESI/EVI2/SPI/SM sources, **subset at the server** | In-house, against a **stored baseline** | — |

Dead code already in the current repo, to reuse or delete:
- `libs/spi_calculations.py`: a gamma/Thom SPI. It is not called.
- `STEP_0104` / `STEP_0204`: FLDAS SM steps. They are broken, with `KeyError`s on removed config keys.
- `libs/hdf_functions.py` and `h4toh5convert`: not referenced anywhere.
- `libs/statistics_operations.rank_parameter`: the rank tops out at (N−1)/N, and the divisor is wrong when the maximum is tied.

### 1.2 Access facts measured on 2026-09-30

| Check | Result |
|---|---|
| Earthdata Login (hub `.env` `EARTHDATA_USERNAME/PASSWORD`) → LP DAAC `VNP13A3.002` | ✅ 206, real HDF5 bytes |
| Same login → GES DISC `FLDAS_NOAH01_C_GL_M.001` (HTTPS archive) | ✅ 206, real HDF5 bytes |
| GES DISC **on-prem** OPeNDAP `hydro1.gesdisc.eosdis.nasa.gov/opendap` (generation 1 used `hydro1…/data`) | ❌ **410 Service Retired**. The replacement is Earthdata Cloud OPeNDAP. |
| **Cloud OPeNDAP** `opendap.earthdata.nasa.gov/collections/C1563089663-GES_DISC/granules/…` with a DAP4 constraint | ✅ bbox subset of 2 variables = **45 KB** for one month (the global grid is 3600×1500 at 0.1°) |
| FLDAS global variables | `SoilMoi00_10cm/10_40/40_100/100_200_tavg`, `Evap_tavg`, `Rainf_f_tavg`, … **no `PotEvap_tavg`**. FLDAS global alone therefore cannot give an ET/PET ESI. |
| Copernicus CDS | ✅ already used by the hub (`cdsapi==0.7.7`, `ECMWF_API_KEY`, `fetch_agera5_observations`). The **ERA5-Land licence has not been accepted yet** on that account. |
| CMR catalogue start dates | CHIRPS 1981 · ERA5-Land 1950 · FLDAS global 1982 · MOD13A3 2000-02 · **VNP13A3 2012-01** · VJ113A3 (NOAA-20) 2018-01 · VJ213A3 (NOAA-21) 2023-02 |
| **Suomi-NPP end of delivery** | NASA stops delivering all Suomi-NPP science data, **VNP13A3 included, on 1 Nov 2026**. NASA's recommended successors are VJ213A3 (first choice), then VJ113A3 ([notice](https://www.earthdata.nasa.gov/data/alerts-outages/suomi-npp-data-product-delivery-cease-november-1-2026)). |
| VNP13A3 EVI2 layer | `1 km monthly EVI2` under `/HDFEOS/GRIDS/NPP_Grid_monthly_VI_1km/Data Fields/`, scaled ×10000, fill −15000. Eswatini is covered by one tile, h20v11, which is 27.6 MB per month. |

### 1.2b Pacific fitness check — Marshall Islands and Fiji (measured 2026-10-06)

Do the four CDI sources actually have data over small and scattered islands? Each source was read over the islands themselves, using August 2026 for FLDAS and CHIRPS.

| Source → CDI input | Marshall Islands (Majuro, Kwajalein atolls) | Fiji (Viti Levu / Vanua Levu; Lau group east of 180°) |
|---|---|---|
| CHIRPS 0.05° → **SPI** | ✅ The atolls are kept in the land mask: Majuro has 26/45 valid cells, and the whole RMI box (160–173°E, 4–15°N) has 853 valid cells. Open ocean is −9999. Over atolls the values are mostly satellite plus climatology, because there are very few gauges. | ✅ 482/600 cells on Viti Levu; 142 cells across 180° |
| FLDAS 0.1° → **SM** | ❌ **0 land cells**: Majuro 0/216, Kwajalein 0/285. The atolls are ocean in its land mask. | ✅ 140 cells west of 180°. ⚠️ Lau group: 2 cells. |
| ERA5-Land 0.1° → **ESI** | ❌ *Inferred, not measured.* It is a 0.1° land-only model like FLDAS, so atolls are expected to be absent. | ✅ expected on the main islands |
| VIIRS 1 km → **EVI2** | ⚠️ The tiles exist (h34v08, h35v08), but atoll islets are a few hundred metres wide, so a 1 km pixel is mostly lagoon or sea. *Pixel values are not checked yet.* | ✅ tiles h34v10, h35v10 |

**Reading:**
- **Fiji: the CDI is technically feasible** on the main islands. The outer islands are thin, and Lau has almost no SM.
  - Fiji **crosses the antimeridian** (177°E → 178°W). `config_reader` builds the grid as `w_lon → e_lon` and STEP_0100 reads one raster window, so both break when `w_lon > e_lon`. The fix is a 0–360° longitude grid, or reading two windows and joining them.
- **Marshall Islands: a 4-input CDI is not fit.** Only rainfall exists, which means SM and ESI are absent. EVI2 over atolls is also scientifically weak: coconut cover on coral sand responds to the freshwater lens, not to soil moisture.
  - The honest product there is **rainfall-only (SPI)**. The pipeline already supports this through weights `spi: 1.0` and others `0`, but it must not be labelled a *combined* indicator.
  - Local rain gauges from the RMI Weather Service matter more than satellites here.
- **Admin aggregation**: atoll and municipality polygons are far smaller than a 0.05° cell (~30 km²). Zonal statistics must use `all_touched=True`, otherwise most units come back null; the same failure happened for CHIRPS normals in Eswatini.

### 1.3 What NDMC's published files reveal (inferred from the rasters; NDMC has not published the method)

- **ESI** values stop exactly at 0.135 and 99.865, which is 100·Φ(±3). This suggests NDMC standardises to a z-score, clips it at ±3, and converts with the normal CDF. None of the other three layers is clipped.
- Each NDMC map has about 106k distinct values. That is not what a per-pixel rank over a short history would produce, so NDMC most likely uses **parametric (Gaussian) percentiles**. NDMC's US blends document exactly that ("Gaussian percentiles associated with a standardized distribution", [ndmcblends.unl.edu](https://ndmcblends.unl.edu/Metadata.aspx)).
- **SM** values span the full 0–100 range. The name and the "100 cm" wording in the email suggest FLDAS Noah 0–100 cm, which is the same `RootZone2` weighting (0.1/0.3/0.6) as NDMC's old toolkit `STEP_0104`.
- **"Pooled ranking" (STEP_0302) is Akvo's own step**, not NDMC's. The D0–D4 cutoffs (30/20/10/5/2) are also the hub's own, following the US Drought Monitor, and appear nowhere in NDMC code.

---

## 2. Requirements

### User Acceptance Criteria
- [ ] Setting a new bbox (and a `region_name`) in `cdi_project_settings.conf` produces monthly CDI GeoTIFFs for that country, with no NDMC files involved.
- [ ] Re-running the pipeline for a past month gives the same values. Published values do not drift.
- [ ] For Eswatini, the in-house CDI class (D0–D4) agrees with the NDMC-based CDI class on at least the threshold agreed in OQ-3, per pixel over the overlap period.

### Technical Acceptance Criteria
- [ ] Raw inputs are fetched **as a bbox subset at the server** (OPeNDAP, CDS `area`, or tile selection), never as global files.
- [ ] Only the months that are missing are downloaded. Gaps anywhere in the history are filled, not just the last month.
- [ ] Each parameter's baseline window is fixed and stored. It is recorded in the NetCDF attributes (`baseline_start`, `baseline_end`, `n_years`).
- [ ] Ranking is vectorised (numpy) and handles gaps by date, never by an index stride.
- [ ] `percentile_source` is `ndmc` or `inhouse`, and the default stays `ndmc`. Eswatini production is unchanged until the spike is signed off.
- [ ] Pytest covers ranking edge cases (ties, gaps, all-missing pixel), SPI against a published reference series, and the subset-to-grid alignment.

---

## 3. Data Model Changes

There are no hub DB changes. The pipeline's file contracts are listed below.

### New config keys (`cdi_project_settings.conf`)

```json
{
  "percentile_source": "inhouse",
  "baseline": { "years": 40, "end_year": 2025 },
  "sources": {
    "spi":  { "provider": "chirps",  "product": "CHIRPS-2.0 global_monthly", "accumulation": 3 },
    "esi":  { "provider": "cds",     "product": "reanalysis-era5-land-monthly-means" },
    "sm":   { "provider": "opendap", "product": "FLDAS_NOAH01_C_GL_M.001", "layer": "0-100cm" },
    "evi2": { "provider": "lpdaac",  "product": ["VNP13A3.002", "VJ113A3.002"] }
  }
}
```

### New working files

```
input_data/raw/{SPI,ESI,SM,EVI2}/{param}_{region}_{YYYYMM}.nc   # bbox subset, native grid
working_data/baseline/{param}_{region}_baseline.nc              # sorted baseline sample per pixel per calendar month
output_data/STEP_0100_{PARAM}_pct_rank_{region}.nc              # UNCHANGED contract: what 0301 already reads
```

### Migration Strategy

```
- ndmc mode keeps today's code path byte-for-byte.
- inhouse mode is a new STEP_0100 variant, STEP_0110_compute_inhouse_percentiles.py.
  It writes the same output file and variable names (esi_pct_rank, …).
- Rollback: set percentile_source back to ndmc.
```

---

## 4. API Contract

### 4.1 Step chain (inhouse mode)

```
job_01  fetch_raw.py <param>     one adapter per provider: chirps | cds | opendap | lpdaac
                                 subset to bbox + 0.5° margin; skip months already on disk
STEP_0110a  regrid → 0.05° config grid       (bilinear for 0.1° FLDAS/ERA5-Land; mean for 1 km VIIRS)
STEP_0110b  derive the index
              SPI  = gamma fit per calendar month on baseline 3-month totals → z = SPI
              ESI  = ET/PET ratio (ERA5-Land e / pev) → z per calendar month      (see D-4)
              SM   = depth-weighted 0–100 cm (0.1·L1 + 0.3·L2 + 0.6·L3, as in STEP_0104) → z
              EVI2 = VIIRS `1 km monthly EVI2`, QC-masked, VNP13A3 until 2026-10 then VJ113A3 → z
STEP_0110c  Gaussian percentile against the stored baseline (per pixel, per calendar month)   (see D-6)
              p = Φ(clip(z, −3, 3))
              z = (x − μ_month) / σ_month over the baseline (SPI: the gamma-derived SPI itself)
            → output_data/STEP_0100_{PARAM}_pct_rank_{region}.nc
            The spike also computes the empirical mid-rank
              (count(baseline < x) + 0.5·count(baseline == x)) / n
            so the two can be compared.
STEP_0301 → 0302 → 0303 → upload → sync        UNCHANGED
```

### 4.2 Provider adapters

| Provider | Access | Auth | Subset method |
|---|---|---|---|
| `chirps` | `data.chc.ucsb.edu/products/CHIRPS-2.0/global_monthly/tifs/` (the hub already uses CHIRPS in `fetch_chirps_observations`) | none | rasterio windowed read of the COG or tif (`/vsicurl/`) |
| `cds` | `cdsapi` → `reanalysis-era5-land-monthly-means`, variables `total_evaporation`, `potential_evaporation` | `ECMWF_API_KEY` (move to the pipeline `.env`) | request `area=[N,W,S,E]` |
| `opendap` | Earthdata Cloud OPeNDAP, DAP4 constraint expression | `EARTHDATA_USERNAME/PASSWORD` via netrc + cookie jar | index-range constraint (measured: 45 KB/month) |
| `lpdaac` | `data.lpdaac.earthdatacloud.nasa.gov` via a CMR granule search with `bounding_box` | same | tile selection (sinusoidal h/v tiles), then reproject |

The login model changes from generation 1's daily `wget` cookie refresh against a MERRA2 file to one netrc plus a cookie jar per run. `requests` + `netrc` are enough; no new dependency is needed.

---

## 5. Decision Log

### D-1: Path to any-country CDI — ask NDMC, build in-house, or both *(needs decision)*
**Options**:
1. **A. Ask NDMC to export more regions.** NDMC already processes global sources on a dedicated server (mail, line 113), and `Southern_Africa` is only the export they set up for us. This is the same logic as REQ-4 in `cdi-scale-fix-requirements.md`: ask for an export, not a reprocessing.
2. **B. Compute in-house** (this doc).
3. **A then B.** Send the email now. Run the B spike in parallel as the independence path.

**Decision** (Iwan, 2026-09-30, sequence revised 2026-10-06): **ask NDMC for the method → compute in-house → NDMC validates.**
- First, ask NDMC how they compute each index, so the initial development follows their expert knowledge instead of what we inferred from their published files (§1.3, D-4, D-6 stay assumptions until they answer).
- Then compute the percentiles in-house.
- Then take the results back to NDMC for review.

**Rationale**:
- The business requirement is *every* country, so independence is the goal. A single volunteer-scale source has already failed once (the 2026 LST disruption).
- Our first validation does not need NDMC: their Eswatini output is already our reference (§9).
- Arriving with concrete numbers ("our Eswatini CDI matches yours X%; here is where it differs") is a smaller and clearer ask of NDMC than an open-ended request.

**Safeguard** (superseded on 2026-10-06, because the method email now goes first): ESI gets a **timebox**. NDMC's ESI formula is not public (D-4). If the spike's ESI does not reach agreement within the timebox, the ESI method question goes to NDMC early instead of waiting for the full validation email.

**Impact**:
- The path-A "export more regions" request is dropped from the plan.
- §11 production tasks 5–7 follow a passed spike directly. They no longer wait for NDMC's answer.

### D-2: Baseline window — follow NDMC's 40-year rolling window where the data allows *(DECIDED 2026-09-30: per-component, 40 yrs for SPI/ESI/SM, 14 yrs for EVI2)*
The brainstorm decision "baseline = all data from 2012" was based on the NDMC file listing. The NDMC mail shows that 2012 is only the **export** window. NDMC ranks against **40-year rolling histories**. Following NDMC therefore means:

| Param | Source start | 40-year window possible? |
|---|---|---|
| SPI | CHIRPS 1981 | ✅ 1986–2025 |
| ESI | ERA5-Land 1950 | ✅ 1986–2025 |
| SM | FLDAS 1982 | ✅ 1986–2025 |
| EVI2 | VNP13A3 2012 → ends 2026-10; VJ113A3 2018 → ongoing (MOD13A3 2000) | ❌ 14 years (26 with MODIS stitched) |

**Decision** (Iwan, 2026-09-30): `baseline.years = 40`, capped at what each source has. So SPI, ESI and SM use 40 years and EVI2 uses 14.
- Rejected: a uniform 14 years for everything. It lowers the quality of three components for no gain.
- Deferred: stitching MODIS onto EVI2 (~26 years). It is revisited only if the spike shows EVI2 is the component that disagrees.
- EVI2 is one **VIIRS series**: VNP13A3 (Suomi-NPP) 2012 → Oct 2026, then VJ113A3 (NOAA-20). It is the same instrument type on sister satellites.
- The spike checks the two sensors over their 2018–2026 overlap. If they are biased against each other, it applies a per-pixel, per-calendar-month offset.
- Stitching MODIS, or asking NDMC about its "modelled backups", is considered only if EVI2 turns out to be the component that disagrees.

**Impact**: EVI2 has a 14-year sample against 40 for the others. With Gaussian percentiles (D-6), the values stay continuous rather than coming in 1/14 steps, but the estimates of μ and σ are noisier. This is the known quality gap of path B.

**Deadline**: VNP13A3 stops on **1 Nov 2026**. Any EVI2 adapter must handle the switch to VJ113A3 from day one.

### D-3: Rank new months against a stored baseline, refreshed once a year
**Options**:
1. Re-rank all history every run (generation 1).
2. Keep a stored baseline sample and rank only the new month against it, then roll the window forward once a year.

**Decision**: 2.

**Rationale**:
- Option 1 changed already-published values and recomputed hours of history for one new month.
- Option 2 is reproducible, since a past month re-runs identically within one baseline vintage, and it is cheap: one month's work per run.

**Impact**: the yearly baseline refresh is an explicit, logged job (`--rebuild-baseline`). Publications record the baseline vintage.

### D-4: ESI definition *(verify first in the spike)*
- NDMC names the file `era5_esi` and says ESI is available "from both FLDAS and ERA".
- FLDAS global has no PET variable (measured, §1.2), so the ERA5-Land route is the only one open to us.
- NDMC's ERA5 ESI formula is **not public**: there is no readme, repo or paper for it.
- **Assumed**: ESI = the ET/PET ratio, standardised per calendar month, clipped at ±3σ, then Φ. The clipping comes from the published raster values (§1.3).
- **Known variable traps** (ECMWF documentation):
  - Since Nov 2021, ERA5-Land `pev` is **open-water (pan) evaporation** and "can give unrealistic results in arid conditions".
  - Plain ERA5 `pev` is underestimated over deserts and forests because of a known bug.
  - ERA5-Land `evavt` actually holds the open-water numbers (the evabs/evaow/evavt values are swapped).
  - Monthly means are per-day values, and negative values mean evaporation.
- ESI is therefore the component most likely to disagree with NDMC, and the spike measures it first.

**Fallbacks**, in order:
1. Ask NDMC for their ESI formula and variables. The mail offered code snippets, and this question belongs in the D-1 email.
2. ERA5 single-levels `e`/`pev`.
3. Drop ESI to weight 0 and re-weight. The pipeline already skips weight-0 inputs.

### D-5: Keep the 0.05° grid and the STEP_0100 output contract
**Decision**: everything is regridded to the config grid that `config_reader` already builds, and written under the existing variable names.

**Rationale**: STEP_0301 → hub is tested and in production. Changing the contract would widen the blast radius for no gain.

**Also**: port the generic hub's bbox → cell-centre snapping (`v1_setup/views.py:294-329`) into a `snap_bounds.py` helper, so a new country's bounds always land on 0.05° centres.

### D-6: Gaussian percentiles, not empirical rank
**Options**:
1. Empirical per-pixel rank. This is what the old toolkit and the generic hub did: `statistics_operations.py:85-122`.
2. Parametric: standardise to z against the baseline month, then take Φ(z).

**Decision**: 2. The spike reports option 1 alongside it.

**Rationale**:
- NDMC's published maps look parametric (§1.3). Following NDMC means following that.
- With EVI2's 14-year sample, an empirical rank can only produce 15 distinct values per pixel and month. Φ(z) produces continuous values.
- Clipping at ±3 matches what NDMC's ESI shows.

**Impact**: `rank_parameter` and its (N−1)/N ceiling bug are retired rather than fixed.

### D-7: Per-country product profile — the full CDI where the data supports it, SPI-only where it does not
**Decision** (proposed): every country config declares which inputs it has, through the existing weights. A deployment whose weights leave only SPI publishes the result as a **rainfall drought index**, not a "CDI". MC-1 then labels the map accordingly.

**Rationale**: §1.2b measured that small atoll states have no SM or ESI data at all. Blending in nodata, or reporting a "combined" index made from one input, would mislead users.

**Impact**:
- Antimeridian-safe bounds handling is required before Fiji (or any country crossing 180°) can run.
- `all_touched=True` aggregation is required for small-island admin units.

---

## 6. Type/Constant Mappings

| CDI param | Variable in STEP_0100 `.nc` | Weight (Eswatini) | In-house source | Baseline |
|---|---|---|---|---|
| ESI | `esi_pct_rank` | 0.3 | ERA5-Land `e`/`pev` | 40 yrs |
| EVI2 | `evi2_pct_rank` | 0.3 | VIIRS EVI2 (VNP13A3 → VJ113A3) | 14 yrs (2012–2025) |
| SPI | `spi_pct_rank` | 0.3 | CHIRPS-2.0, 3-month | 40 yrs |
| SM | `sm_pct_rank` | 0.1 | FLDAS 0–100 cm | 40 yrs |

The D-class thresholds and the per-admin aggregation stay in the hub, unchanged.

---

## 7. Compatibility & Migration

### Backward Compatibility
- [ ] `percentile_source` defaults to `ndmc`, so the Eswatini production cron is untouched.
- [ ] GeoTIFF names, GeoNode categories and the hub sync are unchanged.
- [ ] `ECMWF_API_KEY` and `EARTHDATA_*` are added to the pipeline `env.example`. Today they exist only in the hub `.env`.

### Seeder/CLI Compatibility
- [ ] `job.sh all|recent` keeps working in both modes.
- [ ] New flags: `--rebuild-baseline` and `--compare-ndmc` (the spike's validation report).
- [ ] Delete the dead code listed in §1.1 once 0110 supersedes it.

---

## 8. Security Considerations

- [ ] Earthdata credentials are passed only through a temporary netrc with mode 600, deleted after the run. They are never put on the command line (visible in `ps`) and never logged. Generation 1 used `wget --user --password` on the command line.
- [ ] The CDS key is read from the environment. `cdsapi` output is muted, following the hub's `fetch_agera5_observations`.
- [ ] Downloads are only over HTTPS from the four known hosts, with no redirects to other hosts except `urs.earthdata.nasa.gov`.

---

## 9. Testing Strategy

| Test Type | Coverage |
|---|---|
| Unit | Mid-rank with ties, gaps, all-missing pixel, n=1. SPI against a reference series (e.g. the `climate-indices` package output for one CHIRPS pixel). Φ(SPI) is monotone. Depth weighting. Bounds snapping. |
| Integration | Synthetic raw NetCDFs through 0110 → 0301 → 0303, reusing `test_cdi_pipeline.py` fixtures. The output must match the ndmc-mode contract (names, dims, −9999). |
| Validation (spike) | Eswatini, overlap period 2012–2026 (all four NDMC inputs now start in 2012), in-house vs NDMC, per param and for the CDI. Report: Pearson r, mean bias, and D-class confusion matrix per month. **Never compare against the GeoTIFF archive and GeoNode together: they are different vintages.** |

---

## 10. Open Questions

- [x] **OQ-1 (D-1)**: Who sends the validation email to NDMC (contacts held privately) after the spike? The relationship runs through the Akvo leads. The email attaches the §9 comparison report and asks:
  1. Does our method match yours? In particular: the ERA5 ESI formula and variables; Gaussian vs empirical percentiles; the baseline years.
  2. How do you reach 40 years for EVI2 (the "modelled backups")? The Jan/Jul/Aug gap is closed since 11 Aug 2026.
  3. Do you see any concern with the differences shown in the report?

  **— RESOLVED 2026-10-12: Iwan owns and sends this correspondence directly. The methodology email (2026-10-06) and follow-up (2026-10-12) are already sent; no reply yet.**
- [ ] **OQ-7 (D-7)**: Pacific.
  - Is a satellite drought classification fit for purpose in small island states? Ask NDMC (added to the method email) and the national met services (Fiji Met Service; the RMI Weather Service Office).
  - For the Marshall Islands, would partners accept a rainfall-only product?
  - Do station gauges exist that could feed SPI directly?

  **— PENDING external (Fiji Met Service / RMI Weather Service + NDMC). Working default: adopt the D-7 SPI-only "rainfall drought index" profile for atoll states; the fitness and gauge questions go to the national met services alongside the NDMC method email.**
- [x] **OQ-1b**: How long is the ESI timebox before the ESI question goes to NDMC early? Proposed: 3 working days. **— N/A 2026-10-12: superseded; the ESI method question is already in the methodology email, which goes first (D-1), so there is no separate timebox.**
- [x] **OQ-2 (D-2)**: ~~Confirm the 40-year baseline with EVI2 as the 14-year exception~~. Confirmed on 2026-09-30; this replaces the earlier "from 2012" decision.
- [x] **OQ-3**: What D-class agreement makes the spike a pass? Proposed: ≥ 80% of admin units in the same class, and none more than one class apart. **— RESOLVED 2026-10-12: adopt the proposed threshold as the working pass criterion; TWG/NDRMA confirm (= CDP-5 OQ-1).**
- [x] **OQ-4**: Accept the ERA5-Land licence on the CDS account that owns `ECMWF_API_KEY`. **— RESOLVED 2026-10-12: accept the licence now on that CDS account (= CDP-1 OQ-3).**
- [x] **OQ-5**: Where does the pipeline run for a second country: the same VM with a second config, or one VM per country? Disk is now small (bbox subsets), so one VM should be enough. **— RESOLVED 2026-10-12: one VM, one config per country.**
- [ ] **OQ-6**: CHIRPS-2.0 vs CHIRPS-3.0. NDMC mentions "CHIRPS3". The hub is still on 2.0, and switching must move the normals too. **— PENDING NDMC (Q5); working default: stay on CHIRPS-2.0.**

---

## 11. Work Breakdown

**Spike** (Eswatini only; answers D-1/D-2/D-4 with numbers):

| # | Task | Size |
|---|---|---|
| 1 | Provider adapters with bbox subsetting: `chirps`, `cds`, `opendap`, `lpdaac` + netrc/cookie auth | M |
| 2 | Regrid + index derivation (SPI, ESI, SM, EVI2) on the 0.05° grid | M |
| 3 | Vectorised baseline + Gaussian percentile (and mid-rank for comparison), replacing `rank_parameter`, with unit tests; VNP13A3/VJ113A3 overlap check | S |
| 4 | `--compare-ndmc` validation report for Eswatini 2012–2026 | S |

| 4b | NDMC validation email with the §9 report attached (OQ-1) | S |

**Production** (only if the spike passes):

| # | Task | Size |
|---|---|---|
| 5 | `percentile_source` switch in `job.sh` / `STEP_0000`; incremental missing-month fetch | S |
| 6 | Yearly `--rebuild-baseline` job + baseline vintage in NetCDF/GeoTIFF metadata | S |
| 7 | `snap_bounds.py` + new-country onboarding runbook; delete dead code | S |

---

## 12. References

- NDMC mail thread: `eswatini-droughtmap-hub-cdi/docs/lst-ndvi-retirement-mail.md` (lines 89–131: options and 40-year windows; line 440: nodata −1.0)
- `eswatini-droughtmap-hub-cdi/docs/cdi-scale-fix-requirements.md` §3 (REQ-4: export-window request, not reprocessing)
- Generic hub raw pipeline: `akvo/drought-map-hub` `cdi/src/cdi-scripts/` (STEP_0101–0303, `libs/spi_calculations.py`, `libs/statistics_operations.py:85-122`)
- Suomi-NPP delivery ends 1 Nov 2026: https://www.earthdata.nasa.gov/data/alerts-outages/suomi-npp-data-product-delivery-cease-november-1-2026
- ERA5-Land variable caveats: https://confluence.ecmwf.int/display/CKB/ERA5-Land%3A+data+documentation · ERA5 PET issue: https://forum.ecmwf.int/t/confluence-page-on-the-problems-of-the-potential-evapotranspiration-product-in-era5/2491
- NDMC old CDI toolkit: https://droughtcenter.unl.edu/Outgoing/CDI/software/scripts/scripts_update.zip · Harmony subsetting: https://harmony.earthdata.nasa.gov
- GES DISC on-prem OPeNDAP retirement → Cloud OPeNDAP: https://disc.gsfc.nasa.gov/information/tools?title=OPeNDAP%20In%20The%20Cloud
- Hub memory notes: CHIRPS v3 monthly is mm not SPI; GeoTIFF archive ≠ GeoNode vintage; Earth Engine not available to DIH

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | | | |
| Tech Lead | | | |
| Product | | | |
