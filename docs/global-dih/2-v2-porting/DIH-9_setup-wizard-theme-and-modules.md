# Feature Design Document

## Feature: Setup wizard — brand-colour picker + module toggles (GeoNode / weather / IKS)

**Task ID**: DIH-9 (sub-task of [MC-1](README.md); frontend / UI-UX transition)
**Author**: Iwan Firmawan (with Claude)
**Date**: 2026-10-29
**Status**: Draft
**Effort**: ~6h (incl. agentic coding).
**Feeds**: [DIH-8](DIH-8_theming-per-client-brand.md) (consumes `primary_color`) and the module gating in [DIH-2](README.md)/[DIH-3](README.md)/[DIH-10](DIH-10_v2-ui-surface-port.md).

---

> **Multi-tenancy (WS-3):** the single-site setup wizard becomes **per-tenant self-service onboarding** ([MT-6](../3-multi-tenancy/MT-6_self-service-onboarding.md)) — two-phase register/activate, then a configure step that reuses this doc's colour picker + module toggles + boundary upload — writing **module flags to `Tenant.features`** (the single module store under WS-3, [MT-7](../3-multi-tenancy/MT-7_per-tenant-branding-config.md) — **not** a separate `SiteConfig.modules`) and `primary_color`/country config to the tenant's `SiteConfig`. The field/serializer work here stays valid; it runs in the onboarding flow, scoped to the new tenant. Standalone deploy = configuring the `default` tenant.

## 1. Context & Problem Statement

```
Setup wizard today (app/frontend/src/app/setup/):
  intro (page.js) -> step-1 (name, country, geojson, map_name_key, map_center, organizations[])
  -> step-2 (bounding box -> cdi_project_settings.json) -> step-3 (admin + reviewers) -> complete.

Backend (app/backend/api/v1/v1_setup/):
  SiteConfig = uuid, name, country, geojson_file, map_center, map_name_key (+ Organization).
  POST /setup -> SetupSerializer.create; GET /setup -> SetupResponseSerializer -> the frontend
  middleware caches it into the httpOnly `appConfig` cookie; getAppConfig() reads it.
  Setup endpoints are gated by the X-Setup-Secret header (SETUP_SECRET_KEY).

Gaps:
- SiteConfig has NO colour/theme field and NO module field.
- There is NO `modules` / DIH_MODULES concept anywhere in this app. "Modules" only exists
  at install time in configure.sh (service selection). GeoNode is wired via env vars.
- weather-station and IKS features do not exist in the generic app yet.

Goal:
- Let the team pick, during setup: (a) the client's brand colour, and (b) which optional
  modules the client uses — GeoNode, weather stations, IKS (and future optional modules).
- Both ride the existing SiteConfig -> serializers -> appConfig cookie path. No new endpoint,
  no new module framework in this task (the runtime gating infra is DIH-2).
```

---

## 2. Scope

