# Feature Design Document

## Feature: Country pack — per-tenant pack dir, `country.json`, boundary import

**Task ID**: DIH-4
**Author**: Iwan Firmawan (with Claude)
**Date**: 2026-10-30
**Status**: Draft
**Effort**: ~7h (incl. agentic coding).
**Depends on**: [DIH-2](DIH-2_module-system.md), [MT-1](../3-multi-tenancy/MT-1_tenant-model-scoping.md) (tenant resolver)

> Eswatini-hub file:line refs; re-map to `drought-map-hub/app` when executing.

---

> **Multi-tenancy (WS-3):** `COUNTRY_DIR` is **removed** (D-MT-1) — the country is resolved from `request.tenant`, not an env path, so the "pick one of `source/india|indonesia|kenya`" idea no longer exists. The country pack is **per-tenant**: a `SiteConfig` row ([MT-1](../3-multi-tenancy/MT-1_tenant-model-scoping.md)) + a boundary/zones pack uploaded during **self-service onboarding** ([MT-6](../3-multi-tenancy/MT-6_self-service-onboarding.md)), stored at `STORAGE_PATH/tenants/<subdomain>/`. Standalone deploy = the `default` tenant's pack.

## 1. Context

Country content is baked into code/paths: admin geometry is read from 9 hard-coded `source/eswatini.topojson` paths, and agro-ecological zones are a Python enum of the six Eswatini zones. Move country content to a per-tenant folder the team owns (MC-1 B-4), not code.

## 2. Scope

The country **data pack** + onboarding import. The frontend map framing that follows from a new boundary is [DIH-5](DIH-5_map-framing.md); the admin-unit label is [DIH-6](DIH-6_admin-label.md).

## 3. Approach + files

Country files are resolved from the **tenant's pack directory**, not a global path. A small helper `tenant_source_dir(tenant)` returns `STORAGE_PATH/tenants/<subdomain>/` (see [MT-1](../3-multi-tenancy/MT-1_tenant-model-scoping.md) / [MT-6](../3-multi-tenancy/MT-6_self-service-onboarding.md)); the `default` tenant resolves to `source/`, so standalone deploys are unchanged. This one seam replaces the 9 hard-coded `source/eswatini.topojson` paths. It selects only the **file pack**, never the database — each tenant's Postgres rows (`Administration` seeded from the boundary, publications, users) are already scoped by [MT-1](../3-multi-tenancy/MT-1_tenant-model-scoping.md). The tenant's country pack:

| File | Today | After |
|---|---|---|
| `admin.topojson` | `eswatini.topojson` | renamed; carries `administration_id`, `name`, `region` |
| `zones.topojson` | `eswatini-ecological_regions*.topojson` | renamed, optional (no zones → zone filter hidden) |
| `regions.topojson` | `eswatini-region.topojson` | renamed |
| `climatic-zones.json`, `activity_library.csv`, `priority_areas.csv`, `iks_kobo_catalogue.csv`, `30years/` | as is | as is (already data) |
| `country.json` | — | **new**: name, ~~`admin_label`~~, zones `[{value,label,code}]`, region colours, TWG agencies + logos, brief contacts, `datasets` |

> **Note (#24):** `admin_label` was split out of `country.json` and now lives in **`SiteConfig.admin_label`**, set in the setup wizard (DIH-6 / DIH-9). `country.json` keeps the rest (zones, region colours, agencies, contacts, `datasets`).

- All country files read via `tenant_source_dir(request.tenant)` — none of the 9 hard-coded paths remain.
- **Model**: `Administration.zone` drops `choices=AdministrationZones.choices()` → plain `CharField(max_length=50)`; the `AdministrationZones` enum is replaced by `country_zones()` reading `country.json`. Migration = `AlterField` removing choices only (no data change; Eswatini slugs stay valid). Reversible.
- **Boundary import** (team-run, B-4, or invoked by onboarding MT-6): port the generic hub's `utils/geojson_processor.py:31-78` (GeoJSON → TopoJSON, auto-number `administration_id` 1..n) as a management command `import_admin_boundary <geojson> --name-key --tenant <subdomain>` (writes into that tenant's pack).
- Renamed `source/` files moved with `git mv` in the same PR; restart backend after (delegated mount serves stale content after a rename).

## 4. Decisions

- MC-1 B-4 (team-owned config, no admin UI). Under multi-tenancy the country is chosen by `request.tenant`, never an env path (D-MT-1 — `COUNTRY_DIR` removed entirely). Each tenant has its own pack dir resolved by `tenant_source_dir()`; the `default` tenant = `source/` keeps standalone unchanged. `AdministrationZones` is the only country vocabulary baked into Python → removed.

## Implementation steps

1. Add `tenant_source_dir(tenant)` helper (returns `STORAGE_PATH/tenants/<subdomain>/`; `default` → `source/`). → verify: resolves per tenant; `default` tenant = Eswatini `source/` unchanged.
2. `git mv` `source/eswatini*.topojson` → generic `admin.topojson` / `zones.topojson` / `regions.topojson` (the `default` tenant's pack); restart backend (delegated mount serves stale after a rename). → verify: renamed files served.
3. Repoint the 9 hard-coded `source/eswatini.topojson` reads to `tenant_source_dir(request.tenant)`. → verify: grep finds zero `source/eswatini.topojson`.
4. Add `country.json` + loader `country_zones()`; change `Administration.zone` to a plain `CharField` via an `AlterField` migration (drop `choices`, no data change). → verify: `migrate` forward **and** back; zones now come from `country.json`.
5. `import_admin_boundary <geojson> --name-key --tenant <subdomain>` (port `app/backend/utils/geojson_processor.py:31-78`). → verify: unit test numbers `administration_id` 1..n into the tenant's pack.
6. Boot with a fake non-`default` tenant pack (3 polygons + a `country.json`). → verify: seeders/config read it and the publish cycle runs.

## User acceptance criteria

- As an **operator** onboarding a new tenant/country, I drop in a country pack (boundary file + `country.json`) for that tenant and the app serves that country — zones, admin label, region colours, agencies — with **no code change**.
- The `default` tenant (Eswatini standalone) keeps working with its existing files untouched.

## 5. Technical acceptance criteria

- [ ] Every country file is read via `tenant_source_dir(request.tenant)`; zero hard-coded `source/eswatini.topojson` paths remain.
- [ ] `country.json` supplies zones, `admin_label`, region colours, TWG + contacts, `datasets`.
- [ ] `import_admin_boundary` turns a client GeoJSON into `admin.topojson` with numbered `administration_id` in the tenant's pack.
- [ ] The `default` tenant needs no change (pack at `source/`, same slugs).

**Verify by (goal-driven):** boot a non-`default` tenant with its own pack (3 fake polygons + a `country.json`) → seeders/config read it via `tenant_source_dir`, zones come from `country.json`, and the publish cycle runs; unit test `import_admin_boundary` numbers `administration_id` 1..n and `Administration.zone` AlterField migrates forward/back.

## 6. Dependencies / hand-offs

- Needs DIH-2 + MT-1 (the `tenant_source_dir` resolver). Feeds DIH-5 (framing from the new boundary) and DIH-6 (`admin_label`). `datasets` metadata feeds DIH-7.

## 7. References

- [MC-1](README.md) §3 (Administration.zone), §4.3, §4.4, §7; prior art `app/backend/utils/geojson_processor.py`.
