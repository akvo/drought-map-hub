# Feature Design Document

## Feature: Optional `v1_geonode` app (GeoNode publication-push)

**Task ID**: DIH-1
**Author**: Iwan Firmawan (with Claude)
**Date**: 2026-10-30
**Status**: Implemented (E2, branch `feature/21-optional-geonode-durable-storage`) — see §11 for what shipped vs this plan.
**Effort**: ~9h total (incl. agentic coding) → 2 phases ≤8h each (see Phases): 1a `v1_geonode` ~6h, 1b persistent storage ~3h.
**Depends on**: [DIH-2](DIH-2_module-system.md) (gating mechanism for the `geonode` flag); bootstrapped inside [CDP-0](../1-cdi-data-pipeline/CDP-0_port-eswatini-pipeline.md)

---

> **Multi-tenancy (WS-3):** under the multi-tenant target, `PublicationGeonode` gains a `tenant` FK and the push is attributed per tenant (GeoNode category prefix + service identity / API key). Extended by [MT-8](../3-multi-tenancy/MT-8_geonode-tenant-attribution.md); `geonode_id` stays globally unique. Standalone deploy = the `default` tenant, unchanged.

## 1. Context

The CDI pipeline pushes a finished publication to the hub via `/api/v1/geonode/publications` (+ `/rasters`). In the Eswatini hub that endpoint lives inside `v1_publication` (`CDIGeonodeAPI`, `views.py:167`); the generic hub does not have it as its own app. CDP-0 OQ-2/D-4 decided to **extract it into a new, standalone, optional `v1_geonode` app** so GeoNode can be disabled or swapped per deployment.

**`v1_geonode` (hub app) ≠ GeoNode (infra).** Keep these separate:

| | What it is | Stores rasters? |
|---|---|---|
| **GeoNode** | the external spatial server (own compose) | **Yes — the raster store.** `cdi/.../job_04_upload_to_geonode` uploads the GeoTIFFs here directly |
| **`v1_geonode`** | the hub endpoints that receive the pipeline push and serve it from a metadata **cache** (`PublicationGeonode`) | **No raster files** — only GeoNode resource *metadata* (ids, URLs, size) |

## 2. Where it is toggled, and what "off" means

- **Toggle = env, via [DIH-2](DIH-2_module-system.md).** The app stays in `INSTALLED_APPS` always (D-2: *installed, not wired*); `DIH_MODULES` (comma-separated env var, unset = all on) decides whether its URLs are wired. The per-client wizard (`SiteConfig.modules`, DIH-9) narrows within what the env allows: `effective = env_allows ∧ wizard_enabled`.
- **Off →** `/api/v1/geonode/*` returns **404** (module disabled), Eswatini (on) is unchanged.

**How the pipeline knows whether to push — config, not status-probing.** The CDI→hub push is a pipeline step (`job_05_sync_to_portal.sh`, ported in CDP-0; the current `cdi/job.sh` only runs `job_00..04`). It is **gated by env**: it POSTs only when `DROUGHTMAP_HUB_URL` + `DROUGHTMAP_HUB_API_KEY` are set in `cdi/.env`; unset → it skips silently. The pipeline never *probes* the hub to decide — the enable/disable signal is configuration. Auth is an **API key** (`HasApiKey`), never HTTP-status branching: a `400`/`404`/auth error must not be reinterpreted as "module disabled".

