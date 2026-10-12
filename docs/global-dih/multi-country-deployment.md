# Feature Design Document

## Feature: Multi-country deployment — CDI core + pluggable country modules

**Task ID**: MC-1
**Author**: Iwan Firmawan (with Claude)
**Date**: 2026-09-30
**Status**: Draft
**Depends on**: [`cdi-inhouse-percentiles.md`](cdi-inhouse-percentiles.md) (MC-2). Without it, no country outside NDMC's `Southern_Africa` extent has a CDI to publish.
**Scope note**: this doc is cross-cutting. It touches all three tracks but adds no new track. It is kept at the `docs/` root for that reason.

---

## 1. Context & Problem Statement

```
Currently:
- DIH is built for one country. The only thing future countries are guaranteed
  to share is the CDI output (publication → review → validation → publish).
- Everything around that core assumes Eswatini:
  - Weather stations, IKS, risk level and exposure indicators are always on.
  - v1_publication imports v1_weather directly to compute the reviewer
    confidence score.
  - Admin geometry is read from 9 hard-coded paths to source/eswatini.topojson.
  - Agro-ecological zones are a Python enum of the six Eswatini zones.
  - "Inkhundla"/"Tinkhundla" appears 333 times in the frontend (74 files) and
    287 times in the backend (67 files).
- There are no feature flags anywhere.

Goal:
- One codebase, one instance per country.
- The CDI core always runs.
- Weather stations, IKS, risk level and exposure indicators become modules that
  a deployment switches on or off.
- Country content (boundaries, zones, labels, playbook/SOPs) comes from a
  per-deployment folder owned by the team, not from code.
- A client can bring its own admin-level data, shown only in Insights.
```

**Decisions already taken (brainstorm, 2026-09-30):**

| # | Decision |
|---|---|
| B-1 | The business needs every country covered. The CDI pipeline is the first blocker (→ MC-2). |
| B-2 | Client data is forced into one shape: a table per admin unit per month. |
| B-3 | Confidence **requires** weather stations. No stations means the reviewer map shows review progress only. |
| B-4 | Country config and content are owned by the team via config. There is no admin UI for it. |
| B-5 | This is future-proofing. No second country is committed yet. |
| B-6 | Client data appears only in the Insights tab. It never feeds review or validation. |
| B-7 | IKS and risk level must be switchable too, not only weather. |

**Measured coupling this design must honour** (code read on 2026-09-30):

| Core file | Depends on | What breaks with the module off |
|---|---|---|
| `v1_publication/review/utils.py:18-25` | `v1_weather.confidence` | reviewer map `confidence`, `filter_rows` band filter (`:313`), `_tally` high confidence (`:356`), which drives bulk-accept |
| `v1_publication/validation/utils.py:25` | `build_rows` → `v1_weather` (indirectly) | validation queue rows |
| `v1_publication/brief/situation.py:12-14` | `v1_iks.utils`, `v1_risk_level.service` | brief situation block |
| `v1_insights/services.py:16-26` | `v1_weather`, `v1_iks.utils` | national overview and insights |
| `v1_insights/map_layers.py:29` | `v1_indicators.Indicator` | overview map layers |
| `v1_activity/trigger_evaluation.py:24-30` | `v1_indicators` | SOP trigger evaluation |
| `v1_users/views.py:42`, `admin.py:10` | `v1_weather.citizen_science` | observer magic link |
| `v1_risk_level/service.py:3-7` | `v1_indicators` | risk level cannot exist without indicators |
| `frontend/.../InsightsShell.js:90` | `/iks/aggregations/soil-trend` | the header date is fetched even when the IKS tab is hidden |
| `backend/job.sh:30-77` | weather, CHIRPS, AgERA5, citizen-science jobs | these run unconditionally |

**Prior art: the generic Drought-map Hub** (`akvo/drought-map-hub`, Sep 2025, deployed at least for Kenya). DIH descends from this repo, which was already built to be country-agnostic. Its lessons:

