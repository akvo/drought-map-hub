# Feature Design Document

## Feature: Port the Eswatini CDI pipeline into the generic Drought-map Hub (`drought-map-hub/cdi`)

**Task ID**: CDP-0 (prerequisite of CDP-1 … CDP-6)
**Author**: Iwan Firmawan (with Claude)
**Date**: 2026-10-12
**Status**: Draft
**Source**: `akvo/eswatini-droughtmap-hub-cdi`, `main @ e3651e9`. Port from the **commit**, not the working tree: the working tree has a local edit in `src/background-job/job.sh` that comments out the upload.
**Target**: `akvo/drought-map-hub`, folder `cdi/`, plus the contract rename in `app/`, `geonode/` and `app/rundeck/`.

---

> **Multi-tenancy (WS-3):** this port is the basis for the **central multi-tenant pipeline** ([MT-11](../3-multi-tenancy/MT-11_central-pipeline.md)) — one pipeline that discovers tenants from the hub and loops over them, writing to `/app/data/<subdomain>/`. The `v1_geonode` push gains per-tenant attribution ([MT-8](../3-multi-tenancy/MT-8_geonode-tenant-attribution.md)). The port itself is unchanged; MT-11 wraps it in the tenant loop. A standalone deploy runs it for the `default` tenant.

## 1. Context & Problem Statement

```
Currently:
- The generic Drought-map Hub (akvo/drought-map-hub, Sep 2025) is the
  multi-country product. Its cdi/ is the OLD raw-data pipeline:
    - MODIS LST (MOD21C3) and NDVI (MOD13C2), CHIRPS → SPI, FLDAS SM (disabled);
    - STEP_0101…0303;
    - Earthdata cookie login (job_00);
    - Docker image cdi-scripts, driven by Rundeck.
  NDMC has retired LST/NDVI, and the FLDAS on-prem server it used is retired
  too (hydro1 OPeNDAP → 410).
- The Eswatini pipeline (akvo/eswatini-droughtmap-hub-cdi) is the CURRENT one:
    - NDMC ESI/EVI2/SPI/SM percentiles;
    - STEP_0100 → 0301 → 0302 (pooled) → 0303;
    - a hardened GeoNode upload, a multi-portal sync;
    - pytest + CI.
  It is Eswatini-only (host venv + cron, Southern Africa source).
- CDP-1 … CDP-6 extend the Eswatini pipeline, but they must be EXECUTED in
  drought-map-hub, because that is the product meant for every country.

Goal:
- drought-map-hub/cdi runs the Eswatini pipeline's code, inside the generic
  hub's Docker + Rundeck + setup-wizard wiring.
- The whole generic hub speaks the new input vocabulary (ESI/EVI2/SPI/SM)
  instead of LST/NDVI.
- CDP-1 … CDP-6 then build on top of the ported code.
```

**Measured state of the target (2026-10-12):**
- `drought-map-hub` has **uncommitted local work**: `.gitignore`, `app/backend/source/country.topojson`, `cdi/config/cdi_project_settings.json` (bounds for **Kenya**), `cdi/src/background-jobs/job_03_run_cdi.sh`, `upload_cdi_to_geonode_job.py`, `CDIMap.js`, `iframe/map/page.js`, `publications_seeder.py`, and an untracked `CLAUDE.md`.
  - **These must be committed or stashed by the owner before the port starts.** The port never overwrites them.
- **Kenya is outside NDMC's `Southern_Africa` extent** (12–43°E, 18–36°S). After the port, a Kenya instance gets **no CDI in `ndmc` mode** until in-house mode (CDP-1 → CDP-6) lands. See D-2.

---

## 2. Requirements

### User Acceptance Criteria
- [ ] Following the README, an operator can run `./run.sh mode=dev service=cdi` and then the Rundeck job, and get CDI/ESI/EVI2/SPI/SM GeoTIFFs in GeoNode for a Southern-Africa country (Eswatini as the reference).
- [ ] The setup wizard and the Rundeck "change weight" step accept ESI/EVI2/SPI/SM weights. LST/NDVI no longer appears anywhere in the UI.
- [ ] Eswatini output from `drought-map-hub/cdi` is byte-identical to `eswatini-droughtmap-hub-cdi` for the same month and the same NDMC inputs.

