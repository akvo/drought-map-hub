# NDMC method email — reference pack (Q1–Q6)

Prep notes for the methodology email to NDMC (Jeff Wisner / Calvin Poulsen), part of [`cdi-inhouse-percentiles.md`](cdi-inhouse-percentiles.md) (MC-2, D-1).

The list is limited to sources that were checked on **2026-10-06**:
- every DOI resolved in Crossref;
- every URL returned HTTP 200;
- every NDMC raster number was re-measured from NDMC's own files.

Each question has three parts: **what we cite**, **our own evidence**, and **what NDMC might ask back**.

The NDMC email thread is in `eswatini-droughtmap-hub-cdi/docs/lst-ndvi-retirement-mail.md`. Line numbers below refer to that file.

---

## Corrections found while verifying (fix the email before sending)

| Claim in the draft email | Status on 2026-10-06 |
|---|---|
| Q3: "Is there a reason January, July and August are not published?" | ❌ **Outdated, remove it.** `evi2_1mn` now has all 12 months for every year 2012–2025, plus 2026 up to August. The files were re-published on 11 Aug 2026 (HTTP `Last-Modified`). |
| SPI "only from 2023" (our earlier docs) | ❌ **Outdated.** `chirps_spi_3mn` now has 2012–2026. NDMC backfilled it, which is what REQ-4 asked for. Thank them for it. |

---

## Q1 — ESI formula and ERA5 variables

**Cite**
- Anderson, M.C. et al. (2011). *Evaluation of drought indices based on thermal remote sensing of evapotranspiration over the continental United States.* Journal of Climate. https://doi.org/10.1175/2010JCLI3812.1. This is the origin of the ESI: a standardised anomaly of actual/potential ET.
- NOAA CPC, *Evaporative Stress Index* product page: https://www.cpc.ncep.noaa.gov/products/international/drought/ESI.shtml
- Muñoz-Sabater, J. et al. (2021). *ERA5-Land: a state-of-the-art global reanalysis dataset for land applications.* ESSD. https://doi.org/10.5194/essd-13-4349-2021
- CDS dataset page, ERA5-Land monthly means: https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land-monthly-means
- ECMWF, *ERA5-Land: data documentation* (known issues): https://confluence.ecmwf.int/display/CKB/ERA5-Land%3A+data+documentation
  - Since Nov 2021, `pev` is open-water (pan) evaporation and "can give unrealistic results in arid conditions".
  - The evabs, evaow and evavt values are swapped with each other.
- ECMWF forum, problems with the ERA5 potential evapotranspiration product: https://forum.ecmwf.int/t/confluence-page-on-the-problems-of-the-potential-evapotranspiration-product-in-era5/2491

**Our evidence**
- NDMC mail, line 99: "ESI from both FLDAS and ERA". Line 442: "The ESI … is the replacement for LST."
- NDMC rasters (`Regional_Percentiles/Southern_Africa/era5_esi_1mn/`), re-measured on 2026-10-06:

  | File | min | max |
  |---|---|---|
  | `era5_esi_1mn_2015-01-01.tif` | 0.1682 | 98.0205 |
  | `era5_esi_1mn_2020-06-01.tif` | 1.7816 | 93.6307 |
  | `era5_esi_1mn_2025-09-01.tif` | 0.8835 | **99.8650** |

  - 100·Φ(3) = 99.865 and 100·Φ(−3) = 0.135. No ESI value seen falls outside 0.135–99.865, and the 2025-09 maximum sits exactly on the cap.
  - SPI, SM and EVI2 do reach 0 or 100. That is why we ask whether ESI's z-score is capped at ±3.
- FLDAS global has `Evap_tavg` but **no `PotEvap_tavg`**. We listed its variables through Earthdata Cloud OPeNDAP on 2026-09-30. So an ET/PET ESI from FLDAS needs a PET source from somewhere else.

**NDMC may ask back**
- *"Why not just use our ESI?"* We need countries outside the Southern Africa extent, and an in-house method that keeps working if a feed stops (as the 2026 LST feed did).
- *"ERA5 or ERA5-Land?"* We have no preference yet. We will follow theirs, which is the point of the question.

