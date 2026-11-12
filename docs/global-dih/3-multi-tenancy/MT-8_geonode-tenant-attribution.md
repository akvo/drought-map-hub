# Feature Design Document

## Feature: GeoNode category prefix per tenant + `v1_geonode` push attribution

**Task ID**: MT-8
**Author**: Iwan Firmawan (with Claude)
**Date**: 2026-10-30
**Status**: Draft
**Effort**: ~5h (incl. agentic coding).
**Depends on**: [MT-1](MT-1_tenant-model-scoping.md); extends [DIH-1](../2-v2-porting/DIH-1_v1-geonode-optional-app.md)

> One shared GeoNode for all tenants (foundation §2). Coexistence by unique `geonode_id`; attribution by category prefix + the push identity.

---

## 1. Context

All tenants share one GeoNode. Rasters coexist because `geonode_id` is globally unique, but the hub must know **which tenant** each resource belongs to, both on fetch and on the pipeline push.

## 2. Approach + files

- **Attribution anchor**: DIH-1 **shipped** a core **`Raster`** asset (`geonode_id`, globally unique) + `Publication.raster` OneToOne — not the `PublicationGeonode` cache (superseded). `Publication` is already a tenant root (MT-1), so attribution rides **`Publication.tenant`**; MT-8 adds **`Raster.tenant`** so a pipeline-pushed raster (via `POST /api/v1/rasters`) is attributed before/without a publication. The optional `GeoNodeResource` pointer derives `raster__tenant` — same anchor.
- **Category prefix per tenant**: the pipeline uploads to `cdi-raster-map-<subdomain>` (etc.); the hub's `CDIGeonodeAPI` fetch/list filters by the tenant's category prefix **and** `for_user/for_tenant` on `Publication.tenant`. ⚠️ Verify GeoNode's "category" is free-form enough to prefix per tenant; if it is a fixed ISO vocabulary, use a per-tenant **keyword** or layer-name prefix instead.
- **Push attribution**: `v1_geonode` POST endpoints stamp the tenant on the created/updated `Publication` from the **push identity** —
  - **central pipeline** → an internal service identity + a `tenant` (subdomain) in the payload, validated against an existing `Tenant`;
  - **external pipeline** → the `TenantApiKey` (MT-6) resolves the tenant; the payload `tenant` must match or is ignored.
- `Publication.cdi_geonode_id` stays globally unique (correct for a shared GeoNode).
- Gated by the `geonode` module as today (DIH-1/DIH-2 → now `Tenant.features`).

## 3. Implementation steps

1. Add the tenant/category prefix to the GeoNode upload + the hub fetch filter. → verify: tenant A's fetch returns only `*-<A>` resources.
2. Stamp `Publication.tenant` on push from the resolved identity (service+payload tenant, or API key). → verify: a push with key/identity for A creates rows under A; a mismatched payload tenant is rejected/ignored.
3. Keep `cdi_geonode_id` global-unique; confirm no cross-tenant id collision assumptions. → verify: two tenants' resources with distinct ids coexist.

**Verify (goal-driven):** a push authenticated as tenant A lands under A's category + `Publication.tenant=A`; A's fetch excludes B's resources; an external key for A cannot stamp B.

## 4. User acceptance criteria

- As a **user**, my workspace only lists my own country's maps, even though all countries share one GeoNode behind the scenes.

## 5. Technical acceptance criteria

- [ ] Uploads carry a per-tenant category prefix; hub fetch filters by it + `Publication.tenant`.
- [ ] Push stamps `Publication.tenant` from the service identity or the API key; mismatch rejected.
- [ ] `cdi_geonode_id` stays globally unique.

## 6. Dependencies / hand-offs

- Needs MT-1; extends DIH-1. Consumes the key from MT-6; the central pusher is MT-11.

## 7. References

- [WS-3 README](README.md) §2, invariant 6; [DIH-1](../2-v2-porting/DIH-1_v1-geonode-optional-app.md).
