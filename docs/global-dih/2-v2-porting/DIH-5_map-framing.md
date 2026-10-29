# Feature Design Document

## Feature: Map framing from boundary bounds (drop fixed centre/zoom)

**Task ID**: DIH-5
**Author**: Iwan Firmawan (with Claude)
**Date**: 2026-10-30
**Status**: Draft
**Effort**: ~2h (incl. agentic coding).
**Depends on**: [DIH-4](DIH-4_country-pack.md)

> Eswatini-hub file:line refs; re-map to `drought-map-hub/app` when executing.

---

## 1. Context

The prior art hard-codes map centre from a centroid and zoom to 6/9 — wrong for every country but the one it was tuned on. Framing should be **derived** from the loaded boundary, not configured.

## 2. Scope

Map framing only. The boundary itself comes from DIH-4; nothing here is per-client config.

## 3. Approach + files

- `CDIMap` and the four zoom-9 copies (`LayerMap.js:198,277`, `OverviewMap.js:133`, `InkhundlaMap.js:177`) call `fitBounds` on the loaded topojson; remove `DEFAULT_CENTER` rather than moving it into config.
- **Already partly done** in the generic hub: `app/frontend/src/components/Map/CDIMap.js` now `fitBounds` + lowered default zoom (committed earlier). This task finishes the remaining copies.

## 4. Decisions

- MC-1 prior-art row: replace fixed zoom with `fitBounds`; framing is derived, not configured.

## Implementation steps

1. In `app/frontend/src/components/Map/CDIMap.js`, make `map.fitBounds(bounds)` (already present at `:44`) the sole framing path; remove the `DEFAULT_CENTER` fallbacks (`:92,96,100`) and the hard-coded `zoom={6}` (`:118`). → verify: the map frames to the loaded topojson bounds, no `[0,0]` flash.
2. Derive the initial centre/zoom from the bounds (or `appConfig.map_center` if set). → verify: a non-Eswatini fixture frames correctly.
3. Handle the other `DEFAULT_CENTER` importers (`Map/GetCoordinates.js`, `static/config.js`) — the setup step-2 map (`setup/step-2/page.js:214`) already uses `fitBounds`; keep or repoint `DEFAULT_CENTER` so nothing else breaks. → verify: grep `DEFAULT_CENTER` callers all handled; setup map still works.

## User acceptance criteria

- As a **visitor or reviewer**, when I open any map it is centred and zoomed on the deployment's own country — not on Eswatini — whichever country is deployed.

## 5. Technical acceptance criteria

- [ ] Every map opens framed on the deployment's own boundary; no `DEFAULT_CENTER` / fixed-zoom literals remain.
- [ ] Eswatini still frames correctly.

**Verify by (goal-driven):** load a non-Eswatini fixture boundary → the map viewport contains its bbox (assert `getBounds()` within the fitted view); grep shows no residual `DEFAULT_CENTER` / `zoom={9}`.

## 6. Dependencies / hand-offs

- Needs DIH-4 (boundary). Part of the frontend transition under [DIH-10](DIH-10_v2-ui-surface-port.md).

## 7. References

- [MC-1](README.md) §4.3 + prior-art table.