- Backend: add `primary_color` + `modules` to `SiteConfig`; expose through both serializers.
- Wizard UI: add a colour picker + a module checkbox group to the wizard.
- Make `appConfig` carry both to the frontend.
- **Not** in scope: building the weather/IKS features themselves (they don't exist yet — ship the flag, build later, YAGNI), the runtime gating helper/URL-404 logic (DIH-2), and the theming consumption (DIH-8).

---

## 3. Data model changes (`app/backend/api/v1/v1_setup/models.py`)

| Field (on `SiteConfig`) | Type | Default | Purpose |
|---|---|---|---|
| `primary_color` | `CharField(max_length=7)` | `"#3E5EB9"` | brand colour (hex), consumed by DIH-8 |
| `modules` | `JSONField` | `{"geonode": true, "weather": false, "iks": false}` | optional-module flags for this client |

- One `modules` JSONField, not three Boolean columns — new toggles need no migration. `ponytail: JSON flag-bag; add a BooleanField only if a flag ever needs DB-level querying.`
- One migration adds both fields.
- Also add `is_host` (BooleanField, default `false`) to **`Organization`** — the host entry whose logo is the app's brand/header logo (DIH-10 OQ-3); same migration.

---

## 4. API contract (`serializers.py`)

- Add `primary_color` and `modules` to **`SetupSerializer`** (writable) **and** **`SetupResponseSerializer`** (read — so they reach the `appConfig` cookie).
- Multipart quirk: the wizard POSTs `multipart/form-data`; nested values arrive as strings. Parse `modules` in `SetupSerializer.to_internal_value` (where `organizations` is already hand-parsed), or accept a JSON string and `json.loads` it. `primary_color` is a plain string.
- `GET /setup` response gains `primary_color`, `modules` → `getAppConfig()` exposes them.

No new endpoint. `PUT /manage-setup/{uuid}` picks up the same fields for later edits.

---

## 5. Wizard UI (`app/frontend/src/app/setup/`)

**Placement (D-1): reuse Step 1** (smallest diff) with a new "Branding & modules" section, rather than a new stepper route. (If product wants a dedicated step, add it to the `steps` array in `setup/layout.js` + a route folder — larger diff.)

- **Brand colour**: a colour input bound to form field `primary_color`, default `#3E5EB9`. Use AntD `ColorPicker` (bundled since antd 5.5; the project is on `antd ^5.23`).
- **Modules**: a `Checkbox.Group` — `GeoNode`, `Weather stations`, `IKS` (extensible). Short helper text per item (e.g. "GeoNode: publish CDI layers to a GeoNode instance").
- Append both to the `FormData` in `onFinish` alongside `name`/`country`.

**Auth note**: setup POST/PUT must carry the `X-Setup-Secret` header when `SETUP_SECRET_KEY` is set — ensure `setupApiFormData` (in `@/lib/api`) injects it, same as `src/middleware.js` does for the GET probe.

---

## 6. Consumption (hand-off to other tasks)

- `primary_color` → **DIH-8** (`layout.js` ConfigProvider + `--primary-color`).
- `modules` → **DIH-2/DIH-3/DIH-10**: `getAppConfig().modules` gates menu items (`src/static/config.js` `PUBLIC_MENU_ITEMS`), routes, and optional panels; backend code that assumes GeoNode can gate on `SiteConfig.modules["geonode"]`.

---

## 7. Decisions

- **D-1: reuse Step 1**, don't add a stepper route (smaller diff; revisit if the section grows).
- **D-2: `modules` is a JSONField flag-bag** (one migration; future toggles are free).
- **D-3: `SiteConfig.modules` (per-instance, wizard-chosen) is the runtime source of truth**; the `DIH_MODULES` env var (DIH-2) is the **install-time default** that seeds the wizard and can hard-disable a module the deployment never ships. Precedence: a module is ON only if both the deployment allows it (env/availability) **and** the client enabled it (wizard). *Confirm in OQ-1.* **Under WS-3 the per-tenant store becomes `Tenant.features` ([MT-7](../3-multi-tenancy/MT-7_per-tenant-branding-config.md)), superseding `SiteConfig.modules`; the env×wizard precedence is unchanged.**
- **D-4: ship flags before features.** Weather/IKS UIs don't exist in the generic app; the toggles are inert until DIH-10 ports those surfaces. GeoNode flag gates DIH-1 (`v1_geonode`) + the CDI→hub sync.

---

## Implementation steps

1. **Model** (`app/backend/api/v1/v1_setup/models.py`): add `primary_color` (CharField, default `#3E5EB9`), `modules` (JSONField, callable `default_modules()` → `{"geonode":true,"weather":false,"iks":false}`), and `Organization.is_host` (Boolean). → verify: `makemigrations v1_setup` = one reversible migration; `migrate` forward **and** back clean.
2. **Serializers** (`serializers.py`): add `is_host` to `OrganizationSerializer`; add `primary_color` + `modules` to `SetupSerializer` **and** `SetupResponseSerializer` (so they ride the `appConfig` cookie); refactor the multipart `to_internal_value` to always parse `organizations[{i}][is_host]` and `json.loads` the `modules` string (`import json`). → verify: a multipart POST with `modules` + `is_host` round-trips; `GET /setup` returns them.
3. **Wizard Step 1** (`app/frontend/src/app/setup/step-1/page.js`): AntD `ColorPicker` (`primary_color`) + `Checkbox.Group` (geonode/weather/iks) + a per-org `is_host` checkbox; `initialValues` `primary_color:"#3E5EB9"`, `modules:["geonode"]`; in `onFinish`, append `primary_color`, `modules` (as JSON), and `organizations[{i}][is_host]` to the `FormData`. → verify: the wizard submits and `SiteConfig` persists the chosen colour + modules.
4. **Setup secret**: confirm `setupApiFormData` (`@/lib/api`) sends `X-Setup-Secret` (as `src/middleware.js` does), else POST/PUT 403 when `SETUP_SECRET_KEY` is set. → verify: submit succeeds with the secret configured.
5. **Cookie refresh** (`src/middleware.js`): clear the `appConfig` cookie on setup completion so the next request re-fetches `GET /setup` (it only re-fetches when the cookie is absent). → verify: after saving, a reload reflects the new colour/modules without waiting for the ~1-day TTL.

**Verify (goal-driven):** a test POSTs `/setup` with `primary_color="#C0392B"` + `modules={"geonode":false,"weather":true,"iks":false}`, asserts `SiteConfig` persists both and `GET /setup` returns them; run the migration forward and backward.

## User acceptance criteria

- As an **operator**, during first-run setup I pick a brand colour and toggle GeoNode / weather / IKS, and the running app reflects those choices — no file editing needed for the colour and module selection.

## 8. Technical acceptance criteria

- [ ] `SiteConfig` has `primary_color` + `modules` (one migration, reversible).
- [ ] Both serializers read/write them; `GET /setup` returns them; the `appConfig` cookie carries them.
- [ ] Step 1 saves a chosen colour and module set via the existing `POST /setup` (multipart), with the setup-secret header when required.
- [ ] `getAppConfig()` exposes `primary_color` and `modules` to the app.
- [ ] Defaults reproduce today's behaviour (colour `#3E5EB9`, GeoNode on).

**Verify by (goal-driven; write the check first, loop until green):**
1. **Backend test** — `POST /setup` with `primary_color="#C0392B"` and `modules={"geonode":false,"weather":true,"iks":false}`; assert the created `SiteConfig` persists both, and `GET /setup` returns them in the `SetupResponseSerializer` payload. Run the migration forward **and** backward (reversible).
2. **Cookie** — after a GET probe, assert the `appConfig` cookie JSON contains `primary_color` + `modules`.
3. **Frontend** — Step-1 submit assembles a `FormData` carrying `primary_color` + `modules` (and the `X-Setup-Secret` header when `SETUP_SECRET_KEY` is set); `getAppConfig()` then returns them.
Success criterion to loop on: a freshly-set-up fake instance exposes the chosen colour + module set via `getAppConfig()`.

---

## 9. Open questions

- [x] **OQ-1**: Confirm env-vs-wizard precedence for modules (D-3). Proposed: `effective = DIH_MODULES_allows(m) AND SiteConfig.modules[m]`. **— RESOLVED 2026-10-29: adopted.**
- [x] **OQ-2**: Colour picker — native `<input type="color">` vs AntD `ColorPicker`? **— RESOLVED 2026-10-29: use AntD `ColorPicker` (bundled since antd 5.5; project is ^5.23, no new dep).**
- [x] **OQ-3**: Should `cdi_project_settings.json` CDI **weights** also become wizard-editable here (today they come only from the template, not the wizard)? Likely a separate task; note and defer. **— RESOLVED 2026-10-29: defer; weights stay template-driven (scientific, see WS-1), not a wizard/branding concern.**

---

## 10. References

- Wizard: `app/frontend/src/app/setup/{page.js,layout.js,step-1,step-2,step-3,complete}`
- Backend: `app/backend/api/v1/v1_setup/{models.py,serializers.py,views.py,urls.py}`
- Config channel: `src/middleware.js` (appConfig cookie + X-Setup-Secret), `src/lib/app.js` (`getAppConfig`)
- Setup gate: `app/backend/utils/custom_middleware.py` (`SetupMiddleware`), `SETUP_SECRET_KEY`
