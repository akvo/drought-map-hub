# Global DIH — session handoff

**Purpose:** carry over the planning sessions of 2026-09-30 → 2026-10-12, which happened in the Eswatini repo (`akvo/eswatini-droughtmap-hub`), to the repo where the work is executed: **`akvo/drought-map-hub`**, the generic multi-country DIH.

**Start a new session in the `akvo/drought-map-hub` repo with:** *"Read `docs/global-dih/HANDOFF.md`, then `docs/global-dih/1-cdi-data-pipeline/README.md`."*

---

## 1. The question that started it

A colleague asked on Slack: *"What would need to change in the system to support other countries and regions?"*
- The only thing every country has in common is the **CDI output**.
- IKS and weather stations may not exist in other countries.
- Clients may bring their own data sources.

**Answer: yes, it is feasible.**
- The CDI publish/review/validate core is mostly country-agnostic already.
- The main blocker is **CDI input data**. NDMC publishes ready-made percentiles for **Southern Africa only**.

The short list sent to the colleague, in four groups:
1. **CDI pipeline:** compute the inputs ourselves.
2. **Pluggable modules:** weather, IKS, risk level and indicators become optional.
3. **Country config:** maintained by the team.
4. **Client data:** a table of admin unit × month × value, shown in Insights only.

---

## 2. Where the work happens (decided 2026-10-12)

- All execution happens in **`akvo/drought-map-hub`**, not in the Eswatini repos.
- Its `cdi/` currently holds the **old** raw-data pipeline (MODIS LST/NDVI). That pipeline is broken upstream:
  - NDMC retired LST/NDVI;
  - the GES DISC on-prem OPeNDAP server returns 410;
  - MODIS is at end of life.
- So the first task is **CDP-0**: port the current pipeline from `akvo/eswatini-droughtmap-hub-cdi` `main @ e3651e9` (NDMC ESI/EVI2/SPI/SM) into `drought-map-hub/cdi`, then rename LST/NDVI → ESI/EVI2 across the app, Rundeck and GeoNode.
- ✅ (2026-10-12) `drought-map-hub`'s uncommitted local work is handled: the per-instance files (`country.topojson`, `cdi/config/cdi_project_settings.json`) are now untracked and gitignored with `.example` templates, and the code fixes (`CDIMap.js` et al.) are committed on branch `chore/untrack-instance-config`.
- ⚠️ **Kenya is outside NDMC's Southern_Africa extent.** In NDMC mode a Kenya instance gets no CDI until in-house mode (CDP-1 → CDP-6) lands. See CDP-0 OQ-1.

---

## 3. Decisions (all confirmed by Iwan)

| Ref | Decision | Date |
|---|---|---|
| B-1 | Every country must be covered. The CDI pipeline is the first blocker. | 09-30 |
| B-2 | Client data is forced into one shape: a table per admin unit per month. | 09-30 |
| B-3 | Confidence **requires** weather stations. No stations means the review map shows progress only. | 09-30 |
| B-4 | Country content and config are owned by the team via config. There is no admin UI for it. | 09-30 |
| B-5 | This is future-proofing. No second country is committed yet. | 09-30 |
| B-6 | Client data appears in Insights only. It never feeds review or validation. | 09-30 |
| B-7 | IKS and risk level are also switchable modules. | 09-30 |
| MC-2 D-1 | **In-house first:** build with working defaults, self-validate against NDMC's published files, treat NDMC's reply as a sharpener (never a blocker). `inhouse` mode must run with zero NDMC files/replies. | 09-30, rev 10-06, **in-house-first 10-28** |
| MC-2 D-2 | Baseline per component: **40 years for SPI/ESI/SM, 14 years for EVI2** (VIIRS starts in 2012). Option 1 was chosen; MODIS stitching is deferred. | 09-30 |
| MC-2 D-7 | Full CDI where the data supports it. **SPI-only "rainfall drought index"** for atoll states (Marshall Islands). | 10-06 (proposed) |
| MC-1 D-1 | One instance per country, not multi-tenant. | 09-30 (proposed) |
| CDP-0 OQ-1 | No live non-Southern-Africa instance; drop and tag the legacy LST/NDVI pipeline. | 10-12 |
| CDP-0 OQ-2 | Extract the eswatini `v1_publication` geonode push endpoints into a new, optional `v1_geonode` app in the generic hub; enable the ported sync job. | 10-12 |
| CDP-0 OQ-3/4 | No wholesale app move: port backend APIs first, frontend iteratively. Keep both CDI repos. | 10-12 |
| MC-2 OQ-5 | One VM, one config per country (so prefix GeoNode categories per country). | 10-12 |
| MC-2 OQ-4 | Accept the ERA5-Land licence now. | 10-12 |
| MC-2 OQ-3 | Pass threshold: ≥80% units same D-class, none >1 class apart (TWG to confirm). | 10-12 |
| MC-2 OQ-1 | Iwan owns and sends the NDMC correspondence directly. | 10-12 |

