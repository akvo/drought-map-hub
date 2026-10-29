# Feature Design Document

## Feature: Module system — `DIH_MODULES` + `module_enabled()` gating

**Task ID**: DIH-2
**Author**: Iwan Firmawan (with Claude)
**Date**: 2026-10-30
**Status**: Draft
**Effort**: ~4h (incl. agentic coding) — the mechanism only; guarding each optional app's call sites is part of that app's own port, not this task.
**Depends on**: — (foundation; first consumer is DIH-1's `geonode` gate)

> Paths in the porting-contract table below are **Eswatini-hub** file:line refs — they locate the coupling to guard *when that app is ported*; they do **not** exist in `drought-map-hub/app` today.

---

> **Multi-tenancy (WS-3):** the per-instance env `DIH_MODULES` becomes **per-tenant** `Tenant.features` (JSONField, MT-1). `module_enabled(name)` reads `request.tenant.features` instead of the env var; the frontend `useModule()` reads `tenant-info.features` ([MT-7](../3-multi-tenancy/MT-7_per-tenant-branding-config.md)). The mechanism (gating pattern, dependency check, CoreOnly harness) is unchanged — only the **source** of the flags moves from env to the tenant row. Standalone deploy = the `default` tenant.

## 1. Context

The generic hub today has only the **6 core apps** — `v1_init`, `v1_jobs`, `v1_publication`, `v1_rundeck`, `v1_setup`, `v1_users` — and **no feature flags**. The optional apps (`v1_weather`, `v1_iks`, `v1_risk_level`, `v1_indicators`, `v1_insights`, `v1_activity`) are **not ported yet**: the generic code has zero references to them, `v1_publication` has none of the `review/brief/validation/insights` subdirs, and `app/backend/job.sh` is just `check_overdue_reviews`. The root `drought_map_hub/urls.py` statically includes the 6 core apps.

So DIH-2 builds the **switch mechanism** now (future-proofing, B-5) — there is almost nothing to gate yet. The core↔optional couplings it will need to guard live in **Eswatini-v2** and land one at a time as each optional app is ported (DIH-10 and the backend ports). The first real consumer of the mechanism is the `geonode` gate from [DIH-1](DIH-1_v1-geonode-optional-app.md).

**Porting contract** (Eswatini-v2 refs — each optional app's port must guard these when it lands; DIH-2 does **not** touch them now, because they are not in the generic repo):

| Optional app | Core call site (Eswatini-v2) | What its port must gate |
|---|---|---|
| `v1_weather` | `v1_publication/review/utils.py:18-25`, `:313`, `:356`; `validation/utils.py:25`; `v1_users/views.py:42`, `admin.py:10` | reviewer-map `confidence`, band filter, high-confidence tally → bulk-accept; validation rows; observer magic link |
| `v1_iks` | `v1_publication/brief/situation.py:12-14`; `v1_insights/services.py:16-26` | brief IKS block; insights |
| `v1_risk_level` | `v1_publication/brief/situation.py:12-14`; `v1_risk_level/service.py:3-7` | brief risk block; (requires `indicators`) |
| `v1_indicators` | `v1_insights/map_layers.py:29`; `v1_activity/trigger_evaluation.py:24-30` | overview map layers; SOP trigger evaluation |
| `v1_insights` | `v1_insights/services.py:16-26` | national overview / insights |
| `v1_weather` jobs | Eswatini `backend/job.sh:30-77` (weather/CHIRPS/AgERA5/CS) | fetchers run unconditionally |

Also, when `v1_weather` is ported, fix its stale comment `v1_weather/services.py:41-43` ("v1_publication never imports v1_weather" — false, see `review/utils.py:18`).

## 2. Scope

**The gating mechanism only**, shipped against today's generic repo:
- `DIH_MODULES` env + `module_enabled()` helper,
- the conditional URL-include pattern (first used by `geonode`, DIH-1),
- the cross-module dependency check,
- the `CoreOnlyTestCase` harness.

**Not in scope:** guarding the call sites in the porting-contract table (each app's port does that, using this helper), the per-surface UX of a disabled module (weather-off = DIH-10 Phase C / frontend flags = DIH-3), and the module list/matrix (MC-1 §6).

## 3. Approach + files

**Ships in DIH-2 (generic repo today):**
- `DIH_MODULES` comma-separated env var, read in `settings.py` with the repo's `environ.get` style; unset = all on. One `module_enabled(name)` helper in `app/backend/utils/modules.py`.
- Conditional include in `drought_map_hub/urls.py`: an optional app's urls are included only when `module_enabled(...)` → a disabled module 404s (no attack surface). The pattern ships now; its first live use is `geonode` (DIH-1).
- Cross-module dependency check at startup: `risk_level` on + `indicators` off → `ImproperlyConfigured`. The rule ships now (inert until those apps exist).
- A `CoreOnlyTestCase` base (`override_settings(DIH_MODULES=[])`) as the shared gate harness; its assertions grow as each surface is ported.

**Contract each optional-app port follows (not DIH-2):**
- Register the app's flag, gate its urls via the include pattern, and guard its core call sites (porting-contract table) behind `if module_enabled(...)` with a **local import** (D-3) — no registry.
- Add the app's `job.sh` fetchers behind the flag; fix the `v1_weather` stale comment on that port.

## 4. Decisions (MC-1 Decision Log)

- **D-2**: a disabled module stays in `INSTALLED_APPS`, just not wired (every optional app has an FK to `Administration`; uninstalling breaks migrations).
- **D-3**: core call sites guard with a local import, they do not plug into a registry (one implementation per slot — a registry would be abstraction for its own sake).
- **Mechanism-now, guards-with-port** (this task): because the generic repo has no optional apps yet, DIH-2 ships only the switch; each port wires itself through it.

## Implementation steps

1. Read `DIH_MODULES` in `settings.py` (`environ.get`, comma-separated, unset = all on). → verify: parses a list; unset → everything enabled.
2. `module_enabled(name)` in `app/backend/utils/modules.py`. → verify: unit test across unset / listed / omitted.
3. Conditional-include helper in `drought_map_hub/urls.py` (an optional app's urls are wired only when enabled). → verify: the first live consumer (`geonode`, DIH-1) 404s when off, routes when on.
4. Startup dependency check: `risk_level` on + `indicators` off → `ImproperlyConfigured`. → verify: a settings test raises it.
5. `CoreOnlyTestCase` base (`override_settings(DIH_MODULES=[])`). → verify: full suite green; the base is importable by other apps' tests.

**Verify (goal-driven):** unit-test `module_enabled()`; a `CoreOnlyTestCase` asserting `geonode` routes 404 with the core suite green; a settings test for the `risk_level`-without-`indicators` guard.

## User acceptance criteria

- As an **operator** onboarding a country, I enable only the modules it needs via `DIH_MODULES`; a disabled feature is simply absent (its routes 404, its jobs don't run), never a broken or empty screen.
- Leaving `DIH_MODULES` unset keeps an existing deployment (Eswatini) behaving exactly as before.

## 5. Technical acceptance criteria

**Now (DIH-2):**
- [ ] `DIH_MODULES` defaults to all-on (no change to any existing `.env`).
- [ ] `module_enabled("x")` → true when the var is unset or lists `x`; false when the var is set and omits `x`.
- [ ] Conditional URL include works end-to-end on the first consumer: `geonode` off → `/api/v1/geonode/*` 404; on → routed (shared with DIH-1).
- [ ] `risk_level` on + `indicators` off → `ImproperlyConfigured` at startup (rule present before those apps land).
- [ ] `CoreOnlyTestCase` harness exists; the full suite passes (nothing to gate yet beyond `geonode`).

**Per-port (owned + verified by each app's porting task, listed here as the contract):**
- [ ] As a surface lands, its CoreOnly assertion is added: reviewer map `confidence: null` + `confidence_enabled: false` (weather), brief builds without IKS/risk blocks (iks/risk), national overview loads, weather/IKS/risk URLs 404, `config.js` lists no modules (DIH-3).

**Verify by (goal-driven):** unit-test `module_enabled()` across unset/listed/omitted; a `CoreOnlyTestCase` with `override_settings(DIH_MODULES=[])` asserting `geonode` routes 404 and the core suite is green; a settings test that `risk_level`-without-`indicators` raises `ImproperlyConfigured`.

## 6. Dependencies / hand-offs

- First consumer: [DIH-1](DIH-1_v1-geonode-optional-app.md) (`geonode` gate). Subsequently every optional-app port uses the helper + include pattern and adds its own guards + CoreOnly assertions.
- Feeds [DIH-3](DIH-3_module-flags-frontend.md) (config flags) and DIH-9's wizard precedence (`effective = DIH_MODULES_allows ∧ wizard`).

## 7. References

- [MC-1](README.md) §1 (coupling), §5 D-2/D-3, §6 (matrix), §9 (CoreOnly + leak check).
- Generic repo today: `app/backend/drought_map_hub/urls.py` (static core includes), `app/backend/utils/` (helper home), `app/backend/job.sh` (`check_overdue_reviews` only).