| It did | Keep? | Why |
|---|---|---|
| A web setup wizard (`v1_setup`, `SiteConfig`: name, country, GeoJSON upload, `map_name_key`, centroid) | **No.** Use the file config instead (B-4). | The wizard stored country state in the DB behind an admin UI. B-4 puts the team in charge via config, so a file is simpler and can be reviewed in git. |
| `utils/geojson_processor.py:31-78`: GeoJSON → TopoJSON, auto-numbering `administration_id` 1..n | **Yes**, as a management command | Onboarding a country starts from whatever boundary file the client has. |
| `v1_setup/views.py:294-329`: snaps the country bbox outward to 0.05° cell centres and writes the CDI pipeline config | **Yes** (→ MC-2) | The pipeline grid must align with source pixel centres (STEP_0100 raises otherwise). |
| Map centre from the centroid, zoom hard-coded to 6 | **No.** Use `fitBounds` (§4.3). | A fixed zoom is wrong for every country but the one it was tuned on. |
| `/config.js` delivers the TopoJSON | Already in DIH | — |
| Hard-coded "Eswatini" left in emails and templates, and `object_name="eswatini"` | Warning | A generic-ification attempt left strings behind. §9 adds a grep check for this. |

The stale comment at `v1_weather/services.py:41-43` says "v1_publication never imports v1_weather". It is false because of `review/utils.py:18`, and should be corrected in the same change.

---

## 2. Requirements

### User Acceptance Criteria
- [ ] A deployment with only the CDI core can run the full cycle: start publication → review → validate → publish → national overview and CDI insights.
- [ ] With `weather` off, the reviewer map has no Confidence/Progress toggle. It shows progress only, and never shows the "No confidence score data yet — check back later" empty state.
- [ ] With `weather` off, the bulk-accept banner does not appear, because there is no high-confidence set to accept.
- [ ] With a module off, its Insights tab, its brief block and its overview layers are absent rather than empty.
- [ ] The admin-unit word ("Inkhundla", "District", …) and its plural come from config everywhere a user reads them.
- [ ] Maps open framed on the deployment's own boundary, with no Eswatini centre or zoom.
- [ ] A client admin-level dataset imported by the team appears as a tab in Insights, as a map and a table per month.
- [ ] Eswatini, with all modules on, behaves exactly as today.

### Technical Acceptance Criteria
- [ ] `DIH_MODULES` defaults to all modules on, so no change is needed in the Eswatini `.env`.
- [ ] Startup fails with `ImproperlyConfigured` when `risk_level` is on and `indicators` is off.
- [ ] URLs of a disabled module are not routed, so they return 404.
- [ ] `backend/job.sh` skips the fetchers of disabled modules.
- [ ] No core module imports an optional module at import time. Every call site is behind `module_enabled()`.
- [ ] All country files are read via `settings.COUNTRY_DIR`. None of the 9 hard-coded `source/eswatini.topojson` paths remain.
- [ ] The full backend and frontend test suites pass with all modules on. A dedicated test class also passes with only the core on.

---

## 3. Data Model Changes

### New Models

```python
# New optional app: api/v1/v1_datasets — client-supplied admin-level data (B-2, B-6).
# Long format on purpose: v1_indicators.Indicator is a fixed-column wide table
# (population, cattle, water_demand, …) with a OneToOne to Administration, so it
# cannot hold data whose columns differ per client.
class AdminDatasetValue(models.Model):
    administration = models.ForeignKey(Administration, on_delete=models.CASCADE)
    dataset = models.SlugField(max_length=50)   # key declared in country.json → datasets
    period = models.DateField()                 # first day of the month
    value = models.FloatField(null=True)        # null = reported missing, never 0

    class Meta:
        db_table = "admin_dataset_values"
        constraints = [
            models.UniqueConstraint(
                fields=["administration", "dataset", "period"],
                name="uniq_admin_dataset_period",
            )
        ]
```