---

## 4. Measured facts (do not re-research)

| Fact | When |
|---|---|
| NDMC `Regional_Percentiles/` lists only `Southern_Africa`. That folder now also holds `chirps_spi_1mn`, `era5_esi_3mn` and `ndvi_1mn`. | 09-30, 10-06 |
| NDMC backfilled: all four inputs start in 2012, and `evi2_1mn` has all 12 months. Jan/Jul/Aug were added on 11 Aug 2026, possibly from "modelled backups"; that is unconfirmed. | 10-06 |
| NDMC ranks against **40-year rolling histories** (NDMC mail, line 117). 2012 is only the export window. | 09-30 |
| NDMC's ESI max is exactly 99.865 = 100·Φ(3), and every value seen lies in 0.135–99.865. About 100k distinct values per map, which suggests Gaussian percentiles. SM and SPI reach exactly 0/100. *Inferred, not confirmed.* | 10-06 |
| STEP_0302 "pooled ranking" and the D0–D4 cut-offs (0.30/0.20/0.10/0.05/0.02) are **Akvo's own**, not NDMC's. | 09-30 |
| CHIRPS-2.0 monthly **COG** windowed read: Eswatini comes back as 44×44 cells with no full download. | 10-12 |
| FLDAS global through **Earthdata Cloud OPeNDAP**: a bbox subset is 45 KB per month. The on-prem `hydro1` server returns **410**. FLDAS has **no PET variable**, so ESI needs ERA5(-Land). | 09-30 |
| Earthdata login (`EARTHDATA_USERNAME/PASSWORD`, currently in the **eswatini hub `.env`**) works for LP DAAC and GES DISC. CDS works through the hub's `ECMWF_API_KEY`. The **ERA5-Land licence is not accepted yet.** | 09-30 |
| **Suomi-NPP (VNP13A3) delivery ends 1 Nov 2026.** The successors are VJ113A3 (NOAA-20, from 2018) and VJ213A3 (NOAA-21, from 2023). | 10-06 |
| Pacific: Marshall Islands atolls have CHIRPS data but **0 FLDAS land cells**. Fiji works on its main islands but **crosses 180°**. `config_reader`'s `range(w_lon, e_lon, 50)` returns an empty grid when `w_lon > e_lon`. | 10-06, 10-12 |
| Earth Engine is not available to DIH: no free tier for this use. | earlier |

### Data sources — URL recap

In-house pipeline inputs (full detail in [CDP-1](1-cdi-data-pipeline/CDP-1_raw-data-fetch.md) §1/§6/§8):

| CDI input | Provider · host | Access path | Auth | History |
|---|---|---|---|---|
| **SPI** (rainfall) | CHIRPS-2.0 · `data.chc.ucsb.edu` | `/products/CHIRPS-2.0/global_monthly/cogs/chirps-v2.0.YYYY.MM.cog` (windowed `/vsicurl/`) | none | 1981 → |
| **SM** (soil moisture) | FLDAS Noah · Earthdata Cloud OPeNDAP `opendap.earthdata.nasa.gov` | `/collections/C1563089663-GES_DISC/granules/FLDAS_NOAH01_C_GL_M.001:…` (DAP4 bbox) | Earthdata (`EARTHDATA_USERNAME/PASSWORD`) | 1982 → |
| **ESI** (evaporative stress) | ERA5-Land · CDS `cds.climate.copernicus.eu` | dataset `reanalysis-era5-land-monthly-means`, `area=[N,W,S,E]`; vars `total_evaporation`, `potential_evaporation` | `ECMWF_API_KEY` (cdsapi); **ERA5-Land licence must be accepted** | 1950 → |
| **EVI2** (vegetation) | VIIRS · LP DAAC `data.lpdaac.earthdatacloud.nasa.gov` (granules via `cmr.earthdata.nasa.gov`) | `VNP13A3.002` → `VJ113A3.002`; layer `1 km monthly EVI2` + reliability | Earthdata | 2012 → / 2018 → |
| **NDMC reference** (`ndmc` mode + CDP-5 validation) | NDMC · `droughtcenter.unl.edu` | `/Outgoing/Regional_Percentiles/Southern_Africa/` | none | 2012 → (Southern Africa only) |

Host allow-list (CDP-1 §8): `data.chc.ucsb.edu`, `opendap.earthdata.nasa.gov`, `data.lpdaac.earthdatacloud.nasa.gov`, `cmr.earthdata.nasa.gov`, `urs.earthdata.nasa.gov`, `cds.climate.copernicus.eu`.

---

## 5. NDMC thread status

