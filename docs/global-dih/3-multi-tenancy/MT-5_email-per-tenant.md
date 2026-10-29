# Feature Design Document

## Feature: Email unique per tenant + tenant-aware auth

**Task ID**: MT-5
**Author**: Iwan Firmawan (with Claude)
**Date**: 2026-10-30
**Status**: Draft
**Effort**: ~5h (incl. agentic coding).
**Depends on**: [MT-1](MT-1_tenant-model-scoping.md), [MT-4](MT-4_subdomain-routing.md)

> Mirrors Akvo MIS **MT-013**. The same person can belong to several workspaces as separate accounts.

---

## 1. Context

`SystemUser.email` is globally `unique=True` today. For multi-tenant, one email must be usable in more than one workspace (separate accounts, separate passwords/roles). Login must resolve within the request's tenant.

## 2. Approach + files

- `SystemUser.email` drops `unique=True`; add `UniqueConstraint(fields=["email", "tenant"], name="unique_email_per_tenant")` (migration = `AlterField` + `AddConstraint`). Postgres `NULL != NULL` leaves tenant-less rows unconstrained.
- `utils/tenant_auth_backend.py::TenantAwareBackend(ModelBackend)`: `authenticate(request, email, password, tenant=None)` → if `tenant is None` return None (falls through to `ModelBackend` for shell/mgmt); else `SystemUser.objects.get(email=…, tenant=tenant, deleted_at=None)`, with a dummy `set_password` on miss for timing parity. `AUTHENTICATION_BACKENDS = [TenantAwareBackend, ModelBackend]`.
- `login` passes `tenant=getattr(request, "tenant", None)` to `authenticate()` and scopes the unverified lookup; `resend_activation` and forgot-password likewise tenant-scoped (via serializer context).
- All existing FKs point at `SystemUser.id` (unchanged); JWT encodes pk only — the MT-4 middleware `tenant_id` check blocks replay across tenants.
- Fix any latent `SystemUser.objects.get(email=request.user)` that would raise `MultipleObjectsReturned` once email isn't unique → use `request.user` / `pk=request.user.pk`.

## 3. Implementation steps

1. Migration: drop global unique, add `unique_email_per_tenant`. → verify: same email in two tenants OK; duplicate within a tenant rejected; `migrate` back restores global unique on a de-duped set.
2. `TenantAwareBackend` + `AUTHENTICATION_BACKENDS`. → verify: login on `kenya.` authenticates only the Kenya account of that email.
3. Scope `login`/`resend_activation`/forgot-password to `request.tenant`. → verify: cross-tenant login attempt fails.
4. Fix `get(email=...)` hot-spots. → verify: those paths work with a duplicated email across tenants.

**Verify (goal-driven):** a test creating the same email in two tenants; assert independent login/password per subdomain; assert no `MultipleObjectsReturned` on profile/delete/activity paths.

## 4. User acceptance criteria

- As a **user with one email**, I can hold separate accounts in different workspaces, each with its own password and role; signing into one never touches the other.

## 5. Technical acceptance criteria

- [ ] `UniqueConstraint(email, tenant)` replaces global unique; reversible.
- [ ] Login resolves within `request.tenant`; cross-tenant attempt fails.
- [ ] No `MultipleObjectsReturned` regressions once email is non-unique.

## 6. Dependencies / hand-offs

- Needs MT-1 + MT-4 (`request.tenant`). Feeds MT-6 (registration sets `(email, tenant)`).

## 7. References

- [WS-3 README](README.md) §3, invariant 4; MIS MT-013.