**Where CDI output goes:** raster GeoTIFFs always live in **GeoNode** (the pipeline's `job_04` uploads them there regardless of the hub). The push step only syncs **metadata** into the hub's `PublicationGeonode` cache so the read path (`CDIGeonodeAPI.get`) serves it without calling GeoNode live. Module off (or hub unconfigured) → no metadata reaches the hub; the rasters sit in GeoNode, unreferenced. There is one explicit fallback — **when GeoNode itself is down**, the pipeline pushes pre-computed raster values straight to `POST /geonode/publications/{pk}/rasters` so hub reads survive — but that is a deliberate GeoNode-down path, **not** triggered by a push status code. For map downloads the hub streams from GeoNode on demand into `tmp_dir` (see §3), not a permanent store.

> **Honest framing:** for any live-CDI deployment, `geonode` is effectively **core** — a CDI client needs somewhere to put rasters, and that is GeoNode. The module is extracted into its own app for **swappability** (replace GeoNode with another store later) and **testability** (gate it off in `CoreOnlyTestCase`), **not** because a real CDI instance would run with it off. Document it as optional-in-architecture, core-in-practice.

## 3. Persistent storage for hub-local files (prepared from the start)

Separate from GeoNode rasters, the hub writes two kinds of its **own** files to ephemeral or code-coupled paths. Fix this in the same task so a new deployment is durable from day one:

| What | Where today | Problem |
|---|---|---|
| Map-download exports | `tmp_dir = "./tmp"` (`v1_jobs/job.py:28`), streamed from GeoNode on demand | inside the container; lost on restart/rebuild |
| Organization logos | `MEDIA_ROOT = BASE_DIR/media` (`Organization.logo`, `upload_to='organization_logos/'`) | persists only via the `./backend:/app:delegated` mount of the whole code tree; a clean prod deploy (image COPYs code, no such mount) loses uploads |

**Fix (mirror Akvo `african-bamboo-dashboard@c22321f` — same env name + `:delegated` bind, so ops stays consistent):**

- `settings.py`: `STORAGE_PATH = environ.get("STORAGE_PATH", "./storage")`; `MEDIA_ROOT = Path.joinpath(Path(STORAGE_PATH), "media")` (keep `MEDIA_URL = "/media/"`).
- `v1_jobs/job.py:28`: `tmp_dir = os.path.join(settings.STORAGE_PATH, "tmp")` (was `"./tmp"`) — durable + shared across `backend`/`worker`.
- `app/docker-compose.yml`: add `STORAGE_PATH=$STORAGE_PATH` to `backend` + `worker` `environment`, and mount on both:
  ```yaml
  volumes:
    - ${STORAGE_PATH:-./storage}:/app/storage:delegated
  ```
- `app/docker-compose.test.yml`: `STORAGE_PATH=./storage`. `.env.example` (+ `configure.sh` if it templates env): `STORAGE_PATH=./storage`. `app/storage/.gitignore`: `*` + `!.gitignore`.
- Prod serves `/media/` via the existing reverse proxy (`traefik/`) — only the root moves under `STORAGE_PATH`.

## 4. Scope

This task was **specified in CDP-0 but built in E2** (this branch). Despite CDP-0 §3/D-4, `api/v1/v1_geonode` did **not** exist at E2 start — the push/read code still lived in `v1_publication` (`CDIGeonodeAPI`). E2 therefore did a full greenfield extraction, not a finish-off: new app, `PublicationGeonode` cache, `HasApiKey`, cache-backed read, and the `sync_publication_geonodes` backfill. See §11 for the shipped result.

## 5. Approach (summary; detail in CDP-0)

- New app `api/v1/v1_geonode`, extracted from the eswatini-v2 `v1_publication`:
  - **Write (pipeline, `HasApiKey`)**: `POST geonode/publications` (steady-state metadata sync) + `POST geonode/publications/{pk}/rasters` (GeoNode-down fallback: pre-computed raster values).
  - **Cache model** `PublicationGeonode` (one row per GeoNode resource; `geonode_id` unique) so reads survive GeoNode downtime; migration to create it.
  - **Read path** `CDIGeonodeAPI.get` reads the cache (generic repo today pulls GeoNode live — this port moves it to cache-backed).
  - **Backfill** `sync_publication_geonodes` management command for history/recovery.
- Gated by `DIH_MODULES` (default on) via [DIH-2](DIH-2_module-system.md). Off → endpoints 404; the pipeline push is separately env-gated (`DROUGHTMAP_HUB_URL`/`_API_KEY`, §2).
- Persistent storage: see §3 (`STORAGE_PATH` + `MEDIA_ROOT`/`tmp_dir` repointed + docker-compose volume).

## 6. Decisions

- Carried from CDP-0 D-4 / OQ-2: standalone optional app, not folded into `v1_publication`; the ported sync job POSTs to it.
- `geonode` is optional in architecture but core in practice (see §2); it is extracted for swap/testability, and `DIH_MODULES` is the only toggle.
- Hub-local persistence mirrors Akvo `african-bamboo-dashboard@c22321f` (`STORAGE_PATH` + `:delegated` bind) rather than a new scheme, so ops stays consistent across Akvo projects (§3).

## Implementation steps

**Phase 1a — `v1_geonode`:**
1. Scaffold `api/v1/v1_geonode` (`apps.py`, empty `urls/views/serializers`), add to `INSTALLED_APPS`. → verify: `manage.py check` clean.
2. Port the `PublicationGeonode` cache model from eswatini-v2 + migration. → verify: `makemigrations` creates it; `migrate` forward **and** back clean.
3. Extract the two push views + serializers (`HasApiKey` auth) from eswatini-v2 `v1_publication`. → verify: unit test — both POSTs upsert cache rows with a valid key, 403 without.
4. Wire a conditional URL include via `module_enabled("geonode")` (DIH-2). → verify: `geonode` off → `POST /api/v1/geonode/publications` 404; on → routed.
5. Switch `CDIGeonodeAPI.get` to read the cache; add the `sync_publication_geonodes` backfill command. → verify: read works with GeoNode mocked unreachable; backfill repopulates the cache.

**Phase 1b — persistent storage:**
6. `settings.STORAGE_PATH`; repoint `MEDIA_ROOT` and `v1_jobs/job.py:28` `tmp_dir` under it. → verify: `python -c` prints `MEDIA_ROOT` inside `STORAGE_PATH`.
7. docker-compose volume on `backend`+`worker` + `.env.example` + `app/storage/.gitignore`. → verify: an uploaded logo survives `docker compose restart backend`; a `worker`-written export is readable by `backend`.

## User acceptance criteria

- As an **operator**, I can turn GeoNode off for a deployment via one env var and the app + pipeline behave predictably — endpoints 404, the pipeline push skips — with no crash or half-wired state.
- As an **operator**, organisation logos I upload and map-download exports survive a container restart/redeploy (they persist on a volume, not in ephemeral storage).

## 7. Technical acceptance criteria

**7a — `v1_geonode`:**
- [ ] `v1_geonode` exists as its own app, gated by `DIH_MODULES`.
- [ ] With `geonode` off, the endpoints return 404 and the pipeline sync is inert; Eswatini (on) is unchanged.
- [ ] `DIH_MODULES` is read from env; the wizard (`SiteConfig.modules`) can only narrow within it, never widen.

**7b — persistent storage:**
- [ ] `MEDIA_ROOT` and the map-download export dir both resolve under `STORAGE_PATH` (default `./storage`); no `.env` change needed for existing dev.
- [ ] An uploaded `Organization.logo` survives a `backend` rebuild/restart; a `worker`-written export is readable by `backend` after a restart (shared volume).

**Verify by (goal-driven):**
1. `override_settings(DIH_MODULES=[...without "geonode"])` → `POST /api/v1/geonode/publications` returns 404; with it on, a mocked pipeline push creates a `Publication`.
2. Upload a logo via the setup wizard → `docker compose restart backend` → logo still served. Enqueue a map download on `worker` → the file under `STORAGE_PATH/tmp` is readable by the `backend` download endpoint after a restart.

## Phases (≤8h each)

| Phase | Effort | Scope | Technical acceptance |
|---|---|---|---|
| **1a** `v1_geonode` | ~6h | Extract geonode push/fetch endpoints into the optional app, gated by `DIH_MODULES` (built with CDP-0) | §7a: app exists + gated; off → 404 + inert sync; env-driven toggle |
| **1b** storage | ~3h | `STORAGE_PATH` env → `MEDIA_ROOT`/`tmp_dir` + docker-compose volume on `backend`/`worker` | §7b: logos + exports survive restart; shared volume; default `./storage` |

## 8. Dependencies / hand-offs

- Build target + full spec: [CDP-0](../1-cdi-data-pipeline/CDP-0_port-eswatini-pipeline.md).
- Gating helper: [DIH-2](DIH-2_module-system.md).
- Per-country GeoNode category prefixing: MC-1 OQ-3.

## 9. References

- [CDP-0](../1-cdi-data-pipeline/CDP-0_port-eswatini-pipeline.md) D-4 + §3; [MC-1](README.md) §6 module matrix.
- Eswatini-hub source: `v1_publication/views.py:167` (`CDIGeonodeAPI`), `cdi/src/background-jobs/job_04_upload_to_geonode.sh`, `v1_jobs/job.py:156` (`download_geonode_dataset`).

## 10. Open questions (geonode on/off, surfaced during E2 verification)

GeoNode on/off is a **provision-time, set-once** decision (geonode is core-in-practice), which right-sizes these. Resolved items are recorded for context.

- **OQ-1 — pre-computed values at publication create (RESOLVED in E2).** `cdi_geonode_id` is now `null=True` and `CreatePublicationSerializer.download_url` is optional. `perform_create` branches: with a `cdi_geonode_id` + `download_url` it keeps the old GeoNode download→recompute→notify chain; without them it trusts the `initial_values` supplied in the request and notifies reviewers directly (the shared `notify_reviewers` helper, extracted from `generate_initial_cdi_values_results`). `validate()` requires `initial_values` when `cdi_geonode_id` is absent. A publication can now be created with no GeoNode at all; the values come from the request, not a post-create `PublicationRaster`. (Covered by `test_create_publication_without_geonode_id` + `test_create_requires_values_without_geonode_id`.)
- **OQ-2 — seeders assume GeoNode (low priority).** `publications_seeder` and `fake_*_seeder` hit `GEONODE_BASE_URL`. Make the `fake_*` seeders self-contained (synthetic data, no GeoNode) and guard the real `publications_seeder` behind `module_enabled("geonode")`. Dev tooling; fix when it bites.
- **Resolved E2:** backend route gate is env/startup by nature (urlconf builds once), so `DIH_MODULES` is the authoritative backend knob; `default_modules()` now derives `SiteConfig.modules` from `module_enabled()` so the wizard/frontend match it (set once at provisioning via `DIH_MODULES`). `PublicationRaster` is the GeoNode-**down** fallback (module ON), not a geonode-off mode — so sharing the geonode gate is correct (documented on the model).

## 11. What shipped (E2)

Backend (`app/backend/api/v1/v1_geonode/`, new app):
- Models `PublicationGeonode` (metadata cache, `geonode_id` unique, `save()` normalises `year_month`) + `PublicationRaster` (GeoNode-**down** fallback values, FK→`Publication`).
- `HasApiKey` (in `utils/custom_permissions.py`; `settings.X_API_KEY` + `X_API_KEY_HEADER`). Push views `GeonodePublicationPushAPI` + `GeonodeRasterPushAPI`; cache-backed read `CDIGeonodeAPI` (relocated from `v1_publication`, route `admin/cdi-geonode` kept). Backfill command `sync_publication_geonodes`.
- URL include gated by `module_enabled("geonode")` → off = 404.
- **OQ-1 done:** `cdi_geonode_id` optional + geonode-less create path (§10).
- **Category rename landed** (was deferred): `cdi/spi/evi2/esi/sm` across the pipeline (`upload_to_geonode_job.py`, `sync_geonode_publications_job.py`), the GeoNode seeder (`geonode/src/cdi/.../add_cdi_categories.py`), and the hub `CDIGeonodeCategory`. `RasterIndicatorTypes` (`PublicationRaster.indicator_type`) still carries `lst/ndvi/spi` — not exercised by the sync; renaming it needs a migration, left for when a raster push needs it.
- **Migrations squashed** (pre-deploy): `v1_publication` and `v1_geonode` each collapsed to a single `0001_initial`.

Storage (§3): `STORAGE_PATH` → `MEDIA_ROOT` + `v1_jobs/job.py tmp_dir`; `:delegated` volume on `backend`+`worker`; `app/storage/.gitignore`.

Frontend (DIH-3): `useModule()` gates the publications page, filters, and the "Open in Geonode" map item. **Plumbing fix:** the client context never carried `modules` off the setup flow, so `useModule` always fell back to "all on" — `AppContextProvider` now seeds `appConfig` from the server cookie (`layout.js` passes it) and `middleware.js` refreshes a cookie that predates the `modules` flag. See [DIH-3](DIH-3_module-flags-frontend.md).

Provisioning (`configure.sh`): aligned with current consumers — `DB_SCHEMA=dmh_app`, `STORAGE_PATH`, `X_API_KEY` (matched to the pipeline's `DROUGHTMAP_HUB_API_KEY`), the NDMC download scheme, the current `cdi_project_settings.json` schema, and `create-envfile.py --hostname` so GeoNode's `server_name`/`ALLOWED_HOSTS` match the chosen domain.