The label, unit, source and description of a dataset live in `country.json` (§4.3), not in the table. They are metadata owned by the team, and repeating them on every row adds nothing.

### Modified Models

| Model | Change | Reason |
|---|---|---|
| `Administration.zone` | Drop `choices=AdministrationZones.choices()`. Keep it as `CharField(max_length=50)`. | Zones become data from `country.json`, and validation moves to the seeder. |
| `AdministrationZones` (constants) | Replaced by `country_zones()`, which reads `country.json` | This enum is the only country vocabulary baked into Python. |

### Migration Strategy

```python
# - Administration.zone: AlterField that only removes choices. There is no data
#   change, and the Eswatini slugs stay valid because country.json lists the
#   same six.
# - v1_datasets: new table, empty by default.
# - Rollback: reverse migrations are trivial (re-add choices, drop the table).
# - Optional modules stay in INSTALLED_APPS even when disabled (§5 D-2), so
#   their tables always exist and FK migrations never break.
```

---

## 4. API Contract

### 4.1 Module flags reach the frontend

`generate_config.py` already writes `source/config/config.min.js`, served at `/api/v1/config.js` and read by `DynamicScript.js` into app context. Three variables are added next to `topojson` and `zones`:

```js
var modules=["weather","iks","risk_level","indicators","datasets"];
var country={"name":"Eswatini","admin_label":{"one":"Inkhundla","many":"Tinkhundla"}};
var datasets=[{"key":"ndvi_anomaly","label":"NDVI anomaly","unit":"%","source":"…"}];
```

`DynamicScript` dispatches `SET_MODULES`, `SET_COUNTRY` and `SET_DATASETS`. A small `useModule("weather")` hook reads the flags.

### 4.2 Endpoints

| Method | URL | Purpose | Auth |
|---|---|---|---|
| GET | `/api/v1/config.js` | *(existing)* now also carries `modules`, `country`, `datasets` | Public |
| GET | `/api/v1/reviewer/{id}/map` | *(existing)* with `weather` off, `confidence` is `null` on every row and `meta.confidence_enabled` is `false` | Reviewer |
| GET | `/api/v1/datasets/{key}?period=YYYY-MM` | One client dataset for one month, per admin unit | Public (Insights is public) |
| GET | `/api/v1/datasets/{key}/periods` | Months available for a dataset | Public |

```json
// GET /api/v1/datasets/ndvi_anomaly?period=2026-08
{
  "meta": { "key": "ndvi_anomaly", "label": "NDVI anomaly", "unit": "%", "period": "2026-08" },
  "data": [
    { "administration_id": 12, "value": -14.2 },
    { "administration_id": 13, "value": null }
  ]
}
```

The shape follows the house mock contract (`key`, `label`, `value`, `data`, `meta`). No UI-specific names are used.

### 4.3 Country folder (`COUNTRY_DIR`, default `backend/source/`)

`backend/source/` already holds every country file. It becomes the country pack, mounted per deployment:

| File | Today | After |
|---|---|---|
| `admin.topojson` | `eswatini.topojson` | renamed; must carry `administration_id`, `name`, `region` |
| `zones.topojson` | `eswatini-ecological_regions*.topojson` | renamed and optional; no zones means the zone filter is hidden |
| `regions.topojson` | `eswatini-region.topojson` | renamed |
| `climatic-zones.json` | as is | as is (still generated by `assign_administration_zones`) |
| `activity_library.csv`, `priority_areas.csv`, `iks_kobo_catalogue.csv`, `30years/` | as is | as is; the playbook/SOP content is already data |
| `country.json` | — | **new**: name, `admin_label`, zones `[{value,label,code}]`, region colours, TWG agencies and logos, brief contacts, `datasets` |

