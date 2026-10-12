# Feature Design Document

## Feature: Pipeline integration — `percentile_source` switch, scheduling, new-country onboarding, dead-code removal

**Task ID**: CDP-6 (sub-task of [MC-2](../cdi-inhouse-percentiles.md))
**Author**: Iwan Firmawan (with Claude)
**Date**: 2026-10-12
**Status**: Draft. **Starts only after CDP-5 passes.**
**Repo affected**: `drought-map-hub` → `cdi/` (after the [CDP-0](CDP-0_port-eswatini-pipeline.md) port; file/line refs to existing code point at the `eswatini-droughtmap-hub-cdi` source until then)
**Blocked by NDMC?** Indirectly. It waits for the CDP-5 PASS, which should include NDMC's review.

---

## 1. Context & Problem Statement

```
Currently (live production chain, STEP_0000):
  job.sh → job_01 (NDMC download) → STEP_0100 → 0301 → 0302 → 0303
         → upload_to_geonode → sync to hub

- job.sh greps weights from the config (get_weight_from_config, line 34), and
  skips the download for any weight-0 input.
- cleanup_output_data (utils.sh:374) deletes every output_data/*.nc and
  GeoTiffs/*.tif on each run, so everything is recomputed every time.
- Dead code remains:
    STEP_0104 / STEP_0204 (KeyError on removed config keys),
    libs/hdf_functions.py, libs/h4toh5convert(.exe),
    the legacy shell download functions in utils.sh,
    FinalMapOutput-*-ESRI.py (arcpy, hard-coded 'eSwatini').
- Onboarding a new country is undocumented: bounds, region name, weights,
  credentials.

Goal:
- One config switch chooses NDMC or in-house percentiles. Everything after
  STEP_0100 is shared.
- In-house runs are incremental and cheap: fetch only missing months, rank only
  new months, rebuild the baseline once a year on purpose.
- Onboarding a new country is a written runbook that takes hours, not a code
  change.
- The dead code is deleted.
```

---

## 2. Requirements

### User Acceptance Criteria
- [ ] Eswatini production keeps running on NDMC (`percentile_source: ndmc`) with no change in output until someone flips the switch.
- [ ] A new country can be onboarded by following `docs/onboarding-a-country.md`, with no code edits.
- [ ] A monthly in-house run for one country finishes in under 30 minutes, excluding CDS queue time.

### Technical Acceptance Criteria
- [ ] `percentile_source: ndmc | inhouse` in `cdi_project_settings.conf`. Default is `ndmc`.
  - `ndmc`: today's `job_01` + STEP_0100.
  - `inhouse`: CDP-1 `fetch_raw` → CDP-2 regrid → CDP-3 derive → CDP-4 STEP_0110.
  - **Both write the same `STEP_0100_*_pct_rank_{region}.nc`**, then 0301 → 0303 run unchanged.
- [ ] `cleanup_output_data` no longer deletes `input_data/raw/`, `working_data/regrid|index|baseline/` in `inhouse` mode. Only `output_data/` is rebuilt.
- [ ] A yearly job (January) runs `--rebuild-baseline --end-year <last full year>`. It is logged, and needs one manual approval before the new vintage becomes active.
- [ ] **Product profile** (MC-2 D-7):
  - If the config's weights leave only SPI > 0, the export writes `product: "spi_only"` into the GeoTIFF metadata.
  - The hub (MC-1) can then label the map as a rainfall index, not a CDI.
- [ ] **Antimeridian export**: STEP_0303 writes valid GeoTIFFs for 0–360° grids (CDP-2), in whatever form GeoNode accepts (CDP-2 OQ-1).
- [ ] `env.example` lists `EARTHDATA_USERNAME`, `EARTHDATA_PASSWORD`, `ECMWF_API_KEY` and `ECMWF_API_URL`.
- [ ] Dead code deleted: STEP_0104, STEP_0204, `libs/hdf_functions.py`, both `h4toh5convert` binaries, the legacy download functions in `utils.sh`, `FinalMapOutput-*.py`, and `rank_parameter` (superseded by CDP-4). `CLAUDE.md` and `docs/` are updated to match.

---

## 3. Data Model Changes

### Config (`cdi_project_settings.conf`): final shape for in-house mode

```json
{
  "region_name": "Eswatini",
  "bounds": { "n_lat": -25.675, "s_lat": -27.825, "w_lon": 30.675, "e_lon": 32.825 },
  "percentile_source": "ndmc",
  "sources":    { "...": "CDP-1" },
  "derivation": { "...": "CDP-3" },
  "baseline":   { "years": 40, "end_year": 2025 },
  "percentile": { "method": "gaussian", "clip_sigma": 3, "min_years": 10 },
  "cdi_ranking": "pooled",
  "cdi_parameters": { "names": { "...": "unchanged" }, "weights": { "esi": 0.3, "evi2": 0.3, "spi": 0.3, "sm": 0.1 } }
}
```

