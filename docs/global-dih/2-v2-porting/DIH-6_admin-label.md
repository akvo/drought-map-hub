# Feature Design Document

## Feature: Admin-unit label from config (`useAdminLabel()`)

**Task ID**: DIH-6
**Author**: Iwan Firmawan (with Claude)
**Date**: 2026-10-30
**Status**: Phase 6a done (#24); Phase 6b N/A in this repo (see below)
**Effort**: ~11h total (incl. agentic coding) → 2 phases ≤8h each (see Phases): 7a ~7h, 7b ~4h.
**Depends on**: [DIH-4](DIH-4_country-pack.md) (provides `country.admin_label`), [DIH-3](DIH-3_module-flags-frontend.md) (delivers it to the app)

> Eswatini-hub file:line refs; re-map to `drought-map-hub/app` when executing.

---

## 1. Context

"Inkhundla"/"Tinkhundla" (the Siswati admin-unit noun, singular/plural) appears ~333× in the frontend and ~287× in the backend. The user-visible noun must come from config so another country reads "District/Districts", etc.

## 2. Scope

**User-visible strings only** — UI copy, emails, the PDF brief. Not identifiers (variable/component names like `InkhundlaHeader`), which carry risk and no user benefit. This is the largest mechanical piece, split out as its own task.

## 3. Approach + files

> **As built (#24):** delivery is via **`SiteConfig.admin_label`** (a JSONField `{one, many}`), not `country.json`/`config.js`. The wizard (DIH-9 Step 1) captures it, `SetupResponseSerializer` rides it on the `appConfig` cookie, and the frontend reads it with `useAdminLabel()` / `getAppConfig().admin_label` (both falling back to the Eswatini default). This is the agreed "wizard over country.json" approach; `country.json` (DIH-4) keeps zones / region colours / agencies. The original plan below is kept for context.

- Source: `country.admin_label.{one,many}` in `country.json` (DIH-4), delivered via `config.js`/`appConfig` (DIH-3). **(Superseded: now `SiteConfig.admin_label` + wizard, above.)**
- Frontend: a `useAdminLabel()` hook; backend: ~~`settings.COUNTRY["admin_label"]`~~ `SiteConfig.admin_label`.
- Replace user-facing literals, e.g. `ValidationTable.js:42,134,149` ("Inkhundla", "Tinkhundla", "Search Inkhundla") and copy in `static/config/review.js:46,51`, `static/config/activity.js:22`.

## 4. Decisions (MC-1 Decision Log)

- **D-4**: ~~admin label lives in `country.json`, delivered via `config.js`~~; **as built (#24): admin label lives in `SiteConfig.admin_label`, set in the setup wizard and delivered on the `appConfig` cookie.** Still: replace only user-visible strings, not identifiers.

## Implementation steps

**Phase 6a — UI copy — DONE (#24):**
1. ~~Deliver `country.admin_label` via `appConfig` (from `country.json`).~~ **Done differently:** `SiteConfig.admin_label` JSONField (migration `0003`) → `SetupResponseSerializer`/`SetupSerializer` → `appConfig` cookie; wizard Step 1 captures it. → verified: the cookie carries `admin_label`.
2. `useAdminLabel()` hook (+ `getAppConfig().admin_label` for server components), both with the Eswatini fallback. → verified by `useAdminLabel.test.js`.
3. Replaced user-visible literals across validation / review / publication surfaces + setup Step 1. → verified: leak grep finds no `Inkhundla/Tinkhundla` in user-visible frontend strings.

**Phase 6b — email + PDF — N/A in this repo:**
4. No email HTML templates and no PDF brief generator exist in `app/backend` yet (they arrive with the DIH-10 v2 UI port). Leak grep is already clean on templates. Revisit when those surfaces land; use `SiteConfig.admin_label` (not `settings.COUNTRY`) as the source then.

## User acceptance criteria

- As a **user**, everywhere I read the admin-unit word — on screen, in emails, and in the PDF brief — it uses my country's term (e.g. "District/Districts"), never "Inkhundla/Tinkhundla".

## 5. Technical acceptance criteria

- [ ] The admin-unit word + plural come from config everywhere a user reads them (UI, email, PDF).
- [ ] Identifiers/variable names are untouched.
- [ ] CI leak check passes: no hard-coded `Inkhundla/Tinkhundla` in user-visible frontend strings or email/PDF templates (allow-list: `source/`, tests, comments).

**Verify by (goal-driven):** a frontend test renders a component with `admin_label={one:"District",many:"Districts"}` and asserts the rendered copy; the MC-1 §9 leak-check grep returns clean.

## Phases (≤8h each)

| Phase | Effort | Scope | Status |
|---|---|---|---|
| **7a** UI copy | ~7h | Replace user-visible "Inkhundla/Tinkhundla" in frontend components via `useAdminLabel()` (source: `SiteConfig.admin_label` + wizard) | ✅ Done (#24) — label renders from config; leak grep clean on user-visible frontend strings |
| **7b** email + PDF | ~4h | Replace the admin noun in email templates + the PDF brief via `SiteConfig.admin_label` | ⏸ N/A here — no email/PDF surfaces in `app/backend` yet; lands with DIH-10 |

## 6. Dependencies / hand-offs

- Needs DIH-4 + DIH-3. Folded into the frontend transition [DIH-10](DIH-10_v2-ui-surface-port.md).

## 7. References

- [MC-1](README.md) §5 D-4, §2, §9 (leak check).