- **Contacts:** the NDMC methodology contacts are held privately (not in this repo). The relationship runs through the Akvo leads.
- **Methodology email:** subject "CDI for countries beyond Southern Africa – questions on your methodology". **Both sent — methodology 2026-10-06, follow-up 2026-10-12.** NDMC replied on the Pacific/small-island question on 2026-10-28 (see MC-2 OQ-7); no reply yet on the method questions. Iwan owns and sends this correspondence directly.
- **Open method questions (each has a working default):**
  - ESI formula
  - Percentile method (Gaussian vs empirical) and the 40-year window
  - EVI2 history and the move to NOAA-20/21
  - FLDAS soil-moisture weights
  - CHIRPS version and SPI calibration
  - the example code they offered
  - suitability for small island states
- The verified references for these questions, and the likely questions back, are kept in an internal method-references note (not in this repo).
- **Resolved 2026-10-12:** the "new synthetic/emulated data source" Iwan mentioned is NDMC's Southern-Africa Regional_Percentiles (https://droughtcenter.unl.edu/Outgoing/Regional_Percentiles/Southern_Africa/) — the generation-2 input already used by the Eswatini CDI (`eswatini-droughtmap-hub-cdi`). It is not a new source and does not change the Q1/Q3 wording.

---

## 6. Two workstreams (this folder)

All planning groups under **two top-level plan tasks**:

### Workstream 1 — Plan tasks for the global CDI data pipeline
Make the CDI computable **in-house** for any country (independence from NDMC).
- **Design:** [`cdi-inhouse-percentiles.md`](1-cdi-data-pipeline/cdi-inhouse-percentiles.md) (MC-2) — pipeline generations, measured access, decisions D-1…D-7, Pacific check (§1.2b).
- **Sub-tasks:** [`1-cdi-data-pipeline/README.md`](1-cdi-data-pipeline/README.md) — **CDP-0 … CDP-6** (port → fetch → grid → derive → percentiles → self-validate → integrate).

### Workstream 2 — Plan tasks for porting V2 improvements to the generic repo
Bring the Eswatini hub v2 app features into the generic hub as **optional, country-agnostic modules** (backend-first, frontend iteratively — CDP-0 OQ-3).
- **Design:** [`multi-country-deployment.md`](2-v2-porting/multi-country-deployment.md) (MC-1) — optional modules (`DIH_MODULES`), `source/` as the country pack, weather-off → progress-only review map, the `v1_datasets` client table. Written against the Eswatini hub's code (file:line refs); re-map to `drought-map-hub/app` when executing.
- **Sub-tasks:** [`2-v2-porting/README.md`](2-v2-porting/README.md) — **VP-0 … VP-7** (v1_geonode → module system → weather-off UX → config flags → country pack → map framing → admin label → client data).

**CDP-0 is the hinge:** it ports the pipeline (WS-1) and bootstraps the first WS-2 backend module (`v1_geonode`).

---

## 7. Next steps

1. ✅ Done (2026-10-12): local work committed/ignored on branch `chore/untrack-instance-config`; CDP-0 OQ-1 answered — no live non-Southern-Africa instance.
2. Execute **CDP-0** on a new branch, e.g. `feature/port-ndmc-cdi-pipeline`. It includes creating the new optional `v1_geonode` app (CDP-0 OQ-2 / D-4).
3. Copy `EARTHDATA_USERNAME`, `EARTHDATA_PASSWORD` and `ECMWF_API_KEY` into `drought-map-hub/cdi/.env`, and **accept the ERA5-Land licence on CDS now** (MC-2 OQ-4).
4. ⏱️ **Early & time-sensitive (independent of CDP-0):** pin a checksummed NDMC reference snapshot — build/run `fetch_ndmc_reference.py` (CDP-5) to capture the Eswatini `Regional_Percentiles` with SHA256 + `Last-Modified`. NDMC already re-published files once (11 Aug 2026 backfill); pinning now protects the self-validation baseline before it changes again.
5. Start CDP-2 → CDP-1 (VNP13A3 history **before 1 Nov 2026**) → CDP-3 (SPI/SM/EVI2) → CDP-4 → CDP-5 **without waiting for NDMC** — CDP-5 self-validates against NDMC's published files; NDMC's reply only refines defaults.
6. ✅ Decided (2026-10-12, CDP-0 OQ-3/4): no wholesale v2-app move — port backend APIs first, frontend iteratively; keep both CDI repos.

---

## 8. Related repos and paths

| Repo | Role |
|---|---|
| `akvo/drought-map-hub` | **Target**: generic DIH (app + cdi + geonode + rundeck) |
| `akvo/eswatini-droughtmap-hub-cdi` | Source of the current pipeline (CDP-0); its `docs/` holds the NDMC mail thread |
| `akvo/eswatini-droughtmap-hub` | The Eswatini hub v2, where these docs were written and where the MC-1 code refs point |
