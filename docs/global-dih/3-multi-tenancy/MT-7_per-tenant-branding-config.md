# Feature Design Document

## Feature: Per-tenant branding + config via host-keyed `tenant-info`

**Task ID**: MT-7
**Author**: Iwan Firmawan (with Claude)
**Date**: 2026-10-30
**Status**: Draft
**Effort**: ~5h (incl. agentic coding).
**Depends on**: [MT-4](MT-4_subdomain-routing.md); supersedes the per-deploy config half of [DIH-9](../2-v2-porting/DIH-9_setup-wizard-theme-and-modules.md)/[DIH-10](../2-v2-porting/DIH-10_v2-ui-surface-port.md)

> Mirrors Akvo MIS **MT-025/026**. Config/branding lives on the tenant row, served per host — never baked into the frontend.

---

## 1. Context

The single-tenant plan delivers config through one baked `appConfig` cookie from the single `SiteConfig`. Multi-tenant must serve **each host its own** colour, logo, admin label, language and modules. This replaces the baked-config channel with the host-keyed `tenant-info` endpoint (MT-4).

## 2. Approach + files

- Per-tenant branding on `Tenant` (`logo`, `language`) + `SiteConfig` (name, country, map_center, admin_label, region colours) — all per tenant after MT-1.
- `GET /api/v1/tenant-info` (MT-4) returns the resolved branding/config for `request.tenant`; the frontend bootstraps from it per request (SSR), replacing `getAppConfig()`'s single baked cookie. `features` from `Tenant.features` drives `useModule()` (ties to DIH-3's frontend gating). **`Tenant.features` is the single module store under WS-3** — DIH-9's wizard writes module flags here, not to a separate `SiteConfig.modules` (which it would otherwise add); the two must not both exist.
- Brand colour flows exactly as DIH-8 (token → `--primary-color` → AntD/Tailwind) but the **source** is `tenant-info.primary_color`, not a per-deploy cookie. Logo = the host tenant's logo (replaces static assets where the logo already appears).
- `document.title` / head = tenant name per host.

## 3. Implementation steps

1. Ensure `tenant-info` carries `{primary_color, logo, admin_label, language, features, name, map_center}`. → verify: endpoint returns per-host values.
2. Repoint the frontend bootstrap from the single baked `appConfig` to `tenant-info` (host-keyed). → verify: two subdomains render different colour/logo/title with no redeploy.
3. Drive `useModule()` from `tenant-info.features`. → verify: a module off for tenant A is absent for A, present for B.
4. Brand colour sink (DIH-8 mechanism) reads `tenant-info.primary_color`. → verify: AntD primary + `--primary-color` follow the host tenant.

**Verify (goal-driven):** two seeded tenants with different colour/logo/label/features; assert each host renders its own branding and module set; no value is baked at build time.

## 4. User acceptance criteria

- As a **visitor**, each workspace shows its own name, logo, colour, admin-unit word and enabled features — switching subdomains switches the whole look, with nothing hard-coded.

## 5. Technical acceptance criteria

- [ ] All per-tenant branding/config served by host-keyed `tenant-info`; nothing baked into the frontend build.
- [ ] `useModule()` reads `tenant-info.features`.
- [ ] Brand colour/logo/title/admin-label resolve per host.

## 6. Dependencies / hand-offs

- Needs MT-4. Reuses DIH-8 colour sink + DIH-3 gating; supersedes their per-deploy config source.

## 7. References

- [WS-3 README](README.md) §3, invariant 5; MIS MT-025/026; [DIH-8](../2-v2-porting/DIH-8_theming-per-client-brand.md), [DIH-10](../2-v2-porting/DIH-10_v2-ui-surface-port.md).
