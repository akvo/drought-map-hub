# Feature Design Document

## Feature: Baseline store & percentile engine — per-component 40/14-year windows, Gaussian + empirical

**Task ID**: CDP-4 (sub-task of [MC-2](cdi-inhouse-percentiles.md))
**Author**: Iwan Firmawan (with Claude)
**Date**: 2026-10-12
**Status**: Draft
**Repo affected**: `drought-map-hub` → `cdi/` (after the [CDP-0](CDP-0_port-eswatini-pipeline.md) port; file/line refs to existing code point at the `eswatini-droughtmap-hub-cdi` source until then)

---

## 1. Context & Problem Statement

```
Currently:
- libs/statistics_operations.rank_parameter (lines 85-118) is the old toolkit's
  per-pixel, per-calendar-month empirical rank. Two defects:
    - the score tops out at (N−1)/N;
    - the divisor is wrong when the maximum is tied.
- The previous generation re-ranked ALL history on every run, so
  already-published values drifted month to month.
- NDMC now ranks against 40-year rolling histories, and its published maps look
  parametric. Two observations point that way:
    - ~100k distinct values per map;
    - ESI is capped at 100·Φ(±3).
  Neither is confirmed by NDMC yet.

Goal:
- Turn each derived index (CDP-3) into a 0–1 percentile per cell and month,
  against a stored, versioned baseline.
- The output is exactly the STEP_0100 contract that STEP_0301 already reads.
```

**Decided (MC-2 D-2, 2026-09-30)**: the baseline length is set per component. SPI, ESI and SM use 40 years. EVI2 uses the 14 years VIIRS provides.

---

## 2. Requirements

### User Acceptance Criteria
- [ ] Re-running any past month gives byte-identical percentiles within one baseline vintage.
- [ ] Every percentile file says which baseline it was ranked against (years, n, method, vintage).

### Technical Acceptance Criteria
- [ ] **Baseline store**:
  - Per param, per calendar month, per cell, it keeps the baseline sample (empirical) **and** μ, σ (Gaussian), computed once.
  - The window is `[end_year − years + 1, end_year]`, capped at the source start. For example SPI is 1986–2025 and EVI2 is 2012–2025.
- [ ] **Two methods, one switch** (`percentile.method`):
  - `gaussian`: p = Φ(clip((x − μ)/σ, −3, +3)). SPI is already a z-score from CDP-3, so it skips standardisation.
  - `empirical`: the mid-rank p = (count(b < x) + 0.5·count(b = x)) / n. This fixes both `rank_parameter` defects.
- [ ] A month **inside** the baseline is ranked against the same frozen baseline. It is not re-ranked when new months arrive.
- [ ] The yearly roll-forward is explicit (`--rebuild-baseline --end-year 2026`). It writes a new vintage and never overwrites the old one.
- [ ] A cell with fewer than 10 valid baseline years, or σ = 0, becomes nodata (−9999).
- [ ] The output file and variable names are exactly what STEP_0301 reads today: `output_data/STEP_0100_{ESI,EVI2,SPI,SM}_pct_rank_{region}.nc` with variables `esi_pct_rank`, `evi2_pct_rank`, `spi_pct_rank`, `sm_pct_rank`, on a 0–1 scale.
- [ ] Vectorised numpy. One Eswatini month for all 4 params takes under 5 s.

---

## 3. Data Model Changes

### Config (`cdi_project_settings.conf`)

```json
"percentile_source": "inhouse",
"baseline": { "years": 40, "end_year": 2025 },
"percentile": { "method": "gaussian", "clip_sigma": 3, "min_years": 10 }
```

### New files

```
working_data/baseline/{param}_{region}_v{end_year}.nc
    dims (month=12, lat, lon, year)
    variables: sample, mu, sigma, n_valid
    attrs: baseline_start, baseline_end, years, source_product
output_data/STEP_0100_{PARAM}_pct_rank_{region}.nc
    UNCHANGED contract, plus attrs: baseline_vintage, percentile_method
```

### Migration Strategy

```
- NDMC mode writes the same output files from STEP_0100 as today.
- inhouse mode writes them from this engine.
- STEP_0301 cannot tell the difference, which is the point.
```

---

## 4. API Contract

