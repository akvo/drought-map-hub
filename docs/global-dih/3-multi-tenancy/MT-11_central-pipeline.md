# Feature Design Document

## Feature: Central multi-tenant CDI pipeline

**Task ID**: MT-11
**Author**: Iwan Firmawan (with Claude)
**Date**: 2026-10-30
**Status**: Draft
**Effort**: ~18h total (incl. agentic coding) → 3 phases ≤8h each: 11a hub tenant-config API ~5h, 11b `job.sh` tenant loop + isolation ~8h, 11c scheduling + per-tenant monitoring ~5h.
**Depends on**: [MT-1](MT-1_tenant-model-scoping.md), [MT-8](MT-8_geonode-tenant-attribution.md); reworks WS-1 [CDP-0](../1-cdi-data-pipeline/CDP-0_port-eswatini-pipeline.md)/[CDP-6](../1-cdi-data-pipeline/CDP-6_pipeline-integration.md)

> The one WS-1-side task of multi-tenancy. One Akvo pipeline serves all tenants (foundation §2, D-MT-4); an external per-tenant pipeline stays a fallback.

---

## 1. Context

The CDI pipeline today runs one country per box from filesystem config. To make onboarding fully self-service, a **central** pipeline discovers active tenants from the hub and runs CDI for each — so a newly onboarded tenant (MT-6) is picked up on the next run with no ops step.

## 2. Approach + files

- **11a — hub tenant-config API**: `GET /api/v1/pipeline/tenants` (service-auth) returns active, configured tenants + each one's `{subdomain, bounds, weights, region_name, percentile_source}` (from `SiteConfig` + per-tenant config). This replaces the single bind-mounted `cdi_project_settings.conf`.
- **11b — `job.sh` tenant loop**: fetch the tenant list, then for each tenant run the existing fetch→regrid→derive→percentile→upload steps against **its** bounds/weights, writing to `/app/data/<subdomain>/…` (one volume, per-tenant sub-dirs — foundation §10). **Per-tenant failure isolation**: a tenant's failure is logged + skipped, not `exit 1`. **Bounded parallelism lives in `job.sh` itself** — shell-level (`xargs -P K` over the tenant list, or background jobs + `wait`), capped at **K = the CDS per-account pool limit (≤8, §7.1)**, not a naive serial loop (D-MT-5). **Not** DjangoQ (the app-side `qcluster` worker runs on a different node) and **not** Celery (absent). Shared Akvo NASA/CDS creds.
- Push results to the hub via `v1_geonode` (MT-8) with the internal **service identity** + the tenant; upload to GeoNode under the tenant's category prefix.
- **11c — scheduling + monitoring**: Rundeck **triggers** the monthly run (as today — the per-tenant loop stays inside `job.sh`, D-MT-5); per-tenant run status + alerting + retry, plus a central-account health alert (the central pipeline + shared CDS account are a single point of failure — foundation §7, §7.2).
- **Storage/compose**: one `cdi_data:/app/data` volume (prod) / `./data:/app/data` (dev); config from the hub API, not a file bind (foundation §10 sketch).
- External pipelines stay supported: a tenant may run its own and push with its `TenantApiKey` (MT-8).

## 3. Implementation steps

**11a:** 1. `GET /pipeline/tenants` (service-auth) → active+configured tenants + config. → verify: returns only active/configured tenants; a suspended tenant drops out.
**11b:** 2. `job.sh` loops the tenant list, per-tenant data dir, continue-on-error, per-tenant report. → verify: with 2 fake tenants, one failing, the other still completes + reports. 3. Bounded parallelism. → verify: concurrency capped; total run within the window on a test set. 4. Push with service identity + tenant (MT-8). → verify: each tenant's output lands under its category + `Publication.tenant`.
**11c:** 5. Rundeck schedule + per-tenant status/alerts/retry. → verify: a failed tenant alerts + retries without blocking others.

**Verify (goal-driven):** an integration run over 2 fake tenants (one deliberately failing) → the healthy tenant's maps reach the hub under its category; the failing one is reported + retried, not fatal; a newly added tenant appears in the next run with no config file.

## 4. User acceptance criteria

- As a **newly onboarded country**, my drought maps start appearing automatically after the next scheduled run — I never stand up or configure a pipeline.
- As **Akvo ops**, one pipeline serves every country, with per-tenant run status so one country's failure doesn't hide or block the others.

## 5. Technical acceptance criteria

- [ ] `job.sh` runs per tenant from the hub tenant-config API (no per-country config file); writes to `/app/data/<subdomain>/`.
- [ ] Per-tenant failure isolation (continue-on-error + report); bounded parallelism in `job.sh` (`xargs -P K`, K = CDS pool cap ≤8), triggered by Rundeck (D-MT-5).
- [ ] Pushes carry tenant attribution (MT-8); shared central creds.
- [ ] A new tenant is auto-discovered on the next run; external pipelines still supported via API key.

