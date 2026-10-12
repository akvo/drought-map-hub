# Feature Design Document

## Feature: Eswatini validation — in-house vs NDMC comparison report, then NDMC method review

**Task ID**: CDP-5 (sub-task of [MC-2](../cdi-inhouse-percentiles.md))
**Author**: Iwan Firmawan (with Claude)
**Date**: 2026-10-12
**Status**: Draft
**Repo affected**: `drought-map-hub` → `cdi/` (after the [CDP-0](CDP-0_port-eswatini-pipeline.md) port; file/line refs to existing code point at the `eswatini-droughtmap-hub-cdi` source until then) (report tool). The NDMC review is a process step, not code.
**Blocked by NDMC?** No. The comparison uses NDMC's already-published Eswatini files. NDMC's review comes *after* this report (MC-2 D-1).

---

## 1. Context & Problem Statement

```
Currently:
- Eswatini is the ONLY country where we hold both sides of the comparison:
    - NDMC's published percentiles, Regional_Percentiles/Southern_Africa,
      2012–2026; all four inputs start in 2012 since NDMC's 11 Aug 2026 backfill;
    - soon, our own in-house percentiles (CDP-1 → CDP-4).
- Without a measured comparison, "our method matches NDMC" is an untested claim.
  And the decisions left open in CDP-3 and CDP-4 have no evidence behind them:
    - Gaussian vs empirical,
    - the EVI2 sensor offset,
    - the ESI variables.

Goal:
- A reproducible report that answers, per input and for the final CDI:
  "how close is in-house to NDMC, and where does it differ?"
- Send it to NDMC with our method questions, for review.
- Turn the report into the go/no-go for CDP-6.
```

---

## 2. Requirements

### User Acceptance Criteria
- [ ] One command produces a report (Markdown + PNG maps) comparing in-house and NDMC for Eswatini, 2012-01 → latest month.
- [ ] The report states a clear **PASS / FAIL** against the agreed threshold (OQ-1).
- [ ] The report is attached to the NDMC email (§4.3) along with our method summary.

### Technical Acceptance Criteria
- [ ] Per param (ESI, EVI2, SPI, SM) and for the CDI, per month, computed on cells valid on both sides:
  - Pearson r,
  - mean bias,
  - RMSE in percentile points.
- [ ] **D-class agreement**:
  - Both sides are mapped through the hub's D0–D4 cut-offs (0.30 / 0.20 / 0.10 / 0.05 / 0.02).
  - The report shows a confusion matrix and the share of cells in the same class and within one class.
- [ ] **Inkhundla level**:
  - Aggregate both sides per Inkhundla using the hub's own extraction rule and `source/eswatini.topojson`, with `all_touched=True`.
  - Report the share of the 59 Tinkhundla in the same D-class. This is the number partners would see.
- [ ] **Method A/B**: the in-house side runs twice, `gaussian` and `empirical` (CDP-4), and the report shows both.
- [ ] **ESI variants**: run ERA5-Land and ERA5 `pev` if both are fetched (CDP-1 OQ-1).
- [ ] NDMC files are read **directly** from `Regional_Percentiles` downloads, never from GeoNode. They are different vintages (hub memory note). The report records each NDMC file's HTTP `Last-Modified`.
- [ ] The tool is deterministic; re-running gives the same numbers.

---

## 3. Data Model Changes

There are no database changes. The output is:

```
output_data/validation/{region}_{run_date}/
  report.md                    # summary, PASS/FAIL, tables
  metrics.csv                  # param, method, month, r, bias, rmse, same_class, within_one
  inkhundla_agreement.csv      # month, administration_id, ndmc_class, inhouse_class
  maps/{param}_{YYYYMM}.png    # NDMC | in-house | difference, for the 6 worst months
```

### Migration Strategy

```
- Read-only on both inputs.
- Nothing in production changes.
```

---

## 4. API Contract

### 4.1 CLI

```bash
python cdi/src/cdi-scripts/compare_ndmc.py --region Eswatini --from 2012-01 --to latest \
       --methods gaussian,empirical [--admin-topojson path/to/eswatini.topojson]
```