### Migration Strategy

```
- Default ndmc gives zero behaviour change.
- Switching Eswatini to inhouse is a separate, announced change. It shifts
  published values and needs partner sign-off.
- Rollback: set percentile_source back to ndmc and re-run.
```

---

## 4. API Contract

```bash
./cdi/src/background-jobs/job.sh recent        # reads percentile_source from config
./cdi/src/background-jobs/job.sh all
./cdi/src/background-jobs/job.sh rebuild-baseline 2026      # yearly, manual approval
python cdi/src/cdi-scripts/snap_bounds.py country.geojson   # onboarding (CDP-2)
```

Onboarding runbook (`docs/onboarding-a-country.md`):
1. Snap the bounds from the boundary GeoJSON.
2. Set `region_name`, `bounds` and `weights`; set the weights to SPI-only for atoll states (MC-2 D-7).
3. Set the credentials in `.env`.
4. `fetch_raw --param all --from <start> --to latest`.
5. `rebuild-baseline`.
6. `job.sh all`.
7. Check the GeoNode categories.
8. Point `DROUGHTMAP_HUB_URL` at the country's hub.

---

## 5. Decision Log

### D-1: A config switch, not a fork
**Rationale**:
- Both modes share 0301 → upload → sync, which are tested and in production.
- A fork would duplicate that tested code.

### D-2: Eswatini stays on NDMC by default
**Rationale**:
- NDMC is the reference, and Eswatini's partners are used to its numbers.
- In-house exists so other countries can be covered and so we can keep running if NDMC stops. It is not meant to replace a working feed.

**Impact**: switching Eswatini over is a product decision, not part of this task.

### D-3: The baseline roll-forward needs a human approval
**Rationale**: a new vintage shifts every percentile slightly. Someone should look at the CDP-5-style comparison against the old vintage before it goes live.

---

## 6. Type/Constant Mappings

| `percentile_source` | Steps before 0301 | Inputs on disk |
|---|---|---|
| `ndmc` | job_01 → STEP_0100 | `input_data/{ESI,EVI2,SPI,SM}/*.tif` |
| `inhouse` | fetch_raw → regrid → derive → STEP_0110 | `input_data/raw/`, `working_data/{regrid,index,baseline}/` |

---

## 7. Compatibility & Migration

### Backward Compatibility
- [ ] With the default `ndmc`, output for Eswatini is byte-identical. The existing `test_cdi_pipeline.py` passes unchanged.
- [ ] GeoTIFF names, GeoNode categories and the hub sync are unchanged.

### Seeder/CLI Compatibility
- [ ] New `job.sh` subcommand: `rebuild-baseline`.
- [ ] The removed scripts were never called by `STEP_0000`; the agent report confirmed this.

---

## 8. Security Considerations

- [ ] Credentials live only in `.env`, never in the config files, which are committed.
- [ ] Deleting the bundled `h4toh5convert` ELF and `.exe` binaries removes unauditable executables from the repo.

---

## 9. Testing Strategy

| Test Type | Coverage |
|---|---|
| Unit | Switch parsing; `cleanup_output_data` keeps in-house caches; the SPI-only profile writes the right metadata. |
| Integration | `ndmc` mode: the existing suite, byte-identical. `inhouse` mode: synthetic raw fixtures run end-to-end to GeoTIFF. Antimeridian: a synthetic 0–360° grid exports a GeoTIFF that rasterio reopens with the correct bounds. |
| Manual | Run the onboarding runbook for a dry-run country (e.g. Fiji, with SPI-only and full profiles) up to a local GeoNode upload. |

---

## 10. Open Questions

- [x] **OQ-1**: Where do several countries' pipelines run: one VM with one config per country, or one VM each? Disk is now small (MC-2 OQ-5). **— RESOLVED 2026-10-12: one VM, one config per country.**
- [x] **OQ-2**: Who approves a baseline roll-forward: the dev team or the TWG? **— RESOLVED 2026-10-12: the dev team triggers `--rebuild-baseline`; TWG/NDRMA sign off on the new baseline vintage.**
- [x] **OQ-3**: Does the hub (MC-1) read `product: "spi_only"` from GeoNode metadata or from its own country config? Coordinate with MC-1 task 4. **— RESOLVED 2026-10-12: the hub reads it from its own team-owned country config (B-4), not GeoNode metadata; wire during the iterative MC-1 porting.**

---

## 11. References

- Parent design: [MC-2](../cdi-inhouse-percentiles.md) §4.1, §7, §11; D-7
- Hub side: [MC-1](../multi-country-deployment.md)
- Code (eswatini source, pre-port): `src/background-job/job.sh` (line 34), `utils.sh` (lines 308, 374), `STEP_0000_execute_all_steps.py` (lines 34-37), `upload_to_geonode_job.py`

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | | | |
| Tech Lead | | | |
| Product | | | |
