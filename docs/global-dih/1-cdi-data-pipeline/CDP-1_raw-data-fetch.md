# Feature Design Document

## Feature: Raw data fetch adapters — CHIRPS, ERA5-Land, FLDAS, VIIRS (bbox subset at the source)

**Task ID**: CDP-1 (sub-task of [MC-2](cdi-inhouse-percentiles.md))
**Author**: Iwan Firmawan (with Claude)
**Date**: 2026-10-12
**Status**: Draft
**Repo affected**: `drought-map-hub` → `cdi/` (after the [CDP-0](CDP-0_port-eswatini-pipeline.md) port; file/line refs to existing code point at the `eswatini-droughtmap-hub-cdi` source until then)

---

## 1. Context & Problem Statement

```
Currently:
- job_01 crawls NDMC's directory listing and wgets ready-made percentile
  GeoTIFFs (utils.sh:308 check_and_create_download_log_ndmc).
- No raw source is fetched at all.
- The previous generation (akvo/drought-map-hub) did fetch raw data, and hit
  four problems:
    - it downloaded ~100 GB of global files to cut out one country;
    - it used GES DISC's on-prem OPeNDAP (hydro1), which now answers
      410 Service Retired;
    - its CHIRPS gap-fill only fetched the LAST missing month;
    - it passed the Earthdata password on the wget command line.

Goal:
- One Python entry point that fetches, for any bbox and month range, the raw
  monthly fields needed by the four CDI inputs.
- Each request is subset at the source, so we only transfer the country.
- Any missing month anywhere in a 40-year history is filled.
- Credentials never appear in argv or logs.
```

**Measured facts this design relies on:**

| Source | Access path | Measured |
|---|---|---|
| CHIRPS-2.0 monthly | `data.chc.ucsb.edu/products/CHIRPS-2.0/global_monthly/cogs/chirps-v2.0.YYYY.MM.cog` | A windowed `/vsicurl/` read of Eswatini returns 44×44 cells directly (2026-10-12). The 40 −9999 cells are Maputo Bay, which is ocean. No full download is needed. |
| FLDAS Noah global | Earthdata Cloud OPeNDAP, `opendap.earthdata.nasa.gov/collections/C1563089663-GES_DISC/granules/FLDAS_NOAH01_C_GL_M.001:FLDAS_NOAH01_C_GL_M.AYYYYMM.001.nc.dap.nc4?dap4.ce=…` | A 2-variable bbox subset is **45 KB** per month (2026-09-30). The on-prem `hydro1` server returns **410**. |
| ERA5-Land monthly | CDS `reanalysis-era5-land-monthly-means`, `area=[N,W,S,E]` | The hub already uses `cdsapi` with `ECMWF_API_KEY`. The **ERA5-Land licence is not accepted yet.** |
| VIIRS EVI2 | LP DAAC Cloud: VNP13A3.002 (Suomi-NPP, **ends 1 Nov 2026**), then VJ113A3.002 (NOAA-20, from 2018) | Earthdata login returned 206 with real HDF5. Eswatini fits in one tile, h20v11, at 27.6 MB per month. |

---

## 2. Requirements

### User Acceptance Criteria
- [ ] An operator can run `python fetch_raw.py --param spi --from 1986-01 --to 2026-09` for the configured bbox and get one file per month.
- [ ] Running the same command again downloads nothing if every month is already on disk.
- [ ] Deleting any single month in the middle of the history and re-running fetches exactly that month.

### Technical Acceptance Criteria
- [ ] CHIRPS, FLDAS and ERA5-Land are fetched as **bbox subsets at the source**, with no global files.
- [ ] VIIRS is fetched by tile. Only the EVI2 and QC layers are kept, and the raw tile is deleted after extraction.
- [ ] The bbox is padded by 0.5° on each side so that CDP-2's regridding has neighbours at the edges.
- [ ] Writes are atomic: download to `*.tmp`, validate it opens, then rename.
- [ ] Failed requests retry 3 times with exponential backoff. A month that still fails is listed in the run summary, and the run exits non-zero.
- [ ] The EVI2 sensor is chosen by date: VNP13A3 up to and including 2026-10, and VJ113A3 after that. For the 2018-01 → 2026-10 overlap, **both** sensors are fetched so CDP-3 can measure the bias between them.
- [ ] A bbox that crosses the antimeridian (`w_lon > e_lon`, e.g. Fiji) is split into two requests and joined. This uses CDP-2's `split_bounds()`.
- [ ] A full 40-year Eswatini fetch of SPI, SM and ESI, plus 14 years of EVI2, transfers less than 6 GB, nearly all of it VIIRS tiles.

