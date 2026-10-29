# Feature Design Document

## Feature: Per-client theming — configurable brand color, `tokens.js` as the baseline

**Task ID**: DIH-8 (sub-task of [MC-1](README.md); frontend / UI-UX transition)
**Author**: Iwan Firmawan (with Claude)
**Date**: 2026-10-29
**Status**: Draft
**Effort**: ~6h (incl. agentic coding) — theming MVP; the full 63-literal sweep is DIH-10 Phase A.
**Depends on**: [DIH-9](DIH-9_setup-wizard-theme-and-modules.md) for the `SiteConfig.primary_color` field that this task consumes.

---

## 1. Context & Problem Statement

```
Eswatini hub (source of the v2 look):
- src/static/tokens.js is the single source of truth (module.exports), brand.primary = "#3E5EB9".
- It fans out to Tailwind (tailwind.config.js theme.extend.colors.primary) and to
  Ant Design (src/static/ant-theme.js -> src/app/layout.js <ConfigProvider theme>).
- A second theme (src/static/cw-theme.js, --edm-* CSS vars) themes the Citizen-Weather sub-app.
- BUT 63 hard-coded "#3E5EB9" literals bypass the token (DS components, ECharts option
  objects, Leaflet HTML-string tooltips, globals.css --primary-color, a rogue second
  <ConfigProvider> in Insights/IksTab). The drought-band palette is deliberately separate
  (static/config/drought.js DROUGHT_CATEGORY_COLOR) and is NOT a brand colour.

Generic hub (target):
- No tokens.js. The brand colour "#3E5EB9" is hard-coded in exactly three places:
  src/app/layout.js (ConfigProvider token colorPrimary/colorLink + Tabs ink colours),
  tailwind.config.js (colors.primary), src/app/globals.css (--primary-color).
- src/app/layout.js already calls getAppConfig() (the SSR appConfig cookie), so a
  per-client value can arrive there with no new plumbing.

Goal:
- One per-client brand colour, chosen in the setup wizard (DIH-9), defaulting to the
  Eswatini baseline, applied app-wide (Ant Design + Tailwind + raw CSS).
- Keep tokens.js as the baseline/default palette so the v2 look is preserved.
- No hard-coded brand-colour literal survives (the drought-band palette stays separate).
```

---

## 2. Scope

- Make the **primary/brand colour** configurable per deployment. Other tokens (neutrals, spacing, radii, fonts, component sizing) are ported as a **fixed baseline** from Eswatini `tokens.js` — not per-client in this task.
- Out of scope: the admin-unit label, logos, module gating (DIH-9 / DIH-10); porting the actual pages/components (DIH-10). This task only establishes the **theming spine** so ported components inherit the configurable colour.

---

## 3. Approach

**One source, one override, three sinks.**