### 4.2 Pass criteria (proposed; to confirm in OQ-1)

| Level | Metric | Pass |
|---|---|---|
| Inkhundla | same D-class | ≥ 80% of Tinkhundla-months |
| Inkhundla | more than 1 class apart | 0 |
| Cell, per param | Pearson r (median over months) | ≥ 0.8 |

### 4.3 NDMC review step (process)

1. Attach `report.md` (exported as PDF) and `metrics.csv` to a reply on the methodology thread.
2. State our method in one paragraph per index, and point to the remaining questions (Q1–Q6).
3. Supporting evidence: [ndmc-method-questions-references.md](../ndmc-method-questions-references.md).
4. Record NDMC's feedback as decisions in MC-2 and the CDP docs. Re-run the report if the method changes.

---

## 5. Decision Log

### D-1: Validate at the Inkhundla level, not only per pixel
**Rationale**:
- Partners see one D-class per Inkhundla, not pixels.
- Two maps can differ cell by cell and still agree where it matters. The reverse is also possible.

### D-2: Compare against NDMC files, never GeoNode
**Rationale**: the GeoTIFF archive and GeoNode hold different vintages for the same month. 0/59 values matched for CDI 2026-05 (hub memory note).

### D-3: Report both percentile methods before NDMC answers
**Rationale**:
- Whichever matches NDMC better is empirical evidence for Q2.
- It also makes the NDMC conversation concrete ("Gaussian matches your files at r = X, empirical at Y").

---

## 6. Type/Constant Mappings

These are the same cut-offs as the hub's `get_category()` (`backend/api/v1/v1_publication/utils.py:112`). The value is rounded to 3 decimals first, and a negative value means No Data. Codes are `DroughtCategory`.

| D-class | Hub cut-off (percentile ≤) | Code |
|---|---|---|
| D4 | 0.02 | 5 |
| D3 | 0.05 | 4 |
| D2 | 0.10 | 3 |
| D1 | 0.20 | 2 |
| D0 | 0.30 | 1 |
| Normal | > 0.30 | 0 |

---

## 7. Compatibility & Migration

### Backward Compatibility
- [ ] Read-only. Production NDMC mode is untouched.

### Seeder/CLI Compatibility
- [ ] New CLI: `compare_ndmc.py`.

---

## 8. Security Considerations

- [ ] The report contains no credentials or personal data and can be shared with NDMC.

---

## 9. Testing Strategy

| Test Type | Coverage |
|---|---|
| Unit | Identical inputs give r = 1, bias = 0, 100% same class. A known shift of +0.1 gives bias = 0.1. D-class mapping at the exact cut-offs. Nodata on either side is excluded. Inkhundla aggregation matches the hub's extractor on a fixture polygon. |
| Integration | 12 months of real NDMC files against themselves (sanity: a perfect score), then against a 12-month in-house run. |

---

## 10. Open Questions

- [x] **OQ-1**: Confirm the pass thresholds in §4.2 with the TWG and NDRMA. These are the people who would notice a class change. **— RESOLVED 2026-10-12 (working default): ≥80% of admin units in the same D-class and none more than one class apart; TWG/NDRMA still confirm before the formal sign-off.**
- [x] **OQ-2**: Who sends the review email: Iwan, Maurits or Jacob? This is MC-2 OQ-1. **— RESOLVED 2026-10-12: Iwan sends it directly.**
- [x] **OQ-3**: If it fails, what is the fallback? Proposed order: change the percentile method → ESI to weight 0 → EVI2 sensor offset on. Re-run after each. **— RESOLVED 2026-10-12: adopt the proposed fallback order.**

---

## 11. References

- Parent design: [MC-2](../cdi-inhouse-percentiles.md) §9, D-1
- NDMC email reference pack: [ndmc-method-questions-references.md](../ndmc-method-questions-references.md)
- NDMC data: https://droughtcenter.unl.edu/Outgoing/Regional_Percentiles/Southern_Africa/
- Hub extraction: `backend/api/v1/v1_jobs/job.py` (`generate_initial_cdi_values`); boundaries: `backend/source/eswatini.topojson`

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | | | |
| Tech Lead | | | |
| Product | | | |
