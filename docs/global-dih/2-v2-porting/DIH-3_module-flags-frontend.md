# Feature Design Document

## Feature: Module flags reach the frontend (`config.js` → `useModule()`)

**Task ID**: DIH-3
**Author**: Iwan Firmawan (with Claude)
**Date**: 2026-10-30
**Status**: Draft
**Effort**: ~5h (incl. agentic coding).
**Depends on**: [DIH-2](DIH-2_module-system.md)

> Eswatini-hub file:line refs; re-map to `drought-map-hub/app` when executing. (In the generic hub the equivalent channel is the `appConfig` cookie + `config.js`; see [DIH-9](DIH-9_setup-wizard-theme-and-modules.md).)

---

## 1. Context

The backend knows which modules are on (DIH-2); the frontend must too, so tabs, brief blocks and overview layers of a disabled module are **absent, not empty**.

## 2. Scope

Carry `modules` / `country` / `datasets` to the app and gate frontend surfaces by them. The per-surface work for specific modules (weather-off UX, folded into DIH-10 Phase C) and the full v2 look (DIH-10) build on this.

## 3. Approach + files

- `generate_config.py` already writes `source/config/config.min.js` (served at `/api/v1/config.js`, read by `DynamicScript.js`). Add three variables next to `topojson`/`zones`:

```js
var modules=["geonode","weather","iks","risk_level","indicators","datasets"];
var country={"name":"Eswatini","admin_label":{"one":"Inkhundla","many":"Tinkhundla"}};
var datasets=[{"key":"ndvi_anomaly","label":"NDVI anomaly","unit":"%","source":"…"}];
```

- `DynamicScript` dispatches `SET_MODULES` / `SET_COUNTRY` / `SET_DATASETS`; a small `useModule("weather")` hook reads the flags.
- Gate: Insights tabs, brief blocks, overview layers, and the `InsightsShell.js:90` `/iks/aggregations/soil-trend` header call (don't fetch when IKS is hidden).

> In the generic hub, `modules`/`country` also ride the `appConfig` cookie from `SiteConfig` (DIH-9). Keep one source of truth; prefer the cookie for SSR and `config.js`/context for client gating.

## 4. Decisions

- Follows MC-1 D-2/D-3: flags, not a plugin registry. `admin_label` delivered here is consumed by [DIH-6](DIH-6_admin-label.md).

## Implementation steps

1. Ensure `modules` (+ `country`, `datasets`) ride the `appConfig` cookie — `modules` is added by DIH-9's `SetupResponseSerializer`; confirm `country`/`datasets` are carried too. → verify: `getAppConfig().modules` is populated after setup.
2. `useModule(name)` hook reading `getAppConfig()` (via the app context). → verify: unit test returns true/false per the cookie's `modules`.
3. Gate Insights tabs, brief blocks, overview map layers, and menu items with `useModule(...)`. → verify: component test — with a module off, its tab/menu is **absent** (not an empty placeholder).

> The weather-off reviewer surface specifically is handled in [DIH-10](DIH-10_v2-ui-surface-port.md) Phase C; this task only delivers the flags + the gating hook.

## User acceptance criteria

- As a **visitor**, I never see a tab, menu item, or map layer for a module the operator disabled — the UI shows exactly the enabled modules.
- No "empty" or "coming soon" placeholder appears for a disabled module; it is simply not there.

## 5. Technical acceptance criteria

- [ ] `config.js` / `appConfig` carries `modules`, `country`, `datasets`.
- [ ] A disabled module's Insights tab / brief block / overview layer is not rendered, and its header fetches don't fire.
- [ ] Eswatini (all on) renders every surface as today.

**Verify by (goal-driven):** frontend tests — `InsightsShell` renders the IKS tab and fires `soil-trend` only when `useModule("iks")`; with modules empty, no optional tab mounts. Backend: `config.js` lists exactly the enabled modules (part of the DIH-2 `CoreOnlyTestCase`).

## 6. Dependencies / hand-offs

- Needs DIH-2 (backend flags) and DIH-9 (`SiteConfig.modules` source). Feeds DIH-6 (admin label) and DIH-10 (UI port).

## 7. References

- [MC-1](README.md) §4.1, §5; [DIH-9](DIH-9_setup-wizard-theme-and-modules.md) (modules source).
