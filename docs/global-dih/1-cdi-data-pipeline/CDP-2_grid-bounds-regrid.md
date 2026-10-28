# Feature Design Document

## Feature: Country grid, bounds snapping, antimeridian support, and regridding to 0.05°

**Task ID**: CDP-2 (sub-task of [MC-2](cdi-inhouse-percentiles.md))
**Author**: Iwan Firmawan (with Claude)
**Date**: 2026-10-12
**Status**: Draft
**Repo affected**: `drought-map-hub` → `cdi/` (after the [CDP-0](CDP-0_port-eswatini-pipeline.md) port; file/line refs to existing code point at the `eswatini-droughtmap-hub-cdi` source until then)

---

## 1. Context & Problem Statement

```
Currently:
- libs/config_reader.py builds the grid from config bounds in 0.05° steps:
      for lon in range(w_lon, e_lon, 50):   # thousandths of a degree
  then appends the end bound.
  - If the bounds are not on 0.05° cell centres, the last spacing comes out
    irregular, and nothing catches it.
  - If w_lon > e_lon (a country crossing 180°, e.g. Fiji: 177°E → 178°W), the
    range is EMPTY. The grid silently becomes a single column.
- STEP_0100 does not resample. It reads a fixed window starting at the NW cell,
  which only works because NDMC pixel centres are exactly x.x25 / x.x75.
- Raw sources come on other grids: FLDAS and ERA5-Land at 0.1°, VIIRS at 1 km
  sinusoidal, CHIRPS at 0.05° (same lattice).
- The 0.05° step is hard-coded in three places: config_reader.py,
  netcdf_functions.initialize_dataset (DX/DY), and STEP_0303:124 (res=0.05).

Goal:
- Any country's boundary produces a valid 0.05° grid snapped to cell centres,
  including countries that cross the antimeridian.
- Every raw source is regridded onto that grid, so all four inputs share one
  lattice before percentiles (CDP-4) and the weighted sum (STEP_0301).
```

---

## 2. Requirements

### User Acceptance Criteria
- [ ] An operator gives a country's GeoJSON boundary and gets the exact `bounds` block to paste into `cdi_project_settings.conf`.
- [ ] Fiji's boundary produces a grid that spans 177°E → 178°W without a gap or an empty axis.

### Technical Acceptance Criteria
- [ ] `snap_bounds(geojson)` returns bounds snapped **outward** to 0.05° cell centres (x.x25 / x.x75). Ported from the generic hub, `v1_setup/views.py:294-329`.
- [ ] `config_reader` builds the grid with integer cell indices, not float stepping, so spacing is exactly 0.05° and the last cell is never irregular.
- [ ] Antimeridian: when `w_lon > e_lon`, longitudes run on a **0–360° axis** internally (177.025 … 181.975). `split_bounds()` returns the two −180/180 windows that sources need.
- [ ] Regridding:
  - 0.1° sources (FLDAS, ERA5-Land) use **bilinear** interpolation onto 0.05°. This is the same as `NetCDFSubGrid(interpolate=True)` in the old STEP_0104.
  - 1 km VIIRS uses an **area-weighted mean**, counting only valid (QC-passed) pixels.
  - CHIRPS uses an identity copy (same lattice), with an assertion check.
- [ ] Ocean and nodata stay −9999 through the regrid. A target cell becomes nodata if fewer than 50% of its source area is valid.
- [ ] The 0.05° step is defined once (`GRID_STEP` in `config_reader`). The other two copies read it.

---

## 3. Data Model Changes

### Config (`cdi_project_settings.conf`): unchanged keys, new meaning documented

```json
"bounds": { "n_lat": -25.675, "s_lat": -27.825, "w_lon": 30.675, "e_lon": 32.825 }
// w_lon > e_lon now means "crosses the antimeridian", e.g. Fiji:
// { "n_lat": -12.425, "s_lat": -21.075, "w_lon": 176.825, "e_lon": -178.175 }
```

### New working files

```
working_data/regrid/{PARAM}/{param}_{region}_{YYYYMM}.nc   # 0.05° config grid, −9999 nodata
```

### Migration Strategy

```
- Eswatini bounds are already on cell centres, so the integer-index grid is
  identical (44 × 44).
- A regression test pins the Eswatini lat/lon arrays to today's values.
```

---

## 4. API Contract