### Technical Acceptance Criteria
- [ ] **Code ported** (source path → target path):

  | Source (`eswatini-droughtmap-hub-cdi`) | Target (`drought-map-hub`) |
  |---|---|
  | `src/data-processing/cdi-scripts/` (STEP_0000, 0100, 0301, 0302_rank_cdi_pooled, 0303, `libs/`, `cdi_*_settings.conf`, `requirements.txt`, `__tests__/`) | `cdi/src/cdi-scripts/` |
  | `src/background-job/` (`job.sh`, `job_01`, `job_03`, `job_04`, `job_05_sync_to_portal.sh`, `utils.sh`, `upload_to_geonode/` with `__tests__/`, `requirements.txt`, `geonode_category.json`) | `cdi/src/background-jobs/` (plural, which the target's Rundeck and scripts expect) |
  | `docs/*.md`, `docs/jupyter-notebook-ndmc-validation/` | `cdi/docs/` |
  | `.github/workflows/tests.yml` (2 pytest jobs) | merged into `.github/workflows/test.yml` and `ci/test.sh` as a `cdi` job |
  | `env.example` (NDMC + GeoNode + `DROUGHTMAP_HUB_*`) | merged into `cdi/env.example`; the `configure.sh` prompts are updated |

- [ ] **Kept from the target** and adapted, not replaced:
  - `cdi/src/cdi-scripts/Dockerfile`: add `curl wget jq` to the slim image, because the ported shell jobs need them. The Python version is unchanged; numpy 2.0 and rasterio 1.3.10 support 3.10.
  - `cdi/docker-compose*.yml`: the config mount `./config/cdi_project_settings.json → /app/cdi_project_settings.conf` stays.
  - `change-cdi-bounds.sh`: unchanged.
  - `change-cdi-weight.sh`: takes `--esi_weight --evi2_weight --spi_weight --sm_weight`, and validates that they sum to 1.0 within 1e-6, the same rule as STEP_0301.
- [ ] **Removed from the target `cdi/`**:
  - STEP_0101/0102/0103/0201/0202/0203;
  - `job_00_login.sh`, `job_02_extract-n-rename-chirps.sh`;
  - `MERRA2_100…198101.nc4` (a login probe file committed to the repo);
  - the `FinalMapOutput-*.py` scripts;
  - the legacy LST/NDVI download functions.

  Keep all of these in git history, and tag the pre-port commit `legacy-lst-ndvi-pipeline` (D-2).
- [ ] **Not ported from the source** (`eswatini-droughtmap-hub-cdi`):
  - `src/data-processing/aggregation/main.py` — a hardcoded prototype (sample `eswatini_sample_CDI.tif` paths, matplotlib, not called by `job.sh`). Production per-admin aggregation lives in the hub, not here.
- [ ] **Contract rename across the generic hub** (LST/NDVI → ESI/EVI2, add SM):
  - `app/backend/api/v1/v1_rundeck/models.py`: `lst_weight`/`ndvi_weight` become `esi_weight`/`evi2_weight`. `spi_weight` and `sm_weight` already exist. This needs a migration (§3); the serializer and views follow.
  - `app/backend/api/v1/v1_publication/constants.py`: the `ndvi-raster-map`/`lst-raster-map` categories become `evi2-raster-map`/`esi-raster-map`, and `sm-raster-map` is added.
  - `app/backend/source/config/cdi_project_settings.template.json` and `.json`: the eswatini-cdi config shape (`cdi_parameters.names` = `esi_pct_rank`, …; `cdi_ranking: "pooled"`).
  - `app/rundeck/templates/job_template.json`: the weight options are renamed, and the exec paths are fixed to the real script names (the generic hub had a mismatch).
  - `geonode/src/cdi/management/commands/add_cdi_categories.py`: create `esi/evi2/sm-raster-map`. Keep the old categories so existing layers are not orphaned.
  - Frontend: `static/config.js`, `app/settings/page.js`, `app/about/page.js`.
- [ ] **CI**: the ported cdi pytest suites (`test_cdi_pipeline.py` and the upload/sync tests) pass in the target's CI.
- [ ] The port is a **new branch** in `drought-map-hub`, e.g. `feature/port-ndmc-cdi-pipeline`, split into reviewable commits: (1) cdi code, (2) docker/CI, (3) app + rundeck + geonode rename, (4) new optional `v1_geonode` app (geonode publication-push endpoints), (5) docs.

---

## 3. Data Model Changes

### Modified Models (`drought-map-hub/app`)

| Model | Change | Reason |
|---|---|---|
| `v1_rundeck.Settings` | `lst_weight` → `esi_weight`, `ndvi_weight` → `evi2_weight`. `spi_weight` and `sm_weight` already exist. The defaults change from 0.3/0.3/0.4/0.0 to 0.3/0.3/0.3/0.1 (Eswatini's NDMC weights). | Match the inputs the ported pipeline actually uses |

### Migration Strategy

```python
# 1. RenameField lst_weight → esi_weight, ndvi_weight → evi2_weight.
#    ESI is NDMC's replacement for LST and EVI2 for NDVI (NDMC mail), so the
#    existing rows keep their weights as-is.
# 2. AlterField defaults (spi 0.3, sm 0.1). This affects new rows only;
#    existing rows are not rewritten.
# 3. Reversible: RenameField back, restore the old defaults.
```

### New optional app: `api/v1/v1_geonode` (generic hub)

The geonode publication-push endpoint has **no app of its own** in the eswatini hub — it lives in `v1_publication` (`backend/api/v1/v1_publication/urls.py`: `geonode/publications`, `geonode/publications/{pk}/rasters`). In the generic hub it becomes a **new, standalone, optional** app so GeoNode can be disabled or replaced later:

| Piece | What |
|---|---|
| `v1_geonode/urls.py` | `POST v1/geonode/publications` (steady-state metadata sync from a CDI run); `POST v1/geonode/publications/{pk}/rasters` (GeoNode-down fallback: pre-computed raster values) |
| `v1_geonode/views.py` + `serializers.py` | extracted from the eswatini-v2 `v1_publication` push views; both POSTs authenticate with an **API key** (`HasApiKey`), not a session/user. They set the fields the CDI pipeline sends (geonode id, year-month, category, URLs, file size) |
| `PublicationGeonode` model + migration | cache of GeoNode resource metadata (one row per resource, `geonode_id` unique) so reads survive GeoNode downtime; the read path `CDIGeonodeAPI.get` serves this cache instead of calling GeoNode live (the generic repo currently pulls live — this port moves it to cache-backed) |
| `sync_publication_geonodes` command | backfill of the cache for history / recovery |
| module flag | gated by `DIH_MODULES` (default on; see MC-1 §6). Disabled → endpoints **404** |

**How the CDI side reaches the hub (config, not status-probing):** the ported pipeline step `job_05_sync_to_portal.sh` POSTs to this app **only when** `DROUGHTMAP_HUB_URL` + `DROUGHTMAP_HUB_API_KEY` are set in `cdi/.env`; unset → it skips silently. The pipeline never probes the hub or branches on an HTTP status to decide whether the module exists — the enable/disable signal is configuration, and auth is the API key.

> **E2 — superseded by the core-`Raster` split.** The cache design in the table above (`PublicationGeonode` + `PublicationRaster`, read via `CDIGeonodeAPI`) was replaced mid-E2 by a platform-independent core **`Raster`** asset in `v1_publication` (native push `POST /api/v1/rasters`, listing `GET /admin/rasters`) and a thin **`GeoNodeResource`** pointer in `v1_geonode` (push `POST /api/v1/geonode/publications`, which ensures the `Raster` then upserts the pointer). The pipeline now pushes to `/api/v1/rasters` (authoritative, module-independent) **then** best-effort `/api/v1/geonode/publications` (a `404` = module off, tolerated). `GeonodeRasterPushAPI`, the `admin/cdi-geonode` route and the `sync_publication_geonodes` backfill were dropped. See [DIH-1 §11](../2-v2-porting/DIH-1_v1-geonode-optional-app.md#11-what-shipped-e2) for the shipped state.

---

## 4. API Contract

| Method | URL | Change |
|---|---|---|
| GET | `/api/v1/admin/settings` (existing `SettingsViewSet`) | Weight fields planned to become `esi_weight`/`evi2_weight` — **deferred in E2**: the DB/serializer/Rundeck-option names stay `lst_weight`/`ndvi_weight` (the UI labels show ESI/EVI2). A full rename needs a migration + Rundeck job re-create (see D-1). |
| PUT | `/api/v1/admin/setting/{pk}` | same |

```json
// PUT /api/v1/admin/setting/1  (field names unchanged in E2)
{ "lst_weight": 0.3, "ndvi_weight": 0.3, "spi_weight": 0.3, "sm_weight": 0.1 }
// 400 if the sum differs from 1.0 by more than 1e-6
```

Rundeck job (exec steps — run **inside** the `cdi` container; `change-cdi-weight.sh` accepts the legacy `--lst/--ndvi` aliases → esi/evi2):

```
docker exec cdi bash /app/src/background-jobs/change-cdi-weight.sh \
  --lst_weight=${option.lst_weight} --ndvi_weight=${option.ndvi_weight} \
  --spi_weight=${option.spi_weight} --sm_weight=${option.sm_weight}
docker exec cdi bash /app/src/background-jobs/job.sh
```

---

## 5. Decision Log

### D-1: Port INTO the generic hub, keep its layout and wiring
**Options**:
1. Replace `drought-map-hub/cdi` wholesale with the eswatini repo.
2. Port the eswatini code into the generic hub's layout: `cdi/src/cdi-scripts`, `cdi/src/background-jobs`, Docker, Rundeck and the wizard.

**Decision**: 2.

**Rationale**: the generic hub's wiring is the multi-country part:
- `configure.sh`;
- the setup wizard writing `cdi_project_settings.json`;
- `change-cdi-bounds.sh`;
- the Rundeck template;
- Docker.

A wholesale copy would break all of it.

**Impact**: paths in CDP-1 … CDP-6 refer to the post-port layout, `drought-map-hub/cdi/src/...`.

### D-2: Drop the legacy LST/NDVI pipeline, but tag it
**Options**:
1. Keep the old raw pipeline as a fallback mode.
2. Remove it and tag the last commit.

**Decision**: 2. **Confirmed by the owner on 2026-10-12 (OQ-1): no live non-Southern-Africa instance, so the legacy pipeline is removed and tagged `legacy-lst-ndvi-pipeline`.**

**Rationale**: its sources are already failing:
- NDMC retired LST/NDVI;
- the GES DISC on-prem server it relied on returns 410;
- MODIS is at end of life.

Keeping it means maintaining two pipelines to postpone a gap that CDP-1 → CDP-6 closes anyway.

**Impact**: non-Southern-Africa instances (Kenya) have no CDI between the port and in-house mode going live.

### D-3: Keep the old GeoNode categories alongside the new ones
**Rationale**: existing instances have published `lst-raster-map`/`ndvi-raster-map` layers that the public "browse" and "compare" pages may still link to.

**E2 status**: the pipeline + hub were **renamed** to `esi/evi2/sm` (`esi-raster-map` ← `lst`, `evi2-raster-map` ← `ndvi`, plus new `sm-raster-map`) across `upload_to_geonode_job.py`, `sync_geonode_publications_job.py`, the GeoNode seeder `add_cdi_categories.py`, and the hub `CDIGeonodeCategory`. The old `lst/ndvi-raster-map` categories are **left in GeoNode as orphans** (not deleted) so old browse/compare links still resolve — matching this decision's intent. The weight-reconfig CLI (`change-cdi-weight.sh`) accepts both the legacy `--lst_weight/--ndvi_weight` and the new `--esi_weight/--evi2_weight` (the app's DB/API/Rundeck option names stay `lst_weight`/`ndvi_weight`; a full identifier rename needs a migration + Rundeck job re-create, deferred).

### D-4: Create a new, optional `v1_geonode` app from the eswatini `v1_publication` push endpoints
**Decision** (2026-10-12, OQ-2): the geonode publication-push endpoints have no app of their own in the eswatini hub — they live in `v1_publication`. In the generic hub, extract them into a **new, standalone, optional** app `api/v1/v1_geonode` (see §3). The ported pipeline step `job_05_sync_to_portal.sh` POSTs to it.

**Rationale**:
- The eswatini-v2 push endpoints (`POST /api/v1/geonode/publications` + `/rasters`, `HasApiKey`) and the `PublicationGeonode` cache do not exist in the generic app, which still pulls GeoNode live.
- A dedicated app keeps GeoNode concerns isolated and **optional** (`DIH_MODULES`), so a future deployment can disable or replace GeoNode without touching `v1_publication`. This fits MC-1's pluggable-module model.
- The pipeline push is **env-gated**: `job_05_sync_to_portal.sh` skips silently when `DROUGHTMAP_HUB_URL`/`_API_KEY` are unset, so Eswatini and other deployments are unaffected until the endpoint is wired. The decision is config-driven, not an HTTP-status fallback.

**Impact**: a new `v1_geonode` app gated by `DIH_MODULES` is added, and the ported sync step moves from "off" to active once the endpoint and `DROUGHTMAP_HUB_URL`/`_API_KEY` are configured. *(E2: the originally-planned `PublicationGeonode` cache + `sync_publication_geonodes` backfill were superseded — the GeoNode-independent read path is the core `Raster.values`, and `v1_geonode` holds only a `GeoNodeResource` pointer. See §3 note and [DIH-1 §11](../2-v2-porting/DIH-1_v1-geonode-optional-app.md#11-what-shipped-e2).)*

---

## Implementation steps

Reviewable commits, in order (mirror the §2 AC commit list):
1. New branch `feature/port-ndmc-cdi-pipeline`; copy the `cdi/` code (scripts + `background-jobs/` plural) from the eswatini source. → verify: `job.sh --dry-run` resolves; tree matches the source layout.
2. Port docker/compose + CI wiring for `cdi`. → verify: `ci/test.sh` green for the cdi suite.
3. App/rundeck/geonode rename + the weight migration (`RenameField` lst→esi, ndvi→evi2; `AlterField` defaults spi 0.3, sm 0.1). → verify: `migrate` forward **and** back; existing rows keep their weights.
4. Create the optional `v1_geonode` app and wire it into `DIH_MODULES` (full steps in [DIH-1](../2-v2-porting/DIH-1_v1-geonode-optional-app.md)). → verify: `geonode` off → push endpoint 404; on → a mocked pipeline push creates a `Publication`.
5. Docs (README + onboarding). → verify: links resolve; the onboarding runbook (CDP-6) is referenced.

---

## 6. Type/Constant Mappings

| Old (generic hub) | New | Where |
|---|---|---|
| `lst` / `lst_anom_pct_rank` / `lst-raster-map` / `lst_weight` | `esi` / `esi_pct_rank` / `esi-raster-map` / `esi_weight` | config, constants, GeoNode, Rundeck, Settings |
| `ndvi` / `ndvi_anom_pct_rank` / `ndvi-raster-map` / `ndvi_weight` | `evi2` / `evi2_pct_rank` / `evi2-raster-map` / `evi2_weight` | same |
| `spi` / `spi_3_anom_pct_rank` | `spi` / `spi_pct_rank` | config |
| `sm` / `RootZone2_SM_pct_rank` / `sm_weight` (default 0.0) | `sm` / `sm_pct_rank` / `sm-raster-map` (new) / `sm_weight` (default 0.1) | config, GeoNode, Settings |
| `GeoTiffs/{CDI,LST,NDVI,SPI}` | `GeoTiffs/{CDI,ESI,EVI2,SPI,SM}` | export folders, which map to upload categories |

---

## 7. Compatibility & Migration

### Backward Compatibility
- [ ] Existing published publications and their GeoNode layers stay readable (D-3).
- [ ] `Settings` rows keep their weights through the rename migration.
- [ ] The uncommitted local work in `drought-map-hub` is untouched. The owner commits or stashes it first.

### Seeder/CLI Compatibility
- [ ] `configure.sh` writes the new `cdi/.env` keys: `DOWNLOAD_NDMC_BASE_URL`, `DOWNLOAD_{ESI,EVI2,SPI,SM}_DATASET`, `DROUGHTMAP_HUB_URL`/`_API_KEY` (optional).
- [ ] `post-installation.sh` still copies the backend's `cdi_project_settings.json` into `cdi/config/`.
- [ ] `add_cdi_categories` is idempotent: creating a category that already exists is a no-op.

---

## 8. Security Considerations

- [ ] Remove the committed `MERRA2_100…198101.nc4` (a login probe file) and `.urs_cookies` patterns. Add both to `.gitignore`.
- [ ] Earthdata credentials are no longer needed in `ndmc` mode. They come back in CDP-1, via a temporary netrc, never on argv.
- [ ] `configure.sh` keeps its masked secret prompts.

---

## 9. Testing Strategy

| Test Type | Coverage |
|---|---|
| Unit | The ported `test_cdi_pipeline.py` and the upload/sync `__tests__` run unchanged in the target. `change-cdi-weight.sh` rejects weights that don't sum to 1. |
| Backend | The `Settings` migration forwards and backwards (weights preserved); serializer validation of the sum; constants used by the browse/compare views. |
| Integration | In Docker: `job.sh recent` for Eswatini bounds, then compare the output GeoTIFFs **byte-for-byte** with an `eswatini-droughtmap-hub-cdi` run on the same NDMC files. |
| E2E (manual) | `./run.sh mode=dev service=all` → setup wizard (Eswatini GeoJSON) → set weights → trigger the Rundeck job → layers appear in GeoNode under the new categories → a publication is created in the app. |

---

## 10. Open Questions

- [x] **OQ-1 (D-2)**: Is any live instance relying on the old LST/NDVI pipeline outside Southern Africa? Kenya is configured locally. If one is live, it loses its CDI until CDP-6 ships. **— RESOLVED 2026-10-12: no live instance (Kenya is local/dev only), so the legacy pipeline is dropped and tagged.**
- [x] **OQ-2 (D-4)**: Port the eswatini hub's `/api/v1/geonode/publications` endpoint into the generic app, or keep the generic app's own publication-creation flow? **— RESOLVED 2026-10-12: extract the eswatini `v1_publication` geonode push endpoints into a new, standalone, optional `v1_geonode` app in the generic hub, and enable the ported sync job to POST to it (see D-4 / §3).**
- [x] **OQ-3**: Should the eswatini hub's v2 app features (review/validation redesign, Insights, modules) also move into the generic hub? That is the scope of MC-1, and it is far larger than this port. It needs a decision before MC-1 starts. **— RESOLVED 2026-10-12: no wholesale move. Port the backend APIs first (starting with `v1_geonode`), then port the frontend iteratively to strip Eswatini hardcoding. MC-1 proceeds backend-first and incrementally.**
- [x] **OQ-4**: After the port, does `eswatini-droughtmap-hub-cdi` keep running for Eswatini production, or does Eswatini move to the generic hub's `cdi/`? Until decided, fixes must land in both. **— RESOLVED 2026-10-12: keep both — `eswatini-droughtmap-hub-cdi` stays Eswatini-only, this `cdi/` is the generic/global pipeline. They may diverge; no byte-sync promise.**

---

## 10b. E2 operational fixes (surfaced running the ported pipeline)

- **Config reaches host runs.** Rundeck runs the pipeline on the host via `~/.myenv`, not the `cdi` container, so the compose bind-mount `config/cdi_project_settings.json → src/cdi-scripts/cdi_project_settings.conf` does not apply. The scripts (`config_reader.py`) **and** `job.sh get_weight_from_config` read the `.conf`. `job.sh` now `cp`-syncs the client `.json` → `.conf` at run start (guarded by `cmp -s`) so edits made via `change-cdi-bounds.sh`/`change-cdi-weight.sh` (which write the `.json`) actually take effect.
- **Bounds must fit the NDMC raster** (`12–43°E, 18–36°S`, 0.05°) or `STEP_0100` aborts with "Clipped grid is X but expected Y" — it reads a fixed `rows×cols` window from the top-left corner. Northern-hemisphere-of-18°S areas (e.g. northern Namibia) have no data in this NDMC tile.
- **Weights must total 1.0 over exactly the active params.** `STEP_0301` sums every key in `weights`, so stale `lst/ndvi` keys left beside `esi/evi2/spi/sm` push the total past 1.0. `change-cdi-weight.sh` now replaces the whole `weights` object (self-healing) and `get_categories()` in `upload_to_geonode_job.py` always refreshes its cached `geonode_category.json` instead of writing it once.
- **GeoNode host must be consistent.** `geonode/.env` `SITEURL`/`HTTP_HOST`/`ALLOWED_HOSTS` must name the same host as the hub's `GEONODE_HOST` and the pipeline's `GEONODE_URL`, or nginx drops the connection / Django 400s. `configure.sh` now passes `--hostname` to `create-envfile.py` so these line up at provisioning (see [DIH-1 §11](../2-v2-porting/DIH-1_v1-geonode-optional-app.md)).

## 11. References

- Pipeline plans built on this port: [README](README.md), CDP-1 … CDP-6
- Parent designs: [MC-2](cdi-inhouse-percentiles.md), [MC-1](../2-v2-porting/README.md)
- NDMC retirement of LST/NDVI: `cdi/docs/lst-ndvi-retirement-mail.md` (after the port)
- Generic hub wiring: `drought-map-hub/run.sh`, `configure.sh`, `post-installation.sh`, `app/rundeck/templates/job_template.json`, `app/backend/api/v1/v1_setup/views.py:294-425`

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | | | |
| Tech Lead | | | |
| Product | | | |