```python
# libs/percentiles.py (new)
def build_baseline(param: str, end_year: int, years: int) -> Path: ...
def percentile_gaussian(x: np.ndarray, mu: np.ndarray, sigma: np.ndarray, clip: float = 3.0) -> np.ndarray: ...
def percentile_empirical(x: np.ndarray, sample: np.ndarray) -> np.ndarray: ...
```

```bash
python cdi/src/cdi-scripts/STEP_0110_compute_inhouse_percentiles.py --param all --mode {recent|all}
python cdi/src/cdi-scripts/STEP_0110_compute_inhouse_percentiles.py --rebuild-baseline --end-year 2026
```

---

## 5. Decision Log

### D-1: Build both methods; Gaussian is the default until NDMC answers
**Rationale**:
- NDMC's maps look parametric (MC-2 §1.3, D-6), so Gaussian is the default.
- That is inferred, not confirmed. Keeping `empirical` beside it costs about 20 lines.
- CDP-5 can then report which of the two matches NDMC better before NDMC even replies.

### D-2: A frozen baseline with explicit yearly vintages
**Rationale**: reproducibility. A published month must never change silently; generation 1's drift came from re-ranking everything on every run.

**Impact**: publications carry `baseline_vintage`. A roll-forward is a deliberate, logged act.

### D-3: Clip Gaussian z at ±3σ
**Rationale**:
- This matches what NDMC's ESI shows (0.135–99.865).
- It also stops a single extreme value with a small σ from saturating the CDI.

---

## 6. Type/Constant Mappings

| Param | Baseline window (end 2025) | Method input |
|---|---|---|
| SPI | 1986–2025 (40) | the z from CDP-3 (no re-standardisation) |
| ESI | 1986–2025 (40) | the ratio from CDP-3 → z |
| SM | 1986–2025 (40) | weighted SM from CDP-3 → z |
| EVI2 | 2012–2025 (14) | EVI2 from CDP-3 → z |

---

## 7. Compatibility & Migration

### Backward Compatibility
- [ ] The STEP_0100 output contract is unchanged. The existing `test_cdi_pipeline.py` fixtures must pass when fed by this engine.
- [ ] `rank_parameter` is kept until CDP-6 deletes it.

### Seeder/CLI Compatibility
- [ ] New: `STEP_0110_compute_inhouse_percentiles.py`, with `--rebuild-baseline`.

---

## 8. Security Considerations

- [ ] Local files only.

---

## 9. Testing Strategy

| Test Type | Coverage |
|---|---|
| Unit | Gaussian: p(μ) = 0.5, the clip at ±3 gives 0.00135 / 0.99865, σ = 0 → nodata. Empirical: ties, n = 1, the maximum value gives (n − 0.5)/n rather than (n − 1)/n, and NaN is excluded. A frozen baseline gives an identical result after a new month is appended. A vintage rebuild leaves the old vintage file untouched. |
| Integration | Synthetic 40-year fields → baseline → percentiles → STEP_0301 → STEP_0303; the export contract is unchanged. Reuse the `project` fixture from `test_cdi_pipeline.py`. |
| Performance | One Eswatini month, all 4 params, under 5 s. A full 40-year baseline build is timed and recorded in the PR. |

---

## 10. Open Questions

- [ ] **OQ-1**: Gaussian or empirical, and is the method the same for every index? SM and SPI reach exactly 0 and 100 in NDMC's files, which a pure Φ never produces. **— PENDING: NDMC to confirm the percentile method; working default: Gaussian percentiles (D-6), with the empirical mid-rank reported alongside.**
- [ ] **OQ-2**: What does "rolling" mean in NDMC's 40-year window: refreshed yearly, or every month? **— PENDING: NDMC to confirm the rolling-window meaning; working default: one baseline vintage refreshed yearly (D-3).**
- [ ] **OQ-3**: Does STEP_0302's pooled re-rank of the CDI still make sense when the inputs are true percentiles? That step is our own, not NDMC's. Decide after CDP-5. **— DEFERRED to after CDP-5: keep the pooled re-rank for now; revisit once validation shows whether true-percentile inputs change the D-class agreement.**

---

## 11. References

- Parent design: [MC-2](cdi-inhouse-percentiles.md) D-2, D-3, D-6, §1.3
- Method references: kept in an internal method-references note (not in this repo).
- Code: `cdi-scripts/libs/statistics_operations.py:85-118`, `STEP_0302_rank_cdi_pooled.py`, `__tests__/test_cdi_pipeline.py`

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | | | |
| Tech Lead | | | |
| Product | | | |