```python
# libs/grid.py (new)
GRID_STEP = 0.05

def snap_bounds(geojson_path: Path) -> dict: ...            # → {"n_lat", "s_lat", "w_lon", "e_lon"}
def grid_axes(bounds: dict) -> tuple[np.ndarray, np.ndarray]: ...   # lats (N→S), lons (0–360 if crossing)
def split_bounds(bounds: dict) -> list[dict]: ...           # 1 or 2 boxes in −180/180, for providers
def regrid(src: Path, method: Literal["bilinear", "area_mean", "identity"], bounds: dict) -> np.ndarray: ...
```

```bash
python cdi/src/cdi-scripts/snap_bounds.py path/to/country.geojson
# prints the bounds block for cdi_project_settings.conf
```

---

## 5. Decision Log

### D-1: Keep the 0.05° grid
**Rationale**:
- STEP_0301 → 0303, the GeoNode upload and the hub's per-admin extraction all assume it.
- It matches CHIRPS and NDMC's "calibrated to 5 km".

**Impact**: MC-2 D-5 is unchanged.

### D-2: 0–360° longitudes internally for antimeridian countries
**Options**:
1. Two separate grids, joined at export.
2. One continuous 0–360° axis.

**Decision**: 2.

**Rationale**:
- One array keeps STEP_0301's per-cell maths untouched.
- Only the source reads (CDP-1) and the GeoTIFF export (CDP-6) need to know about the wrap.

**Impact**: STEP_0303 must write the GeoTIFF with an origin above 180°, or split it. This is checked against GeoNode in CDP-6.

### D-3: Area-weighted mean for VIIRS, bilinear for 0.1° models
**Rationale**:
- Downscaling 1 km → 5 km is aggregation, so averaging the valid pixels is right.
- Upscaling 0.1° → 0.05° is interpolation, as the NDMC toolkit already did in STEP_0104.

---

## 6. Type/Constant Mappings

| Source | Native grid | Method onto 0.05° |
|---|---|---|
| CHIRPS-2.0 | 0.05° (same lattice) | identity, with an assert on cell centres |
| FLDAS | 0.1° | bilinear |
| ERA5-Land | 0.1° | bilinear |
| VIIRS VNP13A3 / VJ113A3 | 1 km sinusoidal | reproject + area-weighted mean of QC-valid pixels |

---

## 7. Compatibility & Migration

### Backward Compatibility
- [ ] Eswatini's grid is byte-identical. A regression test checks the 44 lats and 44 lons.
- [ ] NDMC mode's STEP_0100 window read is unchanged for non-crossing bounds.

### Seeder/CLI Compatibility
- [ ] New CLI: `snap_bounds.py`.

---

## 8. Security Considerations

- [ ] `snap_bounds` reads a local GeoJSON only. Nothing is fetched from the network.

---

## 9. Testing Strategy

| Test Type | Coverage |
|---|---|
| Unit | `snap_bounds` snaps outward; integer-index axes give exactly 0.05° spacing; the Eswatini axes are pinned; Fiji axes are continuous across 180°; `split_bounds` returns 2 boxes for Fiji and 1 for Eswatini. Regrid: a constant field stays constant; a known linear field is reproduced by bilinear; area mean ignores QC-masked pixels; the <50%-valid cell becomes −9999. |
| Integration | One real FLDAS month (CDP-1 output) regridded over Eswatini: no NaN leakage, and land/ocean cells are where CHIRPS has them. |

---

## 10. Open Questions

- [ ] **OQ-1**: Does GeoNode accept a GeoTIFF whose x-origin is above 180°, or must the Fiji export be split? To check in CDP-6. **— DEFERRED to CDP-6 (needs a GeoNode test); working default: assume the Fiji/antimeridian export must be split.**
- [x] **OQ-2**: Small islands. A 0.05° cell (~30 km²) is larger than most atolls, and FLDAS/ERA5-Land have no land cells there (MC-2 §1.2b). This task only guarantees the grid; whether a CDI is meaningful there is MC-2 D-7. **— RESOLVED 2026-10-12: scope is grid-only; CDI fitness for small islands is covered by MC-2 D-7 (SPI-only profile).**

---

## 11. References

- Parent design: [MC-2](cdi-inhouse-percentiles.md) D-5, D-7, §1.2b
- Code: `cdi-scripts/libs/config_reader.py` (grid builder), `STEP_0100_ingest_ndmc_geotiffs.py:95-118` (window read), `libs/netcdf_functions.py` (`initialize_dataset`), `STEP_0303` (`res=0.05`)
- Prior art: `akvo/drought-map-hub` `app/backend/api/v1/v1_setup/views.py:294-329` (bbox snapping)

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | | | |
| Tech Lead | | | |
| Product | | | |