Map framing is **derived**, not configured. `CDIMap` and the four copies of zoom 9 (`LayerMap.js:198,277`, `OverviewMap.js:133`, `InkhundlaMap.js:177`) call `fitBounds` on the loaded topojson. This removes `DEFAULT_CENTER` instead of moving it into config.

### 4.4 Client data import (team-run, B-4)

```bash
python manage.py import_admin_dataset ndvi_anomaly path/to/file.csv
# CSV columns: administration_id,period,value      (period = YYYY-MM)
```

- The import is idempotent: an upsert on (administration, dataset, period).
- It fails loudly on an unknown `administration_id` or an undeclared `dataset` key.
- It reports how many rows were inserted, updated and rejected.

There is no upload endpoint.

---

## 5. Decision Log

### D-1: One instance per country
**Options**:
1. One instance per country, with a shared codebase.
2. Multi-tenant, with a country FK on every table.

**Decision**: 1.

**Rationale**: this is how Eswatini runs today. Countries never share users, publications or reviewers. Multi-tenancy would touch every query and permission for no current need (B-5).

**Impact**: a new country means a new `.env` plus a new `COUNTRY_DIR`, and no code change.

### D-2: A disabled module stays installed and is simply not wired
**Options**:
1. Remove disabled apps from `INSTALLED_APPS`.
2. Keep them installed, and gate URLs, jobs, call sites and the UI.

**Decision**: 2.

**Rationale**: every optional app has an FK to `Administration`, and several core files import them. Uninstalling an app breaks migrations and imports. Keeping the tables costs nothing: an empty table is inert.

**Impact**: one `module_enabled(name)` helper in `utils/`. `eswatini/urls.py` includes an app's urls only when that app is enabled. `job.sh` checks the same flag.

### D-3: Core call sites guard, they do not plug in
**Options**:
1. A provider/registry interface (e.g. "evidence providers" for confidence).
2. An `if module_enabled(...)` guard with a local import at each of the 8 call sites in §1.

**Decision**: 2.

**Rationale**: there is exactly one confidence source (stations, B-3) and exactly one of each other module. A registry with one implementation per slot is abstraction for its own sake.

**Impact**: `review/utils.py` returns `confidence=None` and `meta.confidence_enabled=false` when weather is off. `filter_rows` ignores band filters, `_tally` returns 0 high-confidence, and the bulk-accept banner stays hidden.

**Revisit when**: a second, non-station confidence source is actually agreed.

### D-4: Admin label lives in `country.json`, delivered via `config.js`
**Decision**: `country.admin_label.{one,many}`, read through a `useAdminLabel()` hook in the frontend and `settings.COUNTRY["admin_label"]` in the backend. The replacement covers only user-visible strings: UI copy, emails, and the PDF brief.

**Rationale**: of the 333 frontend matches, many are comments or variable names such as `InkhundlaHeader`. Renaming identifiers adds risk and does nothing for users.

**Impact**: this is the largest mechanical piece of work, so it is split out as its own task (§11).

### D-5: Client data is a long table in its own optional app
**Decision**: a new `v1_datasets` app with the `AdminDatasetValue` table (§3).

**Rationale**: `v1_indicators` is wide and has fixed columns. B-2 fixes the shape as admin × month × value. B-6 keeps it out of review and validation, so it needs no link to `Publication`.

**Impact**: one generic Insights tab lists `datasets` from `config.js`, then renders a choropleth plus a table for each key and month.

### D-6: No stations means progress only, not an empty state
**Decision**: `REVIEW_MAP_MODE` drops `confidence` when `!useModule("weather")`. The toggle at `ReviewQueue.js:254-261` is not rendered, and the default at `:51` becomes `progress`.

**Rationale**: `EmptyConfidence` promises the data will come ("check back later"). For a country with no stations, that is a false promise (B-3).

---

## 6. Type/Constant Mappings