---

## Q2 — Gaussian vs empirical percentiles; the 40-year window

**Cite**
- NDMC mail, line 117: "We now use rolling windows of 40-year histories for each index". Line 121: "The rankings are now true percentiles; the older method had to use plain rankings due to the shorter histories of NDVI/LST."
- NDMC Drought Blends metadata, which describes "Gaussian percentiles associated with a standardized distribution": https://ndmcblends.unl.edu/Metadata.aspx. This is the US product; whether Southern Africa uses the same method is exactly what we ask.
- NDMC old CDI toolkit, `scripts_update.zip`: https://droughtcenter.unl.edu/Outgoing/CDI/software/scripts/scripts_update.zip. In `libs/statistics_operations.py`, the old method is an empirical rank per pixel and calendar month.
- MENA CDI paper, an example of NDMC-style CDI in another region (it uses 20/10/2 class cutoffs): https://pmc.ncbi.nlm.nih.gov/articles/PMC10914844/

**Our evidence**
- Each NDMC map has about 98k–108k distinct values out of 117,697 valid pixels, re-measured on 2026-10-06. A per-pixel empirical rank over 15 years could give at most 16 distinct levels per pixel, so the maps look parametric, or ranked against a much longer history.
- SM and SPI reach exactly 0 and 100 (`noah_soilm_1mn_2025-09-01`, `chirps_spi_3mn_2025-09-01`). A pure Φ(z) would never return exactly 0 or 100. So the method may **differ per index**; ask about each one.

**NDMC may ask back**
- *"What do you do with the CDI after the weighted sum?"* Our STEP_0302 "pooled" re-rank is **our own step**, not theirs: `eswatini-droughtmap-hub-cdi/src/data-processing/cdi-scripts/STEP_0302_rank_cdi_pooled.py`. The D0–D4 cutoffs (30/20/10/5/2) are also the hub's own, following the US Drought Monitor.

---

## Q3 — EVI2 sensor, 40-year history, Suomi-NPP end

**Cite**
- Jiang, Z. et al. (2008). *Development of a two-band enhanced vegetation index without a blue band.* Remote Sensing of Environment. https://doi.org/10.1016/j.rse.2008.06.006. This is the definition of EVI2.
- VNP13A3 file specification (layer `1 km monthly EVI2`): https://ladsweb.modaps.eosdis.nasa.gov/filespec/VIIRS/1/VNP13A3
- LP DAAC catalogue, VNP13A3 v002 (scale ×10000, fill −15000): https://www.earthdata.nasa.gov/data/catalog/lpcloud-vnp13a3-002
- NASA notice, *Suomi NPP data product delivery to cease November 1, 2026*: https://www.earthdata.nasa.gov/data/alerts-outages/suomi-npp-data-product-delivery-cease-november-1-2026. It names VJ213A3 (NOAA-21) and VJ113A3 (NOAA-20) as successors.
- NDMC mail, line 89: "we have already transitioned other projects to VIIRS data". Line 101: "NDVI and EVI2 with modeled backups".

**Our evidence**
- NASA CMR catalogue start dates: VNP13A3 2012-01, VJ113A3 2018-01, VJ213A3 2023-02, MOD13A3 2000-02.
- So with VIIRS alone there is no 40-year EVI2. That is why we ask about the "modelled backups".

**NDMC may ask back**
- *"Which baseline will you use for EVI2?"* Our decision (MC-2 D-2) is 40 years for SPI/ESI/SM and the 14 years available for EVI2. We are open to their approach.

---

## Q4 — Soil moisture: FLDAS Noah 0–100 cm, 0.1/0.3/0.6

**Cite**
- McNally, A. et al. (2017). *A land data assimilation system for sub-Saharan Africa food and water security applications.* Scientific Data. https://doi.org/10.1038/sdata.2017.12. This is the FLDAS reference.
- GES DISC collection page, FLDAS_NOAH01_C_GL_M v001: https://disc.gsfc.nasa.gov/datacollection/FLDAS_NOAH01_C_GL_M_001.html
- NDMC mail, line 103: "100cm Soil Moisture from both FLDAS and ERA".
- NDMC old toolkit (`scripts_update.zip` above), `STEP_0104`, `RootZone2`: 0.1·(0–10 cm) + 0.3·(10–40 cm) + 0.6·(40–100 cm). Our copy is `eswatini-droughtmap-hub-cdi/src/data-processing/cdi-scripts/STEP_0104_create_5km_soil_moisture_netcdf.py`, lines 118–120.

