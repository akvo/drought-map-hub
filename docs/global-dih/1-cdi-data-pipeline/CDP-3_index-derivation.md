# Feature Design Document

## Feature: Index derivation — SPI, soil moisture, EVI2, ESI from raw fields

**Task ID**: CDP-3 (sub-task of [MC-2](../cdi-inhouse-percentiles.md))
**Author**: Iwan Firmawan (with Claude)
**Date**: 2026-10-12
**Status**: Draft
**Repo affected**: `drought-map-hub` → `cdi/` (after the [CDP-0](CDP-0_port-eswatini-pipeline.md) port; file/line refs to existing code point at the `eswatini-droughtmap-hub-cdi` source until then)
**Blocked by NDMC?** **ESI: yes.** The formula and variables wait for NDMC Q1. SPI, SM and EVI2 can start now, with their NDMC questions (Q3–Q5) treated as configuration choices, not code rewrites.

---

## 1. Context & Problem Statement

```
Currently:
- No index is derived; NDMC delivers finished percentiles.
- Dead or broken code for some indices already exists in the repo, inherited
  from NDMC's old CDI toolkit:
    libs/spi_calculations.py  calculate_monthly_spi: Thom gamma fit, zero-rain
                              mixed term, Φ⁻¹. Not called anywhere.
    STEP_0104                 FLDAS depth weighting (lines 118-120). Not called;
                              KeyErrors on removed config keys (lines 19, 31).
    libs/hdf_functions.py, h4toh5convert   MODIS HDF4 helpers. Unreferenced.

Goal:
- For each month, turn CDP-2's regridded raw fields into one index value per
  0.05° cell.
- CDP-4 then standardises and percentiles these values against the baseline.
- Each index has its definition in one place, with its constants in config, so
  NDMC's answers change config rather than code.
```

---

## 2. Requirements

### User Acceptance Criteria
- [ ] For every month in the history, each enabled parameter has one derived-index file over the country grid.

### Technical Acceptance Criteria
- [ ] **SPI-3**:
  - 3-month rolling precipitation totals.
  - A gamma fit per pixel and per calendar month over the baseline window from CDP-4.
  - Zero-rain probability handled with the mixed term.
  - z = Φ⁻¹(H).
  - Reuses `calculate_monthly_spi`, vectorised and with tests added.
- [ ] **SM**: 0–100 cm root zone = 0.1·(0–10) + 0.3·(10–40) + 0.6·(40–100) cm. These are the toolkit's `RootZone2` weights, and they are config, not constants.
- [ ] **EVI2**:
  - Read `1 km monthly EVI2` (×10000, fill −15000), masked by the pixel-reliability/QC layer.
  - Area-mean is done in CDP-2.
  - **Sensor splice**: VNP13A3 up to and including 2026-10, VJ113A3 after.
  - Over the 2018-01 → 2026-10 overlap, compute a per-pixel, per-calendar-month mean offset (VJ1 − VNP). Apply it only if it is significant (OQ-2). Store it in `working_data/evi2_sensor_offset.nc`.
- [ ] **ESI** (provisional until NDMC Q1):
  - ratio = actual ET / potential ET from ERA5(-Land) monthly means.
  - Sign convention: ECMWF uses negative = evaporation, so flip the sign.
  - Units: monthly means are per-day values in m; ×1000 gives mm/day.
  - `pev ≤ 0` cells → nodata.
  - The formula sits behind one function, `derive_esi()`, so the NDMC answer replaces exactly that function.
- [ ] Every output is float32, on the CDP-2 grid, with −9999 for nodata, and carries `derivation` and `source` attributes.
- [ ] Derivation of one month is deterministic: same inputs, same bytes.

---

## 3. Data Model Changes

### Config (`cdi_project_settings.conf`)

```json
"derivation": {
  "spi":  { "accumulation_months": 3, "distribution": "gamma" },
  "sm":   { "layers_cm": [[0,10],[10,40],[40,100]], "weights": [0.1, 0.3, 0.6] },
  "evi2": { "splice_month": "2026-11", "apply_sensor_offset": "auto" },
  "esi":  { "et": "total_evaporation", "pet": "potential_evaporation", "status": "provisional" }
}
```

### New working files

```
working_data/index/{PARAM}/{param}_{region}_{YYYYMM}.nc   # derived index, CDP-2 grid
working_data/evi2_sensor_offset.nc                         # 12 × lat × lon, VJ1 − VNP
```

### Migration Strategy

```
- Additive.
- STEP_0104 / STEP_0204 and the unused HDF helpers are deleted in CDP-6, after
  this task supersedes them.
```

---

## 4. API Contract

```python
# libs/indices.py (new) — one function per index, pure: arrays in, array out
def derive_spi(precip_monthly: np.ndarray, baseline_mask: np.ndarray, accumulation: int = 3) -> np.ndarray: ...
def derive_sm(layers: list[np.ndarray], weights: list[float]) -> np.ndarray: ...
def derive_evi2(evi2_raw: np.ndarray, qc: np.ndarray) -> np.ndarray: ...
def derive_esi(et: np.ndarray, pet: np.ndarray) -> np.ndarray: ...   # provisional (NDMC Q1)
```

