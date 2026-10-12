# Global DIH — 1. CDI data pipeline

> The main blocker for taking DIH beyond Eswatini.
> Today we download ready-made percentiles from NDMC, and NDMC only publishes Southern Africa.
> This workstream computes the four CDI inputs ourselves from raw data, so any country can get a CDI.

**Parent design**: [MC-2 — In-house CDI input percentiles](../cdi-inhouse-percentiles.md)
**Hub-side counterpart**: [MC-1 — Multi-country deployment](../multi-country-deployment.md)
**Executed in**: **`akvo/drought-map-hub`** (the generic, multi-country DIH), folder `cdi/`. It is not executed in the Eswatini repos.
**Source of the current pipeline code**: `akvo/eswatini-droughtmap-hub-cdi` `main @ e3651e9`, ported first by [CDP-0](CDP-0_port-eswatini-pipeline.md).
**Status**: Planning. We are waiting for NDMC's answers on method (methodology email + follow-up).

> **Path convention**: new files in CDP-1 … CDP-6 are written with their post-port paths (`cdi/src/cdi-scripts/…`, `cdi/src/background-jobs/…`). References to *existing* code with line numbers point at the eswatini source until CDP-0 lands.

---

## Summary

- **Today**: we download NDMC's ready-made percentiles, which cover Southern Africa only.
- **Change**: compute the 4 CDI inputs ourselves from raw data (rainfall, evaporation, soil moisture, vegetation), so any country works.
- **Order**: first a test run on Eswatini, compared against NDMC's numbers. Then NDMC reviews our method.
- **Watch out**: NASA stops delivering VNP13A3, the vegetation product we planned to use, on **1 Nov 2026**. We use its successor, VJ113A3, from the start.

---

## Sub-tasks

| ID | Plan | What it delivers | Blocked by NDMC? | Size |
|---|---|---|---|---|
| **CDP-0** | [Port the Eswatini pipeline into the generic hub](CDP-0_port-eswatini-pipeline.md) | `drought-map-hub/cdi` runs the current NDMC pipeline inside the generic Docker/Rundeck/wizard wiring; LST/NDVI is renamed to ESI/EVI2 across app, Rundeck and GeoNode | No | M |
| CDP-1 | [Raw data fetch adapters](CDP-1_raw-data-fetch.md) | CHIRPS, FLDAS, ERA5-Land and VIIRS fetched as bbox subsets, filling any missing month | Partly: ERA5 vs ERA5-Land (Q1) and CHIRPS v2 vs v3 (Q5) | M |
| CDP-2 | [Grid, bounds & regrid](CDP-2_grid-bounds-regrid.md) | 0.05° country grid, bounds snapping, antimeridian (Fiji), regrid of every source | No | M |
| CDP-3 | [Index derivation](CDP-3_index-derivation.md) | SPI-3, root-zone SM, EVI2 with the sensor splice, ESI (provisional) | **ESI only** (Q1) | M |
| CDP-4 | [Baseline & percentile engine](CDP-4_baseline-percentile-engine.md) | Frozen 40/14-year baselines, Gaussian and empirical percentiles, the STEP_0100 output contract | Default method only (Q2) | S |
| CDP-5 | [Eswatini validation + NDMC review](CDP-5_eswatini-validation.md) | In-house vs NDMC report (per cell, per Inkhundla, D-class), PASS/FAIL, review email | No | S |
| CDP-6 | [Pipeline integration](CDP-6_pipeline-integration.md) | `percentile_source` switch, incremental runs, yearly baseline roll, onboarding runbook, dead-code removal | After the CDP-5 PASS | M |

---

## Order of work

```
CDP-0 port (drought-map-hub/cdi) ──► everything below
CDP-2 grid ──┬─► CDP-1 fetch ──► CDP-3 derive ──► CDP-4 percentiles ──► CDP-5 validate ──► NDMC review ──► CDP-6 integrate
             └─────────────────────────────────────────────────────────────▲
                                    (CDP-1 needs split_bounds for antimeridian countries)
```

**Before anything else:** CDP-0. The owner must first commit or stash the uncommitted local work in `drought-map-hub`: the Kenya config, `country.topojson`, `CDIMap.js`, and the others listed in CDP-0 §1.

**Can start now, while we wait for NDMC (after CDP-0):**
- CDP-2 (grid);
- CDP-1 (all four adapters; product choice is a config value);
- CDP-3 for SPI, SM and EVI2;
- CDP-4 (both methods);
- the CDP-5 tool.

**Waits for NDMC:**
- the ESI formula (CDP-3);
- the default percentile method (CDP-4);
- the final CDP-5 PASS, after NDMC's review.

**Hard date:** VNP13A3 ends on 1 Nov 2026. CDP-1 must fetch the 2012 → Oct 2026 VNP13A3 history and the 2018 → VJ113A3 overlap.

---

## Decisions already made

| Ref | Decision | Date |
|---|---|---|
| MC-2 D-1 | Ask NDMC for their method first → compute in-house → NDMC validates | 2026-09-30, revised 2026-10-06 |
| MC-2 D-2 | Baseline per component: 40 years for SPI/ESI/SM, 14 years for EVI2 (VIIRS) | 2026-09-30 |
| MC-2 D-5 | Keep the 0.05° grid and the STEP_0100 output contract | 2026-09-30 |
| MC-2 D-7 | Full CDI where the data supports it; SPI-only (a rainfall index) for atoll states such as the Marshall Islands | 2026-10-06 |

---

## Open questions waiting on NDMC

Sent in the methodology email. The full references are in [ndmc-method-questions-references.md](../ndmc-method-questions-references.md).

| NDMC Q | Topic | Affects |
|---|---|---|
| Q1 | ESI formula; ERA5 vs ERA5-Land variables; the ±3σ cap | CDP-1, CDP-3 |
| Q2 | Gaussian vs empirical percentiles; the 40-year window | CDP-4, CDP-5 |
| Q3 | EVI2 sensor and long history ("modelled backups"); NOAA-20/21 | CDP-1, CDP-3 |
| Q4 | Soil moisture: FLDAS 0–100 cm weights | CDP-3 |
| Q5 | SPI: CHIRPS v3, calibration period | CDP-1, CDP-3 |
| Q6 | Example download and processing code | CDP-1 |
| Q7 | Suitability for small island states (Fiji, Marshall Islands) | MC-2 D-7, CDP-6 |

---

## Key measured facts (so nobody re-checks them)

| Fact | Measured |
|---|---|
| NDMC `Regional_Percentiles` lists only `Southern_Africa` | 2026-09-30 |
| All four NDMC inputs now start in 2012, and EVI2 has all 12 months (backfilled 11 Aug 2026) | 2026-10-06 |
| CHIRPS-2.0 COG windowed read gives Eswatini as 44×44 cells, with no full download | 2026-10-12 |
| FLDAS bbox subset via Earthdata Cloud OPeNDAP is 45 KB per month; the on-prem `hydro1` OPeNDAP returns 410 | 2026-09-30 |
| FLDAS global has no PET variable, so ESI needs ERA5(-Land) | 2026-09-30 |
| Earthdata login (hub `.env`) reaches LP DAAC and GES DISC | 2026-09-30 |
| Marshall Islands: FLDAS has 0 land cells; CHIRPS has data. Fiji crosses 180° | 2026-10-06 |
| `config_reader` grid is empty for `w_lon > e_lon`, so it breaks for antimeridian countries | 2026-10-12 |