1. **Port `tokens.js` as the baseline.** Copy Eswatini `src/static/tokens.js` into the generic `app/frontend/src/static/tokens.js` unchanged (keeps the v2 palette, sizing, radii). `tokens.brand.primary = "#3E5EB9"` becomes the **default**, not a hard-code.
2. **Build `ant-theme.js` from tokens** (port Eswatini `src/static/ant-theme.js`) so `layout.js` imports a theme object instead of an inline literal.
3. **Single runtime override = `appConfig.primary_color`** (from `SiteConfig`, DIH-9). Resolve once: `const primary = appConfig?.primary_color || tokens.brand.primary`.
4. **Three sinks, all fed from that one value:**
   - **Ant Design** — `src/app/layout.js` `<ConfigProvider theme={{ token: { colorPrimary: primary, colorLink: primary, ... } }}>` (and the Tabs ink/active colours that currently repeat the literal). SSR, so it is correct per render.
   - **CSS variable** — set `--primary-color: <primary>` once on `<body>` (inline style in `layout.js`, from the same resolved value). `globals.css` keeps `--primary-color` only as a static fallback default.
   - **Tailwind** — `tailwind.config.js` `colors.primary = "var(--primary-color)"` so every `text-primary`/`bg-primary` tracks the CSS var (Tailwind can't be per-request, but a CSS var makes it dynamic).
5. **Eliminate stray literals** (relevant when DIH-10 ports Eswatini components): CSS and HTML-string contexts (ECharts/Leaflet tooltips, `globals.css`) read `var(--primary-color)`; JS chart option objects read the imported token or a runtime theme value; remove the rogue second `<ConfigProvider>` in `IksTab`. In the generic hub today only the three spots in §1 exist, so the generic sweep is small; the 63-literal sweep lands with the component port (DIH-10).
6. **Citizen-Weather** (`cw-theme.js`, `--edm-*`) — only if/when that sub-app is ported (DIH-10); drive its vars from the same resolved colour.

The **drought-band palette** (`DROUGHT_CATEGORY_COLOR`) is explicitly left out — it is data semantics, not branding.

---

## 4. Files to touch (generic `app/frontend`)

| File | Change |
|---|---|
| `src/static/tokens.js` | **new** — port Eswatini tokens as the baseline default |
| `src/static/ant-theme.js` | **new** — port; builds the AntD theme object from tokens, `colorPrimary` overridable |
| `src/app/layout.js` | resolve `primary = appConfig?.primary_color \|\| tokens.brand.primary`; pass to `ConfigProvider` + set `--primary-color` on `<body>`; replace the three literal colours + Tabs ink colours |
| `tailwind.config.js` | `colors.primary = "var(--primary-color)"` (keep other extends from tokens) |
| `src/app/globals.css` | `--primary-color` default = token value (static fallback); drop the hand-maintained duplicate literal |

Backend field is DIH-9.

---

## 5. Decisions

- **D-1: tokens.js stays the baseline, only `brand.primary` is per-client.** Rationale: the v2 look (neutrals, sizing, radii, fonts) should be consistent across clients; only the brand accent is a client identity. Keeps the diff small and the design coherent. Revisit if a client needs a fuller palette.
- **D-2: `var(--primary-color)` is the cross-cutting mechanism** for Tailwind + raw CSS + HTML-string chart tooltips; AntD uses the resolved value via `ConfigProvider`. One value set on `<body>` drives all. Rationale: Tailwind/CSS/ECharts-HTML can't read the AntD token, but all read a CSS var.
- **D-3: default colour = `#3E5EB9`** (Eswatini brand) so an un-themed / Eswatini deployment is byte-identical to today.

---

## Implementation steps

Consumes the `primary_color` that [DIH-9](DIH-9_setup-wizard-theme-and-modules.md) delivers in `appConfig` (incl. its cookie-refresh). Wire the one colour through 3 sinks:

1. **`src/app/layout.js`**: `const primary = appConfig?.primary_color || "#3E5EB9"`; put `style={{ "--primary-color": primary }}` on `<body>`; in `ConfigProvider` set token `colorPrimary`/`colorLink = primary` + the Tabs ink colours. → verify: a fake `appConfig` colour themes the AntD primary and sets `--primary-color` on `body`.
2. **`tailwind.config.js`**: `primary: "#3e5eb9"` → `primary: "var(--primary-color)"`. → verify: `.text-primary` / `.bg-primary` follow the runtime colour.
3. **`src/app/globals.css`**: keep `--primary-color: #3e5eb9` as the **static fallback** (the inline var on `<body>` overrides it at runtime). → verify: a no-cookie render still shows `#3E5EB9`.

> MVP = one configurable colour app-wide. Porting the full Eswatini `tokens.js` (neutrals/sizing/`ant-theme.js`) + sweeping the 63 literals is **DIH-10 Step A**, not here.

**Verify (goal-driven):** boot a fake `appConfig` with `primary_color="#C0392B"` → assert (1) an AntD primary `Button` bg = `#C0392B`, (2) `getComputedStyle(body).getPropertyValue('--primary-color')` = `#C0392B`, (3) a `.text-primary` colour = `#C0392B`; empty colour → renders `#3E5EB9`.

## User acceptance criteria

- As a **visitor**, I see the deployment's brand colour consistently across the app — buttons, links, charts, map accents — with no stray Eswatini blue (`#3E5EB9`) unless that is the chosen colour.

## 6. Technical acceptance criteria

- [ ] Setting `primary_color` in the wizard (DIH-9) recolours the whole app: AntD controls, `text-primary`/`bg-primary` utilities, and CSS-var-driven styles — without a rebuild (SSR picks it from the cookie).
- [ ] With no `primary_color` set, the app renders exactly as today (`#3E5EB9`).
- [ ] No hard-coded brand-colour literal remains in the generic frontend except the single token default; grep for `#3[eE]5[eE]B9` returns only `tokens.js`/`globals.css` fallback.
- [ ] Drought-band colours are unchanged (not affected by the brand colour).
- [ ] `tokens.js` present and imported by both Tailwind and `ant-theme.js`.

**Verify by (goal-driven; write the check first, loop until green):** boot a fake `SiteConfig` with `primary_color = "#C0392B"`, then assert, in one test run:
1. a rendered AntD primary `Button`'s computed background = `#C0392B`;
2. `getComputedStyle(document.body).getPropertyValue('--primary-color')` = `#C0392B`;
3. a `.text-primary` element's computed colour = `#C0392B`;
4. `grep -rE "#3[eE]5[eE]B9" app/frontend/src` returns only `tokens.js`/`globals.css` fallback;
5. the drought-band legend swatches are unchanged.
Then set `primary_color` empty → the app renders identical to today (`#3E5EB9`). (Jest + @testing-library for 1–3/5; the grep for 4; a Playwright smoke on the running app is the end-to-end form.)

---

## 7. Open questions

- [x] **OQ-1**: Contrast/accessibility — should the wizard validate the chosen colour for min contrast against white text on buttons, or derive `colorPrimaryHover`/active shades automatically (AntD does this from `colorPrimary`)? Proposed: rely on AntD's derived shades; add a soft contrast warning in the picker (DIH-9). **— RESOLVED 2026-10-29: AntD-derived shades + a soft, non-blocking contrast warning.**
- [x] **OQ-2**: Do we also expose a couple of secondary brand tokens (e.g. `brand.dark` for the nav) per client, or only `primary`? Proposed: only `primary` now; AntD derives the rest. **— RESOLVED 2026-10-29: `primary` only; AntD derives hover/active/shades.**

---

## 8. References

- Eswatini theming: `eswatini-droughtmap-hub/frontend/src/static/{tokens.js,ant-theme.js,cw-theme.js}`, `src/app/layout.js`
- Generic theming today: `app/frontend/src/app/layout.js`, `tailwind.config.js`, `src/app/globals.css`
- Config channel: `app/frontend/src/lib/app.js` (`getAppConfig`), `src/middleware.js` (appConfig cookie)