---

## 3. Data Model Changes

There are no hub database changes. These are the file and config contracts.

### New config block (`cdi_project_settings.conf`)

```json
"sources": {
  "spi":  { "provider": "chirps",  "product": "CHIRPS-2.0", "variable": "precip" },
  "sm":   { "provider": "opendap", "product": "FLDAS_NOAH01_C_GL_M.001",
            "variables": ["SoilMoi00_10cm_tavg", "SoilMoi10_40cm_tavg", "SoilMoi40_100cm_tavg"] },
  "esi":  { "provider": "cds",     "product": "reanalysis-era5-land-monthly-means",
            "variables": ["total_evaporation", "potential_evaporation"] },
  "evi2": { "provider": "lpdaac",  "products": [
              { "short_name": "VNP13A3", "version": "002", "until": "2026-10" },
              { "short_name": "VJ113A3", "version": "002", "from":  "2018-01" } ] }
}
```

### New files

```
input_data/raw/{SPI,SM,ESI,EVI2}/{param}_{region}_{YYYYMM}[_{sensor}].nc
    native grid, bbox + 0.5° margin
    attrs: source_product, source_granule, fetched_at, bbox
input_data/raw/fetch_log.json
    per param: months present, last run, failures
```

### Migration Strategy

```
- Additive only. NDMC mode (input_data/{ESI,EVI2,SPI,SM}/*.tif) is untouched.
- Rollback: delete input_data/raw/.
```

---

## 4. API Contract

### CLI

```bash
python cdi/src/cdi-scripts/fetch_raw.py --param {spi|sm|esi|evi2|all} \
       --from YYYY-MM --to YYYY-MM [--force] [--dry-run]
# exit 0 = all months present; exit 1 = one or more months failed (listed)
```

### Provider functions (one module, a plain dict, no registry class)

```python
def fetch_month(param: str, month: date, bbox: Bounds, out: Path) -> Path: ...

PROVIDERS = {
    "chirps":  fetch_chirps_cog,      # rasterio /vsicurl/ windowed read
    "opendap": fetch_fldas_opendap,   # DAP4 index-range constraint
    "cds":     fetch_era5land_cds,    # cdsapi, one request per YEAR (12 months)
    "lpdaac":  fetch_viirs_tiles,     # CMR granule search (bbox+temporal) → tile download
}
```

---

## 5. Decision Log

### D-1: Subset at the source, never download global files
**Options**:
1. Download global files and clip locally, as generation 1 did.
2. Subset at the source with COG windows, OPeNDAP or the CDS `area` parameter.

**Decision**: 2. VIIRS is the exception: it is fetched as one tile and pruned to the EVI2 and QC layers.

**Rationale**:
- Measured: 45 KB per month (FLDAS) vs ~121 MB per global file.
- CHIRPS needs no download at all.
- This removes the ~100 GB disk problem of generation 1.

**Impact**: the pipeline VM needs very little disk. A country's 40-year history becomes realistic.

### D-2: Python `requests` + temporary netrc instead of shell `wget`
**Decision**: all four providers are Python. Earthdata auth writes a mode-600 netrc and a cookie jar to a temp directory, both deleted at exit.

**Rationale**:
- Generation 1 passed `wget --user --password` on the command line, where `ps` exposes it.
- `requests` is already a dependency of `background-job`.

### D-3: One CDS request per year, not per month
**Rationale**: the CDS queues every request, so 12× fewer requests means far less waiting. A year of ERA5-Land monthly means over one country is small.

### D-4: Fetch both VIIRS sensors during their overlap
**Rationale**:
- VNP13A3 stops on 1 Nov 2026.
- The EVI2 baseline (2012 →) must splice onto VJ113A3. Without the 2018–2026 overlap there is no way to measure a sensor bias.