**Our evidence**
- Earthdata Cloud OPeNDAP returned the four FLDAS layers `SoilMoi00_10cm`, `10_40`, `40_100` and `100_200_tavg`, with a bbox subset of 45 KB per month (2026-09-30).
- GES DISC's old on-prem OPeNDAP (`hydro1.gesdisc.eosdis.nasa.gov/opendap`) now answers **410 Service Retired**.

**NDMC may ask back**
- *"FLDAS or ERA for SM?"* We prefer FLDAS, to stay close to their `noah_soilm_1mn` naming, and will follow their advice.

---

## Q5 — SPI: CHIRPS v3, gamma calibration, SPI → percentile

**Cite**
- McKee, T.B., Doesken, N.J. & Kleist, J. (1993). *The relationship of drought frequency and duration to time scales.* 8th Conference on Applied Climatology, Anaheim, CA, 17–22 Jan 1993. This is the original SPI paper. It has no DOI and is a conference preprint.
- WMO (2012). *Standardized Precipitation Index User Guide* (WMO-No. 1090), by M. Svoboda, M. Hayes and D. Wood: https://www.droughtmanagement.info/literature/WMO_standardized_precipitation_index_user_guide_en_2012.pdf. Svoboda and Hayes are NDMC, so this is NDMC's own guidance.
- Guttman, N.B. (1999). *Accepting the Standardized Precipitation Index: a calculation algorithm.* JAWRA. https://doi.org/10.1111/j.1752-1688.1999.tb03592.x. It covers the gamma fit and the calibration-period sensitivity.
- Funk, C. et al. (2015). *The climate hazards infrared precipitation with stations — a new environmental record for monitoring extremes.* Scientific Data. https://doi.org/10.1038/sdata.2015.66 (CHIRPS v2).
- NCAR Climate Data Guide, CHIRPS v3 (it replaced v2 on 6 Dec 2024): https://climatedataguide.ucar.edu/climate-data/chirps-climate-hazards-infrared-precipitation-station-data-version-3
- NDMC mail, line 97: "SPI and SPEI from both CHIRPS3 and ERA".

**Our evidence**
- The old toolkit's `libs/spi_calculations.py` (in `scripts_update.zip`, and in our repo) uses the Thom gamma estimator with a zero-rain mixed term, then SPI = Φ⁻¹(H), then an **empirical** rank.
- The hub still uses CHIRPS-2.0 for its own weather features. If we switch the CDI's SPI to v3, the 30-year normals must move too (hub memory note).

**NDMC may ask back**
- *"Which accumulation period?"* 3 months, matching `chirps_spi_3mn`.

---

## Q6 — The example code offered in April

**Cite**
- NDMC mail, lines 105–111, Option 2: "I would provide examples and code snippets of the new download processes".
- Akvo's reply, line 171: "Share example files and code snippets for the new download process, as you mentioned." **We already asked once.** Jeff's 3 June reply (line 436 onward) delivered the regional percentiles, but no code.

**NDMC may ask back**
- *"Didn't you choose Option 1?"* Yes, for Eswatini, and it works well. Option 2-style code is now needed for countries outside the Southern Africa export.

---

## Reproduce our NDMC raster numbers

```bash
B=https://droughtcenter.unl.edu/Outgoing/Regional_Percentiles/Southern_Africa
curl -sO $B/era5_esi_1mn/2025/era5_esi_1mn_2025-09-01.tif
python3 -c "import rasterio,numpy as n;a=rasterio.open('era5_esi_1mn_2025-09-01.tif').read(1);v=a[a>=0];print(v.min(),v.max(),n.unique(v).size)"
# expected: 0.8835 99.865 108555   (nodata = -1.0)
```
