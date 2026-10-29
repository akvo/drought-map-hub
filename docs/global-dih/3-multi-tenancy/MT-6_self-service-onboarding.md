# Feature Design Document

## Feature: Self-service onboarding (two-phase) + auto-issued API key

**Task ID**: MT-6
**Author**: Iwan Firmawan (with Claude)
**Date**: 2026-10-30
**Status**: Draft
**Effort**: ~10h total (incl. agentic coding) → 2 phases ≤8h each: 6a auth/registration ~5h, 6b configure + boundary + key ~5h.
**Depends on**: [MT-1](MT-1_tenant-model-scoping.md), [MT-4](MT-4_subdomain-routing.md), [MT-5](MT-5_email-per-tenant.md); reuses [DIH-4](../2-v2-porting/DIH-4_country-pack.md) boundary import

> Mirrors Akvo MIS **MT-001/006**, plus this app's country-specific configure step. See [WS-3 README](README.md) §9.

---

## 1. Context

A country should be able to stand up its whole **hub** workspace itself — account, subdomain, branding, boundary, modules — without ops. Drought data then starts automatically because the central pipeline (MT-11) discovers the new tenant on its next run.

## 2. Approach + files

**Phase 6a — registration + activation:**
- `POST /api/v1/register` {email, password, subdomain, country name, language}: atomically create `Tenant(subdomain, is_active=False)` + `SystemUser(is_active=False, tenant)` assigned the **top tenant role** (existing roles/abilities system) — **not** Django `is_superuser` (D-MT-7: `is_superuser` bypasses permission checks, so it is reserved for the tenant-less platform operator, MT-10); claim the subdomain; `send_activation_email` with `signing.dumps(user.pk)`. Returns 200 (no token, no enumeration on resend).
- `POST /api/v1/register/activate` {token}: verify signed token (max age ~7d) → `is_active=True`; return auth token + `configured:false`.
- `POST /api/v1/register/resend-activation` {email}: always 200.
- `subdomain` validated (DNS label, reserved words incl. `admin`, `www`, base domain).

**Phase 6b — configure + pipeline key:**
- `POST /api/v1/register/configure` (auth, active-unconfigured): upload **boundary GeoJSON** → `import_admin_boundary` (DIH-4, per-tenant) seeds `Administration` + writes the tenant's `admin.topojson` under `STORAGE_PATH/tenants/<subdomain>/`; set admin label, zones/region colours, brand colour, module selection (`Tenant.features`), TWG orgs/logos; set `SiteConfig` row for the tenant.
- **API key auto-issued** on tenant creation/activation: a `TenantApiKey` row (hashed, revocable) → shown once with the hub URL (for the **external-pipeline** case only; the central pipeline uses a service identity).
- `configured` is a **derived** boolean (tenant has a named level-0 + root `Administration`), not a column; a routing guard forces an unconfigured tenant owner to `/configure`.

## 3. Implementation steps

**6a:** 1. `register` (atomic Tenant+user, claim subdomain, email token). → verify: duplicate subdomain rejected; resend non-enumerating. 2. `activate` + `resend`. → verify: token activates; expired token rejected.
**6b:** 3. `configure` wiring to `import_admin_boundary` + `SiteConfig`/`features`. → verify: a GeoJSON upload seeds Administration under the tenant; second configure rejected. 4. `TenantApiKey` auto-issue + one-time reveal. → verify: key hashed at rest, maps to the tenant, revocable.

**Verify (goal-driven):** an E2E test: register → activate → configure with a fake boundary → the tenant has Administration rows + a `SiteConfig` + `features`; an issued `TenantApiKey` authenticates a push (MT-8) and resolves to this tenant.

## 4. User acceptance criteria

- As a **new country**, I sign up, verify my email, and configure my workspace (boundary, branding, modules) **myself**; my first drought maps appear after the next pipeline run — no ops ticket.

## 5. Technical acceptance criteria

- [ ] Two-phase register/activate with no email enumeration; subdomain reserved words blocked.
- [ ] `configure` seeds per-tenant Administration + SiteConfig + features; idempotent-once.
- [ ] An API key is auto-issued (hashed, revocable) and maps to the tenant.

## 6. Dependencies / hand-offs

- Needs MT-1/4/5 + DIH-4 import. Issues the key MT-8 consumes; the tenant it creates is auto-discovered by MT-11.

## 7. References

- [WS-3 README](README.md) §8 (D-MT-2/3), §9; MIS MT-001/006; [DIH-4](../2-v2-porting/DIH-4_country-pack.md).
