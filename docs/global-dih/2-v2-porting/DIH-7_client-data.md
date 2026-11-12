# Feature Design Document

## Feature: Client data — `v1_datasets` (admin × month × value)

**Task ID**: DIH-7
**Author**: Iwan Firmawan (with Claude)
**Date**: 2026-10-30
**Status**: Phase 8a done (backend + admin/CLI import); Phase 8b deferred
(no Insights host in this repo yet — lands with DIH-10)
**Effort**: ~10h total (incl. agentic coding) → 2 phases ≤8h each (see Phases): 8a ~6h, 8b ~4h.
**Depends on**: [DIH-2](DIH-2_module-system.md); dataset metadata from [DIH-4](DIH-4_country-pack.md) (`country.json → datasets`)

> Eswatini-hub file:line refs; re-map to `drought-map-hub/app` when executing.

---

## 1. Context

A client may bring its own admin-level data. It is forced into one shape — a value per admin unit per month (MC-1 B-2) — and shown **only in Insights**, never feeding review or validation (B-6).

## 2. Scope

A new optional `v1_datasets` app: model, team-run import, read-only API, one generic Insights tab. No link to `Publication`.

## 3. Approach + files

**Model** (long format on purpose — `v1_indicators` is a fixed-column wide table and can't hold per-client columns):

```python
class AdminDatasetValue(models.Model):
    administration = models.ForeignKey(Administration, on_delete=models.CASCADE)
    dataset = models.SlugField(max_length=50)   # key declared in country.json → datasets
    period = models.DateField()                 # first day of the month
    value = models.FloatField(null=True)        # null = reported missing, never 0
    class Meta:
        db_table = "admin_dataset_values"
        constraints = [models.UniqueConstraint(
            fields=["administration", "dataset", "period"], name="uniq_admin_dataset_period")]
```

Label/unit/source/description live in `country.json` (DIH-4), not per row.

**Import** (team-run, B-4) — two paths sharing one `importer.py` (validation + upsert):
- **Django admin** (as built, #—): a staff-gated CSV import on the `AdminDatasetValue` changelist (download a template, fill it, upload), mirroring the Eswatini weather admin (`v1_weather/admin.py`). This is the primary UX for bulk-importing additional (non-satellite) data.
- **CLI**: `python manage.py import_admin_dataset <key> file.csv` (cols `administration_id,period,value`, period `YYYY-MM`), for automation.

Both: idempotent upsert on (administration, dataset, period); reject (never create) an unknown `administration_id`; blank/`null` value → NULL (missing, never 0); report inserted/updated/rejected. No **public** upload endpoint — the admin import is staff-only inside `/admin`.

> **Supersedes the original "no file parsing in the web process" AC:** the prior-art weather hub parses the upload in a staff-gated admin view, so this does too. The constraint is narrowed to "no *public* upload endpoint", not "no web parsing".

**API** (read-only, public like the rest of Insights): `GET /api/v1/datasets/{key}?period=YYYY-MM` and `GET /api/v1/datasets/{key}/periods`. Response follows the house mock contract (`key`, `label`, `value`, `data`, `meta`):

```json
{"meta":{"key":"ndvi_anomaly","label":"NDVI anomaly","unit":"%","period":"2026-08"},
 "data":[{"administration_id":12,"value":-14.2},{"administration_id":13,"value":null}]}
```

**Frontend**: one generic "Other data" Insights tab lists `datasets` from config, renders a choropleth + table per key/month. Gated by the `datasets` module flag (DIH-3).

## 4. Decisions (MC-1 Decision Log)

- **D-5**: client data is a long table in its own optional app (B-2 shape; B-6 keeps it out of review/validation → no `Publication` link).

## Implementation steps

**Phase 7a — backend:**
1. `AdminDatasetValue` model + migration (unique `administration`+`dataset`+`period`; `value` nullable). → verify: `migrate` forward **and** back.
2. `import_admin_dataset <key> file.csv` command — idempotent upsert, reject unknown `administration_id`/undeclared `dataset` key, `null` ≠ 0. → verify: unit test upsert + reject + null handling.
3. Read-only API `GET /datasets/{key}` + `/datasets/{key}/periods`, gated by the `datasets` module (DIH-2). → verify: returns the house-contract shape; `datasets` off → routes 404.

**Phase 7b — frontend:**
4. Generic "Other data" Insights tab (choropleth + table per key/month), gated by `datasets` (DIH-3). → verify: renders from `config.datasets`; absent when `datasets` off.

## User acceptance criteria

- As an **operator**, I import my country's own admin-level dataset and it appears to viewers as an "Other data" Insights tab (a map + table per month).
- As a **reviewer**, this client data never changes anything in the review/validation workflow — it is display-only.

## 5. Technical acceptance criteria

- [ ] An imported admin-level dataset appears as an Insights tab — a map + a table per month.
- [ ] Import is idempotent; unknown `administration_id`/dataset key is rejected, not created; null = missing (never 0).
- [x] The datasets **read** API is read-only + public; no *public* upload endpoint (bulk import is the staff-gated admin view or the CLI).
- [ ] With the `datasets` module off, the tab is absent.

**Verify by (goal-driven):** unit test `import_admin_dataset` upsert + reject + null handling; API test returns the house-contract shape; a test with `datasets` off asserts the tab/routes are absent.

## Phases (≤8h each)

| Phase | Effort | Scope | Technical acceptance |
|---|---|---|---|
| **8a** backend | ~6h | `AdminDatasetValue` model + migration, shared `importer.py`, **admin CSV import** + `import_admin_dataset` CLI, read-only API (`/datasets/{key}`, `/periods`), gated by `datasets` | ✅ Done — migration fwd/back; import idempotent + rejects unknown id + null≠0; API returns the house-contract shape; module off → routes 404 (17 tests) |
| **8b** frontend | ~4h | Generic "Other data" Insights tab (choropleth + table per key/month), gated | ⏸ Deferred — no Insights host in this repo yet; lands with DIH-10 |

## 6. Dependencies / hand-offs

- Needs DIH-2 (gating) + DIH-4 (dataset metadata in `country.json`). Insights tab rendering is part of DIH-3/DIH-10.
- Security: team-run command only; validates ids/keys against the DB + `country.json`; help text warns against importing sensitive data.

## 7. References

- [MC-1](README.md) §3, §4.2, §4.4, §5 D-5, §8, B-2/B-6.