---

## 6. Type/Constant Mappings

| CDI input | Provider | Product | Variables fetched | History |
|---|---|---|---|---|
| SPI | `chirps` | CHIRPS-2.0 monthly COG | precip (mm) | 1981 → |
| SM | `opendap` | FLDAS_NOAH01_C_GL_M.001 | SoilMoi 0–10, 10–40, 40–100 cm | 1982 → |
| ESI | `cds` | ERA5-Land monthly means | total_evaporation, potential_evaporation | 1950 → |
| EVI2 | `lpdaac` | VNP13A3.002 → VJ113A3.002 | `1 km monthly EVI2` + pixel reliability | 2012 → / 2018 → |

---

## 7. Compatibility & Migration

### Backward Compatibility
- [ ] The NDMC download path (`job_01_check-dataset.sh`) is unchanged.
- [ ] `ECMWF_API_KEY`, `EARTHDATA_USERNAME` and `EARTHDATA_PASSWORD` are added to the pipeline's `env.example`. Today they exist only in the hub's `.env`.
- [ ] `cdsapi` is added to `cdi-scripts/requirements.txt`. No other new dependency is needed.

### Seeder/CLI Compatibility
- [ ] New CLI: `fetch_raw.py`. `job.sh` calls it only in `inhouse` mode (CDP-6).

---

## 8. Security Considerations

- [ ] Credentials come from the environment only. The netrc is mode 600 in a temp dir, removed in a `finally` block.
- [ ] They are never passed on argv and never logged. `cdsapi` logging is muted, as in the hub's `fetch_agera5_observations`.
- [ ] Hosts are allow-listed: `data.chc.ucsb.edu`, `opendap.earthdata.nasa.gov`, `data.lpdaac.earthdatacloud.nasa.gov`, `cmr.earthdata.nasa.gov`, `urs.earthdata.nasa.gov`, `cds.climate.copernicus.eu`. Redirects to any other host are refused.

---

## 9. Testing Strategy

| Test Type | Coverage |
|---|---|
| Unit | Missing-month detection (gaps at the start, middle and end); bbox padding; antimeridian split; sensor selection by date; atomic write leaves no partial file on failure. HTTP is mocked by monkeypatching `requests.Session`. |
| Integration | One month per provider against a tiny fixture bbox, marked `@pytest.mark.network`. These run locally but are skipped in CI. |
| Manual | A full Eswatini fetch 1986 → 2026. Record transfer size and duration in the PR. |

---

## 10. Open Questions

- [ ] **OQ-1**: ERA5 or ERA5-Land? ERA5-Land `pev` is pan evaporation since Nov 2021. **— PENDING: NDMC to confirm ERA5 vs ERA5-Land; working default: ERA5-Land.**
- [ ] **OQ-2**: CHIRPS-2.0 or 3.0? The hub's normals are on 2.0. **— PENDING: NDMC to confirm the CHIRPS version; working default: CHIRPS-2.0.**
- [x] **OQ-3**: Who accepts the ERA5-Land licence on the CDS account behind `ECMWF_API_KEY`? **— RESOLVED 2026-10-12: Iwan accepts the licence now, on the CDS account behind `ECMWF_API_KEY`.**
- [x] **OQ-4**: Should VIIRS use OPeNDAP subsetting instead of tile download? The research agent saw an OPeNDAP link on the collection, but it is untested. **— RESOLVED 2026-10-12 (default): use tile download; revisit OPeNDAP subsetting in the spike only if tiles prove too heavy.**

---

## 11. References

- Parent design: [MC-2](cdi-inhouse-percentiles.md) §1.2, §4.2
- GES DISC OPeNDAP retirement: https://disc.gsfc.nasa.gov/information/tools?title=OPeNDAP%20In%20The%20Cloud
- Suomi-NPP end of delivery: https://www.earthdata.nasa.gov/data/alerts-outages/suomi-npp-data-product-delivery-cease-november-1-2026
- Prior art: `akvo/drought-map-hub` `cdi/src/background-jobs/` (`job_00_login.sh`, `utils.sh`), including its pitfalls

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | | | |
| Tech Lead | | | |
| Product | | | |
