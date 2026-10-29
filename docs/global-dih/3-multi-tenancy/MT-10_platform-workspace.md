# Feature Design Document

## Feature: Platform workspace + tenant inspection (optional, later)

**Task ID**: MT-10
**Author**: Iwan Firmawan (with Claude)
**Date**: 2026-10-30
**Status**: Draft — **optional / deferred** (not required for the multi-tenant MVP)
**Effort**: epic (~multi-day) → phase before building: 10a console backend, 10b console frontend, 10c inspection/switching. Detail each as its own ≤8h doc when scheduled.
**Depends on**: [MT-1](MT-1_tenant-model-scoping.md)..[MT-5](MT-5_email-per-tenant.md)

> Mirrors Akvo MIS **MT-021/022/023**. An operator console to list, suspend, rename, inspect tenants. Nice-to-have for support; the self-service MVP (MT-1..9, MT-11) works without it.

---

## 1. Context

Once many tenants exist, Akvo support needs a way to list/search tenants, suspend/delete, edit entitlements, and read a tenant's workspace (read-only) for support — without a per-tenant login. MIS built this as a separate platform console on a reserved `admin.<domain>` host.

## 2. Approach (summary; detail when scheduled)

- **Operator identity**: `SystemUser.is_platform_admin` (distinct from `is_superuser` = workspace owner); operator = `tenant=None, is_platform_admin=True`. `IsPlatformAdmin` permission. Bootstrapped by a `createplatformadmin` command.
- **Admin host**: reserved `admin.<BASE_DOMAIN>` (never resolves to a tenant). Console API queries `Tenant.objects` directly (a tenant-less operator's `for_user` → empty, so cross-tenant reads must be explicitly opted into).
- **Lifecycle**: Active / Deactivated (`is_active=False`) / Deleted (`deleted_at`), enforced in the one host resolver (MT-4) → a suspended tenant's host 404s, killing live sessions.
- **Entitlements**: `Tenant.features` (already MT-1) edited from the console.
- **Inspection/switching**: a read-only `TenantInspectionToken` lets an operator open a tenant's real app read-only; enforced read-only twice (middleware + auth class). One-time hand-off code, not a token in the URL.

## 3. Implementation steps (high level; phase before building)

- **10a** console backend (`IsPlatformAdmin`, admin host, tenant list/summary/detail, deactivate/activate/delete/rename, features). → verify: operator-only; a normal superadmin is 403.
- **10b** console frontend (tenants table, detail, rename-with-impact). → verify: host-decides-route to the admin app.
- **10c** inspection token + one-time code + read-only guards + switching. → verify: inspection is read-only (both guards), revocation immediate.

**Verify (goal-driven):** operator can list/suspend a tenant and a suspended tenant 404s next request; inspection opens a tenant read-only and cannot write (except the one switch endpoint).

## 4. User acceptance criteria

- As an **Akvo operator**, I can see every workspace, suspend/rename one, and look inside a workspace read-only to help — without logging in as that customer.

## 5. Technical acceptance criteria

- [ ] `is_platform_admin` separate from `is_superuser`; console behind `IsPlatformAdmin` + admin host.
- [ ] Suspension enforced in the host resolver (no per-view check).
- [ ] Inspection is read-only, enforced in both middleware and auth class.

## 6. Dependencies / hand-offs

- Needs MT-1..5. Independent of MT-11. Deferred until there are enough tenants to warrant a console.

## 7. References

- [WS-3 README](README.md) §4 (optional), §7; MIS MT-021/022/023.
