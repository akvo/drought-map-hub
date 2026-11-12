"""Shared CSV import for client datasets (DIH-7).

Used by both the management command (CLI) and the Django admin import view, so
validation + upsert live in one place. Rows upsert on
(administration, dataset, period); an unknown ``administration_id`` is rejected
(never created); a blank / ``null`` value is stored as NULL (missing) — never
0, because 0 is a real reading.
"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import List

from api.v1.v1_datasets.models import AdminDatasetValue
from api.v1.v1_publication.models import Administration

REQUIRED_COLUMNS = ("administration_id", "period", "value")
_MISSING = {"", "null", "na", "n/a", "nan", "none"}


def parse_period(raw: str) -> date:
    """`YYYY-MM` -> first day of that month."""
    return datetime.strptime(raw.strip(), "%Y-%m").date().replace(day=1)


def parse_value(raw):
    """Blank / null markers -> None (missing). Otherwise float. null != 0."""
    if raw is None or raw.strip().lower() in _MISSING:
        return None
    return float(raw)


def has_required_columns(fieldnames) -> bool:
    return set(REQUIRED_COLUMNS).issubset(set(fieldnames or []))


@dataclass
class ImportResult:
    inserted: int = 0
    updated: int = 0
    rejected: int = 0
    errors: List[str] = field(default_factory=list)

    def summary(self) -> str:
        ins, upd, rej = self.inserted, self.updated, self.rejected
        return f"inserted={ins} updated={upd} rejected={rej}"


def import_rows(key: str, reader) -> ImportResult:
    """Upsert the rows of a ``csv.DictReader`` for one dataset key."""
    result = ImportResult()
    valid_ids = set(Administration.objects.values_list("id", flat=True))
    for line_no, row in enumerate(reader, start=2):
        try:
            adm_id = int(row["administration_id"])
            period = parse_period(row["period"])
            value = parse_value(row["value"])
        except (ValueError, KeyError, TypeError) as e:
            result.rejected += 1
            result.errors.append(f"row {line_no}: {e}")
            continue
        if adm_id not in valid_ids:
            result.rejected += 1
            msg = f"row {line_no}: unknown administration_id {adm_id}"
            result.errors.append(msg)
            continue
        _, created = AdminDatasetValue.objects.update_or_create(
            administration_id=adm_id,
            dataset=key,
            period=period,
            defaults={"value": value},
        )
        if created:
            result.inserted += 1
        else:
            result.updated += 1
    return result