| Module flag | Django app(s) gated | Frontend surface gated | Scheduled jobs gated |
|---|---|---|---|
| *(core, always on)* | `v1_init`, `v1_jobs`, `v1_users`, `v1_publication`, `v1_activity`, `v1_rundeck`, `v1_insights` | review, validation, CDI insights, national overview, SOP library | — |
| `weather` | `v1_weather` | Weather tab, confidence map mode, bulk-accept, citizen-science, brief weather block | WIS2 fetch, CHIRPS observations, AgERA5, CS reminders |
| `iks` | `v1_iks` | IKS tab, the `soil-trend` header call, brief IKS block | Kobo download |
| `indicators` | `v1_indicators` | exposure overview layers, dataset uploads | dataset upload jobs |
| `risk_level` (requires `indicators`) | `v1_risk_level` | Risk level tab, brief risk block | — |
| `datasets` | `v1_datasets` | generic "Other data" Insights tab | — |

`DIH_MODULES` is a comma-separated env var. If it is unset, all modules are on.

---

## 7. Compatibility & Migration

### Backward Compatibility
- [ ] The Eswatini deployment needs no `.env` change, because the defaults are all modules on and `COUNTRY_DIR=source/`.
- [ ] The renamed files in `source/` are moved with `git mv` in the same PR as the path change. Restart the backend afterwards, because the delegated mount serves stale content after a rename.
- [ ] Existing API responses are unchanged when all modules are on. `meta.confidence_enabled` is additive.

### Seeder/CLI Compatibility
- [ ] `generate_administrations_seeder`, `assign_administration_zones`, `generate_config`, the IKS seeders, `download_iks_data` and `fetch_chirps_monthly` all read via `COUNTRY_DIR`.
- [ ] New: `import_admin_dataset`.
- [ ] `seed_demo` seeds only the modules that are enabled.

---

## 8. Security Considerations

- [ ] A disabled module has no routes, so it adds no attack surface. This is better than returning 403 from a routed view.
- [ ] Client data enters only through a team-run management command. There is no new upload endpoint and no file parsing in the web process.
- [ ] `import_admin_dataset` validates every `administration_id` and dataset key against the DB and `country.json`, and rejects unknowns instead of creating them.
- [ ] The datasets API is read-only and public, like the rest of Insights. Do not import sensitive client data; state this in the import command's help text.

---

## 9. Testing Strategy

| Test Type | Coverage |
|---|---|
| Unit | `module_enabled` parsing and defaults. The `risk_level` without `indicators` configuration error. `country.json` loading. `import_admin_dataset` upsert, rejects and null handling. |
| Integration | A `CoreOnlyTestCase` using `override_settings(DIH_MODULES=[])`. It checks that the reviewer map returns `confidence: null` and `confidence_enabled: false`, that validation rows build, that the brief builds without IKS or risk blocks, that the national overview loads, that weather, IKS and risk URLs return 404, and that `config.js` lists no modules. |
| Frontend | `ReviewQueue`: no toggle and progress mode when weather is off. `InsightsShell`: tabs filtered and no `soil-trend` call when IKS is off. `useAdminLabel` renders the configured word. |
| Leak check | A CI grep that fails on `eswatini|Eswatini|Inkhundla|Tinkhundla` in user-visible frontend strings and in email or PDF templates (allow-list: `source/`, tests, comments). The generic hub regressed exactly here. |
| E2E (manual) | Boot with `DIH_MODULES=` and a non-Eswatini `COUNTRY_DIR` fixture (e.g. 3 fake polygons), then walk the publish cycle. |

---

## 10. Open Questions

> **MC-1 execution approach (decided 2026-10-12, CDP-0 OQ-3):** no wholesale app move. Port the backend APIs first (starting with `v1_geonode` in CDP-0), then port the frontend iteratively to strip Eswatini hardcoding. One instance per country (D-1); `eswatini-droughtmap-hub` and this generic hub run in parallel.

