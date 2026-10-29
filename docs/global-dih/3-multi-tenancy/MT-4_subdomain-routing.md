# Feature Design Document

## Feature: Subdomain routing + host-bound enforcement + `tenant-info`

**Task ID**: MT-4
**Author**: Iwan Firmawan (with Claude)
**Date**: 2026-10-30
**Status**: Draft
**Effort**: ~7h (incl. agentic coding).
**Depends on**: [MT-1](MT-1_tenant-model-scoping.md)

> Mirrors Akvo MIS **MT-008**. Host identifies the tenant; defense-in-depth on top of `for_user` (MT-2).

---

## 1. Context

The web app must know which tenant a request belongs to. MIS binds it to the **subdomain**; the hub follows the same model so one deployment serves `kenya.hub.domain`, `fiji.hub.domain`, etc. Config/branding must then be served per host, replacing the single baked `appConfig`.

## 2. Approach + files

- `BASE_DOMAIN` setting. `resolve_tenant_from_host(host) -> Tenant | None` in `utils/tenant_host.py`: strip port/lowercase; `<label>.BASE_DOMAIN` → `Tenant.objects.filter(subdomain=label, is_active=True, deleted_at__isnull=True).first()`; unknown → None. (The `is_active/deleted_at` filter is the single place suspension is enforced — a suspended tenant's host 404s everywhere, killing live sessions on the next request.)
- **Base domain (no subdomain)** is **configurable** (D-MT-6): a `BASE_DOMAIN_TENANT` setting maps it either to the **`default` tenant** (the **standalone** case — so a single-tenant install post-backfill keeps working, its user's `tenant_id` matching the host) or to **`None`** (a multi-tenant SaaS landing/registration page). This resolves the standalone-vs-`None` contradiction; subdomains always resolve to their own tenant regardless.
- `TenantMiddleware`: set `request.tenant`; unknown host → 404 pre-view; for an authenticated request, if `request.user.tenant_id != request.tenant.id` → 403 (browser: redirect to the user's own subdomain). Because DRF authenticates at the view layer, the middleware runs `JWTAuthentication().authenticate(request)` itself. Exempt list: `register*`, `health`, `tenant-info`, `config.js`.
- `GET /api/v1/tenant-info` (public, host-keyed): `{subdomain, name, language, logo, features}` for `request.tenant`; on the base domain it returns the `default` tenant's info (standalone) or 204 (SaaS, `BASE_DOMAIN_TENANT=None`). Drives the tenant-branded login + bootstraps the frontend (replaces the single baked `appConfig`; see MT-7).
- Login is subdomain-scoped (MT-5 pairs with this).
- **Local dev**: `/etc/hosts` + `BASE_DOMAIN=localapp.test`, Django `ALLOWED_HOSTS=.localapp.test`; the Next proxy forwards the Host header. Test override `X-Tenant-Subdomain` honored only under `DEBUG`/`ALLOW_TENANT_HEADER`.

## 3. Implementation steps

1. `BASE_DOMAIN` + `BASE_DOMAIN_TENANT` + `resolve_tenant_from_host` (with the active/undeleted filter). → verify: unit test — `kenya.`→tenant, unknown→None, suspended→None; base→`default` when `BASE_DOMAIN_TENANT=default`, base→None when unset.
2. `TenantMiddleware` sets `request.tenant`, 404s unknown hosts, 403/redirects host-mismatch. → verify: request on `kenya.` with a `fiji` token → 403.
3. `GET /tenant-info` public endpoint. → verify: returns the host's tenant branding; 204 on base domain.
4. Local-dev wiring (hosts, ALLOWED_HOSTS, proxy, test header). → verify: two subdomains reachable locally; test client uses `X-Tenant-Subdomain`.

**Verify (goal-driven):** middleware tests for resolve/404/403; a suspended tenant's host 404s on the next request without a per-view check; `tenant-info` returns per-host branding.

## 4. User acceptance criteria

- As a **user**, I reach my workspace at my own subdomain, see its name/logo on the login page, and cannot use my session on another workspace's URL.

## 5. Technical acceptance criteria

- [ ] `request.tenant` resolved from the host; unknown → 404; host/user mismatch → 403 (API) / redirect (browser).
- [ ] Suspension/deletion enforced solely in `resolve_tenant_from_host`.
- [ ] `tenant-info` serves per-host branding/config; base domain → `default` tenant (standalone) or 204 (SaaS), per `BASE_DOMAIN_TENANT`.
- [ ] Local dev works with subdomains; tests use the header override.

## 6. Dependencies / hand-offs

- Needs MT-1. Pairs with MT-5 (login scoping) and feeds MT-7 (config via `tenant-info`).

## 7. References

- [WS-3 README](README.md) §3, invariant 3/6; MIS MT-008.
