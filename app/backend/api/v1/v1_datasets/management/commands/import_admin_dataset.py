"""Team-run import of a client admin-level dataset (DIH-7, B-4).

    python manage.py import_admin_dataset <key> file.csv

CSV columns: ``administration_id,period,value`` (period ``YYYY-MM``). Shares
its validation + upsert with the Django admin import view (``importer.py``).
Fails loudly on a missing file or bad header.
"""

import csv

from django.core.management.base import BaseCommand, CommandError

from api.v1.v1_datasets.importer import has_required_columns, import_rows


class Command(BaseCommand):
    help = "Import a client admin-level dataset (admin x month x value)."

    def add_arguments(self, parser) -> None:
        parser.add_argument("key", help="Dataset key (slug)")
        parser.add_argument("csv_file", help="CSV file to import")

    def handle(self, *args, **options) -> None:
        key: str = options["key"]
        path: str = options["csv_file"]

        try:
            handle = open(path, newline="", encoding="utf-8")
        except FileNotFoundError:
            raise CommandError(f"File not found: {path}")

        with handle:
            reader = csv.DictReader(handle)
            if not has_required_columns(reader.fieldnames):
                raise CommandError(
                    "CSV header must have columns: "
                    "administration_id, period, value "
                    f"(got: {reader.fieldnames})"
                )
            result = import_rows(key, reader)

        self.stdout.write(self.style.SUCCESS(f"{key}: {result.summary()}"))
