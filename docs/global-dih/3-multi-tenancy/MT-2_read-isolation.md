# Feature Design Document

## Feature: Read isolation — `for_user()` + `TENANT_PATH`

**Task ID**: MT-2
**Author**: Iwan Firmawan (with Claude)
**Date**: 2026-10-30
**Status**: Draft
**Effort**: ~8h (incl. agentic coding) — at the ceiling; if the query-site rewrite balloons, split by app (publication / users / jobs) into ≤8h phases.
**Depends on**: [MT-1](MT-1_tenant-model-scoping.md)

> Mirrors Akvo MIS **MT-003**. Explicit manager method, **not** middleware + thread-locals (rejected: global state, breaks in the DjangoQ worker, hides the filter).

---

## 1. Context

With tenant anchors in place (MT-1), every tenant-owned read must return only the current tenant's rows. The mechanism must be greppable and testable, and a forgotten site must fail loudly in tests, not leak silently.

## 2. Approach + files

- `TenantScopedQuerySet.for_user(user)` in `utils/`: `return self.filter(**{self.model.TENANT_PATH: user.tenant})`. Added to the default manager (and `SoftDeletes` manager where present).
- **`for_tenant(tenant)`** — the **public/unauthenticated** path: the hub's public frontend (`browse`, `compare`, `iframe`, published-map endpoints) has **no `request.user`**, so those reads scope by the **host tenant**: `return self.filter(**{self.model.TENANT_PATH: tenant})`, called with `request.tenant` ([MT-4](MT-4_subdomain-routing.md)). Same `TENANT_PATH`; `for_user` just resolves the tenant from the user instead of the host. **Every tenant-owned read uses one of the two — never a bare `.objects.filter`.**
- Rewrite every tenant-owned read `Model.objects.filter(...)` → `Model.objects.for_user(request.user).filter(...)` (authenticated) or `Model.objects.for_tenant(request.tenant).filter(...)` (public) across `v1_publication`, `v1_setup`, `v1_users`, `v1_jobs`.
- Every `is_superuser → return all rows` leak becomes "all rows of **my** tenant". In-tenant admin authority comes from the top **tenant role** (existing roles/abilities system, assigned at onboarding — [MT-6](MT-6_self-service-onboarding.md)), **not** Django `is_superuser` (which bypasses permission checks); the cross-tenant platform role is MT-10.
- Detail lookups route through the scoped queryset → a foreign object **404s** (not 403) for free.
- Coverage = a hand-maintained per-endpoint checklist, reviewer-signed; each endpoint gets a cross-tenant test.

## 3. Implementation steps

1. Add `TenantScopedQuerySet`/manager + wire into the tenant-owned models' managers. → verify: `Model.objects.for_user(u)` filters by `TENANT_PATH`.
2. Rewrite read sites app by app (publication → users → jobs → setup). → verify: per-endpoint test — tenant A's token never sees tenant B's rows; foreign detail = 404.
   - Include the **public** endpoints (browse/compare/iframe/published maps) via `for_tenant(request.tenant)`. → verify: an anonymous request on `A.host` returns only A's published maps; none of B's.
3. Redefine `is_superuser` reads as tenant-scoped. → verify: a superuser lists only their tenant.
4. Build the coverage checklist. → verify: every listed endpoint has a cross-tenant test.

**Verify (goal-driven):** a `CrossTenantTestCase` seeding two tenants; for each tenant-owned list/detail endpoint, assert A cannot read B (list excludes, detail 404). A grep check that no tenant-owned view calls bare `.objects.filter` on a scoped model.

## 4. User acceptance criteria

- As a **user**, I only ever see my own workspace's data; another workspace's records are invisible, not merely hidden.

## 5. Technical acceptance criteria

- [ ] Every tenant-owned read routes through `for_user` (authenticated) or `for_tenant` (public); foreign detail 404s; no bare `.objects.filter` on a scoped model.
- [ ] Public endpoints (browse/compare/iframe) scope by `request.tenant`; an anonymous visitor on one host never sees another tenant's published maps.
- [ ] Cross-tenant tests pass for every endpoint on the coverage checklist.
- [ ] `default`-tenant / legacy rows still resolve (NULL=NULL) so the legacy suite is green.

## 6. Dependencies / hand-offs

- Needs MT-1. Consumed by MT-3 (write guards reuse `for_user`) and MT-9 (jobs/datasets).

## 7. References

- [WS-3 README](README.md) §3; MIS MT-003.