- [x] **OQ-1**: Should `v1_activity` (SOP library and triggers) be optional too? Today it is core, but its triggers read `v1_indicators`. Proposed answer: keep it core, and when indicators are off, skip only the indicator-based triggers. **— RESOLVED 2026-10-12 (direction): keep `v1_activity` core; when indicators are off, skip only the indicator-based triggers. Build during the incremental MC-1 porting.**
- [ ] **OQ-2**: Brief PDF: when every optional module is off, is a CDI-only brief still useful, or should the brief itself become optional? **— DEFERRED to MC-1 execution; recommendation: keep a CDI-only brief (do not make the brief itself optional).**
- [x] **OQ-3**: The Rundeck and GeoNode wiring assumes one pipeline run per country (MC-2 already supports feeding several portals). Should the `GEONODE_*` categories become prefixed per country if two countries share one GeoNode? **— RESOLVED 2026-10-12: yes, prefix `GEONODE_*` categories per country — the one-VM/one-config model (MC-2 OQ-5) means countries can share a GeoNode.**
- [ ] **OQ-4**: Translation: is English UI copy acceptable for all target countries? The admin label is only the first localisation seam. **— DEFERRED to MC-1 execution; recommendation: English UI acceptable initially; `admin_label` is the first localisation seam.**

---

## 11. Work Breakdown

Ordered cheapest and most useful first. Tasks 1–3 are the "future-proofing now" slice (B-5). Tasks 4–7 wait until a second country is real.

| # | Task | Size |
|---|---|---|
| 1 | `module_enabled` + `DIH_MODULES` + gated URLs and `job.sh`; guard the 8 core call sites; fix the stale comment | M |
| 2 | Weather-off reviewer UX: progress-only map, no bulk-accept, `meta.confidence_enabled` | S |
| 3 | Module flags through `config.js`; Insights tabs, brief blocks and overview layers respect them | M |
| 4 | `COUNTRY_DIR` + generic file names in `source/`; `country.json` for zones, region colours, TWG and contacts; drop `AdministrationZones` choices; port `geojson_processor` from the generic hub as `import_admin_boundary <geojson> --name-key` | M |
| 5 | Map framing from topojson bounds (`fitBounds`); remove `DEFAULT_CENTER` and the four copies of zoom 9 | S |
| 6 | Admin label from config across user-visible UI, email and PDF copy | L (mechanical) |
| 7 | `v1_datasets`: model, `import_admin_dataset`, API, generic Insights tab | M |

---

## 12. References

- Pipeline prerequisite: [`cdi-inhouse-percentiles.md`](cdi-inhouse-percentiles.md) (MC-2)
- Confidence design: [`track-3/weather-satellite-temperature-confidence.md`](https://github.com/akvo/eswatini-droughtmap-hub/blob/main/eswatini-v2/docs/track-3/weather-satellite-temperature-confidence.md) (WX-11), [`specs/WX-2_review_confidence_deltas.md`](https://github.com/akvo/eswatini-droughtmap-hub/blob/main/eswatini-v2/docs/specs/WX-2_review_confidence_deltas.md)
- Review queue: [`track-2/drought-review-queue.md`](https://github.com/akvo/eswatini-droughtmap-hub/blob/main/eswatini-v2/docs/track-2/drought-review-queue.md)
- Boundary provenance: [`track-3/inkhundla-boundary-provenance.md`](https://github.com/akvo/eswatini-droughtmap-hub/blob/main/eswatini-v2/docs/track-3/inkhundla-boundary-provenance.md)
- Wide indicator table: [`specs/PA-1_v1_indicators.md`](https://github.com/akvo/eswatini-droughtmap-hub/blob/main/eswatini-v2/docs/specs/PA-1_v1_indicators.md)
- Prior art: generic Drought-map Hub — `github.com/akvo/drought-map-hub` (setup wizard `app/backend/api/v1/v1_setup/`, `app/backend/utils/geojson_processor.py`)

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | | | |
| Tech Lead | | | |
| Product | | | |