## 6. Dependencies / hand-offs

- Needs MT-1 (tenant model) + MT-8 (push attribution) + MT-6 (tenants to discover). Reworks CDP-0/CDP-6 (central-pipeline model).

## 7. Feasibility assessment

Grounds the §7/§10 foundation bullets in numbers and a verdict. Anchors: a one-country monthly run finishes in **< 30 min compute, excluding CDS queue** ([CDP-6](../1-cdi-data-pipeline/CDP-6_pipeline-integration.md) UAC); monthly runs are **incremental** (one new month per source) and baseline rebuilds are **yearly + manual-approval gated** ([CDP-6](../1-cdi-data-pipeline/CDP-6_pipeline-integration.md) D-3); a bbox subset is tiny (FLDAS ~45 KB/month, CHIRPS ~44×44 cells — HANDOFF §4).

### 7.1 Compute & CDS load

| Mode | Per run | At N tenants | Verdict |
|---|---|---|---|
| **Monthly steady-state** | 1 new month × 4 sources; < 30 min compute | compute is embarrassingly parallel on one node (bounded pool); CDS = N small single-month requests | **Cheap.** Even N≈50 clears inside the monthly window (days), not minutes |
| **Yearly baseline rebuild** | 40-yr (SPI/ESI/SM) + 14-yr (EVI2) fetch per tenant | the real load spike: N × heavy CDS fetches, each queueable for hours | **Manageable** — it is yearly *and* manual-approval gated, so **stagger it** across days/tenants; never rebuild all N at once |

**Binding ceiling = CDS per-account concurrency.** The CDS caps simultaneous requests per account at **~10–12** (requests above the cap queue, they don't fail; the limit flexes with system load — [ECMWF](https://confluence.ecmwf.int/x/nuRtDg), [CDS live limits](https://cds.climate.copernicus.eu/live/limits)). One central account funnels **every** tenant through that one quota. Mitigation: cap the `cdsapi` worker pool at **≤ 8** (safely under the limit); stagger baseline rebuilds. If N ever outgrows what one account clears in the window, **shard across 2–3 CDS accounts** (additive, cheap) — but that is beyond any committed scale (B-5: no second country committed yet).

### 7.2 Single point of failure

| Failure | Blast radius | Mitigation / budget |
|---|---|---|
| One tenant's config or fetch fails | that tenant only | already isolated — continue-on-error + per-tenant report (11b); **not systemic** |
| Pipeline node down for a run | all tenants miss that run | **tolerable**: cadence is monthly, runs are idempotent-incremental → just re-run; delay of hours/days, **no data loss**. Not a low-latency service |
| **Central CDS/Earthdata account suspended or throttled** | **all tenants stall** | the sharpest systemic SPOF → monitor account health + CDS queue depth as a first-class alert; the **external-pipeline fallback** (D-MT-3) is the pressure valve for a tenant that cannot wait |

**Failure budget:** a monthly map carries no SLA — onboarding copy already sets *"maps appear after the next run"*. The SPOF is acceptable **by design** because what it threatens is a monthly, idempotent, re-runnable batch.

### 7.3 Production deployment & sizing

Topology/DNS/TLS/storage are in [README §10](README.md#10-production-deployment-assessment). Adds here:
- **Node sizing**: one CDI node sized for ~1 tenant's working set × pool concurrency (≤8). No horizontal fleet needed at the realistic horizon.
- **Disk**: ~GB/tenant including 40-yr baselines + GeoTIFFs (bbox subsets are small); dozens of tenants ≈ tens of GB — **linear and modest**, not a near-term constraint.
- **Monitoring**: per-tenant run status **and** central-account health (quota/suspension) are both mandatory alerts.

### 7.4 Verdict

**Viable at the realistic horizon (1 → low-double-digit tenants).** Monthly steady-state is cheap; the only real load is the yearly, gated, stagger-able baseline rebuild; the SPOF is acceptable because the workload is a monthly re-runnable batch with the external pipeline as a fallback. Rework is forced only at a scale not on the roadmap (many dozens of tenants, or a sub-monthly cadence). **Recommended guardrails:** CDS pool ≤ 8, stagger baseline rebuilds, alert on the central account, keep the external-pipeline fallback.

## 8. References

- [WS-3 README](README.md) §2 (D-MT-4), §7, §10; [CDP-0](../1-cdi-data-pipeline/CDP-0_port-eswatini-pipeline.md), [CDP-6](../1-cdi-data-pipeline/CDP-6_pipeline-integration.md).
- CDS concurrency limits: [ECMWF request-limit docs](https://confluence.ecmwf.int/x/nuRtDg), [CDS live limits page](https://cds.climate.copernicus.eu/live/limits).
