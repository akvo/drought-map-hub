# Feature Design Document

## Feature: `Tenant` model + DB scoping + `default` backfill

**Task ID**: MT-1
**Author**: Iwan Firmawan (with Claude)
**Date**: 2026-10-30
**Status**: Draft
**Effort**: ~7h (incl. agentic coding).
**Depends on**: — (foundation for all of WS-3)

> Mirrors Akvo MIS **MT-002**. This repo has **no** tenant concept today; see [WS-3 README](README.md) §3.

---

## 1. Context

Every row in the hub today is global to the instance. To serve many countries from one deployment, tenant-owned tables need a tenant anchor, and existing data must keep working. This task adds the model + the scoping migration only; read/write enforcement is MT-2/MT-3.

## 2. Approach + files

- **`Tenant`** in `v1_users/models.py`: `subdomain` (CharField, unique, the identity), `is_active` (default True), `deleted_at` (nullable, soft delete), `features` (JSONField, default `{}` — the per-tenant module flags that replace `DIH_MODULES`), `language` (default `en`), `logo` (nullable). Country config (name, country, map_center, map_name_key) stays on `SiteConfig`, now one row **per tenant**.
- **Direct tenant FK** (`null=True`, `on_delete=PROTECT`) on the definition roots: `SiteConfig`, `Organization`, `Administration`, `Publication`, `SystemUser` — **plus `Jobs`**, which (verified against the repo) has **no `user`/owner FK**, so it cannot derive and takes a **direct** `tenant` FK. All other tenant-owned models derive via join — no FK added:

  | Model | `TENANT_PATH` | Note |
  |---|---|---|
  | `SiteConfig`, `Organization`, `Administration`, `Publication`, `SystemUser` | `tenant` | direct FK |
  | `Jobs` | `tenant` | **direct FK** — no `user` FK exists to derive from; scope by tenant (add a `created_by` FK later only if per-user ownership is ever needed) |
  | `Review` | `publication__tenant` | derives |
  | `AdminDatasetValue` (DIH-7) | `administration__tenant` | derives; model is new in DIH-7 |
  | GeoNode link | `Publication.tenant` / `Raster.tenant` | DIH-1 **shipped** a core `Raster` (geonode_id unique) + `Publication.raster` OneToOne (not the `PublicationGeonode` cache — superseded). Attribution rides `Publication.tenant`; MT-8 adds `Raster.tenant` for pipeline-pushed rasters not yet tied to a publication. The optional `GeoNodeResource` pointer derives `raster__tenant`. |

- Each model declares `TENANT_PATH` (a class attribute) so MT-2's `for_user()`/`for_tenant()` can resolve it; a model without `TENANT_PATH` is intentionally global.
- **Existing `Organization` primitive**: `SystemUser` already has an `organization` FK (`SET_NULL`), and `Organization` holds the TWG/collaborator agencies. `Tenant` sits **above** `Organization` (one tenant → many organizations); `SystemUser` keeps `organization` and **gains** `tenant`. No conflict — `Organization` is one of the direct-FK roots.
- **Backfill migration**: create `Tenant(subdomain="default")`, stamp every existing row + tenant-less `SystemUser` to it. Idempotent + reversible. Postgres `NULL = NULL` means un-stamped rows still match a tenant-less user, so nothing breaks mid-migration. The `default` tenant is the one a **standalone deployment** runs as — served on the **base domain** ([MT-4](MT-4_subdomain-routing.md) resolves the base domain to `default`, configurable, not forced to `None`), so existing single-tenant installs keep working.
- **Post-backfill nullability**: after the `default` backfill, a follow-up `AlterField` sets `null=False` on the non-user roots (`SiteConfig`/`Organization`/`Administration`/`Publication`/`Jobs`); keep `null=True` only on `SystemUser` (platform admins are tenant-less, MT-10). This closes the silent-orphan window (a forgotten stamp would otherwise create a row no tenant can see).
- **Constraint shifts** (where a global unique becomes per-tenant): `Organization` name uniqueness (if any) → `UniqueConstraint(tenant, name)`; `SiteConfig` one row per tenant. (`SystemUser.email` is MT-5; `cdi_geonode_id` stays global.)

## 3. Implementation steps

1. Add the `Tenant` model to `v1_users` (no FK to it yet). → verify: `makemigrations` creates it; `manage.py check` clean.
2. Add the `tenant` FK (`null=True, PROTECT`) to the 5 roots **+ `Jobs`** + a `TENANT_PATH` attr to every tenant-owned model. → verify: migration builds; no `on_delete` cascade surprises.
3. Data migration: create `Tenant(subdomain="default")` + stamp all existing rows/users. → verify: after `migrate`, every root row has `tenant_id = default`; `migrate` back restores nulls.
4. Per-tenant constraints (Organization/SiteConfig). → verify: two tenants can hold same-named orgs; one `SiteConfig` per tenant.

**Verify (goal-driven):** migration forward **and** back on a seeded DB; a test asserting every `TENANT_PATH`-bearing model resolves its path to a `Tenant`; the legacy suite stays green (tenant-less rows match via `NULL=NULL`).

## 4. User acceptance criteria

- As an **operator**, an existing single-tenant deployment keeps all its data and behaviour — it simply becomes the `default` tenant, no manual data fix.

## 5. Technical acceptance criteria

- [ ] `Tenant` exists with `subdomain` unique; the 5 roots **+ `Jobs`** carry a direct `tenant` FK; all tenant-owned models declare `TENANT_PATH`.
- [ ] Backfill stamps existing rows to `default`; migration is reversible.
- [ ] Full legacy suite passes unchanged (NULL=NULL).

## 6. Dependencies / hand-offs

- Foundation for MT-2 (read), MT-3 (write), MT-4 (routing). Consumes nothing.

## 7. References

- [WS-3 README](README.md) §3; MIS MT-002. Repo models: `v1_users/models.py`, `v1_setup/models.py`, `v1_publication/models.py`, `v1_jobs/models.py`.
