# Feature Design Document

## Feature: Jobs / export / datasets tenant scoping

**Task ID**: MT-9
**Author**: Iwan Firmawan (with Claude)
**Date**: 2026-10-30
**Status**: Draft
**Effort**: ~5h (incl. agentic coding).
**Depends on**: [MT-2](MT-2_read-isolation.md), [MT-3](MT-3_write-enforcement.md)

> Mirrors Akvo MIS **MT-009**. The async export/download paths that read/write files, easy to miss in MT-2/MT-3.

---

## 1. Context

`v1_jobs` (map downloads) and the `v1_datasets` tab (DIH-7) run outside the ordinary request path — background tasks and file downloads. They must not leak across tenants.

## 2. Approach + files

- `Jobs` `TENANT_PATH = tenant` (**direct FK**, MT-1 — the repo's `Jobs` has **no `user` FK** to derive from). `download_file`/`download_status` scope by `get_object_or_404(Jobs.objects.for_user(request.user), ...)` → tenant ownership (add a `created_by` FK later only if per-user, not per-tenant, ownership becomes a requirement).
- Export-request serializers make any `administration_id`/`publication_id`/selection FKs tenant-scoped (`TenantScopedPrimaryKeyRelatedField`) → 400 before a `Jobs` row is created.
- Belt-and-suspenders: the worker task builds its base queryset scoped to `job.tenant` so even a slipped id cannot leak.
- `v1_datasets` (DIH-7): `AdminDatasetValue` derives via `administration__tenant`; the read-only API + import command scope by tenant; files written under `STORAGE_PATH/tenants/<subdomain>/`.

## 3. Implementation steps

1. Scope `v1_jobs` download endpoints + export serializers by tenant/user. → verify: tenant A cannot download B's export; a foreign selection id → 400.
2. Scope the worker export task's base queryset to `job.tenant`. → verify: a slipped id yields no foreign rows in the output.
3. Scope `v1_datasets` API + import to the tenant; per-tenant file paths. → verify: A's dataset tab shows only A's data.

**Verify (goal-driven):** cross-tenant tests on every `v1_jobs` download/export endpoint and the datasets API; a worker-task test asserting the output contains only the job tenant's rows.

## 4. User acceptance criteria

- As a **user**, my exports and downloads contain only my workspace's data, and I can't fetch another workspace's generated file.

## 5. Technical acceptance criteria

- [ ] `Jobs` + datasets reads/writes route through `for_user`/tenant ownership (`Jobs.tenant`, direct FK).
- [ ] Export selection FKs validated per tenant (400 on foreign).
- [ ] Worker export base queryset is tenant-scoped.

## 6. Dependencies / hand-offs

- Needs MT-2/MT-3. Covers the async gap after the sync endpoints are scoped.

## 7. References

- [WS-3 README](README.md) §3; MIS MT-009; [DIH-7](../2-v2-porting/DIH-7_client-data.md).