```bash
python cdi/src/cdi-scripts/derive_indices.py --param {spi|sm|evi2|esi|all} --from YYYY-MM --to YYYY-MM
```

---

## 5. Decision Log

### D-1: Reuse the NDMC toolkit's SPI and SM definitions
**Rationale**:
- They are NDMC's own code (`scripts_update.zip`), and our repo already carries copies.
- Matching NDMC is the validation target (CDP-5).

**Impact**: `calculate_monthly_spi` gets vectorised and tested instead of rewritten.

### D-2: SPI stays a z-score here; the percentile happens in CDP-4
**Rationale**:
- The old toolkit ranked SPI empirically. NDMC's current method is unknown (Q2).
- Keeping derivation (z) separate from the percentile step lets CDP-4 switch between Gaussian and empirical without touching SPI.

### D-3: The EVI2 sensor offset is measured, not assumed
**Options**:
1. Splice VNP13A3 → VJ113A3 raw.
2. Always apply an offset.
3. Measure the offset over the 8-year overlap and apply it only if it is significant.

**Decision**: 3.

**Rationale**: both are VIIRS on sister satellites, so the bias may be negligible. A forced correction adds noise if it is.

### D-4: ESI is isolated as provisional
**Rationale**: NDMC's ESI formula is unpublished (MC-2 D-4), and ERA5-Land `pev` has documented problems in arid areas.

**Impact**: ESI may run at weight 0 until NDMC answers. STEP_0301 already skips weight-0 inputs.

---

## 6. Type/Constant Mappings

| Param | Raw input (CDP-1) | Derived quantity | Units out |
|---|---|---|---|
| SPI | CHIRPS precip | SPI-3 z-score | dimensionless |
| SM | FLDAS SoilMoi 0–10/10–40/40–100 | weighted root-zone SM | m³/m³ |
| EVI2 | VIIRS `1 km monthly EVI2` | EVI2 (scale removed), QC-masked | dimensionless (−1…1) |
| ESI | ERA5(-Land) `e`, `pev` | ET/PET ratio | dimensionless |

---

## 7. Compatibility & Migration

### Backward Compatibility
- [ ] NDMC mode does not call this task.

### Seeder/CLI Compatibility
- [ ] New CLI: `derive_indices.py`.

---

## 8. Security Considerations

- [ ] Local files only; no network access in this task.

---

## 9. Testing Strategy

| Test Type | Coverage |
|---|---|
| Unit | SPI against a reference series. One CHIRPS pixel goes through both our `derive_spi` and the WMO-No.1090 / Guttman (1999) algorithm, and they must agree within 0.01. SPI of an all-zero-rain month is handled by the mixed term. SM weights sum to 1, and output = weights · layers. EVI2 fill and QC-masked pixels → nodata. The sensor offset of identical inputs is 0. ESI sign and units on a synthetic ERA5 field. |
| Integration | 24 months of real Eswatini raw data → derived files. Spot-check 3 pixels by hand in a notebook, attached to the PR. |

---

## 10. Open Questions

- [ ] **OQ-1 (NDMC Q1)**: The ESI formula and variables. Is the z-score capped at ±3? **— PENDING NDMC (Q1); working default: ESI = ET/PET ratio, z-score per calendar month, clipped at ±3σ, then Φ.**
- [x] **OQ-2**: What counts as a "significant" EVI2 sensor offset? Proposed: apply it where the mean offset is greater than 0.5 × the standard deviation of month-to-month EVI2 change. **— RESOLVED 2026-10-12: adopt the proposed rule.**
- [ ] **OQ-3 (NDMC Q3)**: NDMC's "modelled backups" for EVI2. Should our pre-2012 history be modelled too, or is 14 years acceptable? D-2 in MC-2 says 14 years is acceptable for now. **— PENDING NDMC (Q3); working default: 14-year EVI2 baseline, no pre-2012 modelled backfill.**
- [ ] **OQ-4 (NDMC Q5)**: CHIRPS v3 and the SPI calibration period. **— PENDING NDMC (Q5); working default: CHIRPS-2.0 with its existing calibration.**

---

## 11. References

- Parent design: [MC-2](../cdi-inhouse-percentiles.md) D-4, D-6, §4.1
- Method references: [ndmc-method-questions-references.md](../ndmc-method-questions-references.md) (Q1, Q3, Q4, Q5)
- Code: `cdi-scripts/libs/spi_calculations.py`, `STEP_0104_create_5km_soil_moisture_netcdf.py:110-122`
- WMO (2012), *SPI User Guide*, WMO-No. 1090; Guttman (1999), https://doi.org/10.1111/j.1752-1688.1999.tb03592.x; Jiang et al. (2008), https://doi.org/10.1016/j.rse.2008.06.006

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | | | |
| Tech Lead | | | |
| Product | | | |
