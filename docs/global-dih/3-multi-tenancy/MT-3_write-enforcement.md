# Feature Design Document

## Feature: Write-path enforcement — stamp + guard + FK validation

**Task ID**: MT-3
**Author**: Iwan Firmawan (with Claude)
**Date**: 2026-10-30
**Status**: Draft
**Effort**: ~6h (incl. agentic coding).
**Depends on**: [MT-1](MT-1_tenant-model-scoping.md), [MT-2](MT-2_read-isolation.md)

> Mirrors Akvo MIS **MT-004**. Three threats, three mechanisms.

---

## 1. Context

Reads are scoped (MT-2); writes must not create, modify, or reference across tenants. A client must never be able to set `tenant` or point a foreign-key at another tenant's row.

## 2. Approach + files

- **(a) Stamp creates**: `TenantStampedSerializerMixin.create()` injects `tenant = self.context["user"].tenant` into `validated_data`; a client-supplied `tenant` key is ignored. Only the direct-FK roots are stamped; derived rows inherit via their parent.
- **(b) Guard update/delete**: detail write views fetch via `get_object_or_404(Model.objects.for_user(request.user), pk=...)` → a foreign target 404s.
- **(c) Validate payload FKs**: `TenantScopedPrimaryKeyRelatedField` (extends the repo's custom PK field) sets `get_queryset()` → `base.for_user(context["user"])`; a foreign pk fails with `does_not_exist` → **400**.
- Error split (from MIS): foreign object by URL id → **404** (hide existence); foreign FK in payload → **400** (invalid value).
- Async writes (DjangoQ worker): the task loads the user and stamps `user.tenant` — no signature change.

## 3. Implementation steps

1. Add the stamping mixin; apply to create serializers of the 5 roots. → verify: a create with a spoofed `tenant` in the body is stamped to the caller's tenant, not the spoof.
2. Route update/delete detail views through `for_user` lookups. → verify: PATCH/DELETE on a foreign pk → 404.
3. Add `TenantScopedPrimaryKeyRelatedField`; apply to payload FKs. → verify: a payload referencing a foreign row → 400 `does_not_exist`.
4. Stamp async worker writes from `user.tenant`. → verify: a worker-created row carries the right tenant.

**Verify (goal-driven):** per write endpoint — spoofed-tenant create is corrected; foreign update/delete 404; foreign payload FK 400. A worker-task test asserts the stamped tenant.

## 4. User acceptance criteria

- As a **user**, anything I create or edit stays inside my workspace, and I cannot attach it to another workspace's records — even by crafting the request.

## 5. Technical acceptance criteria

- [ ] Creates are stamped from the authenticated user; client `tenant` ignored.
- [ ] Foreign update/delete → 404; foreign payload FK → 400.
- [ ] Async writes carry the correct tenant.

## 6. Dependencies / hand-offs

- Needs MT-1 + MT-2 (`for_user`). Pattern reused by MT-9.

## 7. References

- [WS-3 README](README.md) §3, invariant 2/4; MIS MT-004.
