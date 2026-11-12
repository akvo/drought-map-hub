"""Client-data admin with a CSV bulk-import path (DIH-7).

Mirrors the Eswatini weather admin import (download a template, fill it,
upload). Staff-only (inside ``/admin``), so it is still a team-run action —
not a public upload endpoint. Import validation + upsert are shared with the
management command (``importer.py``).
"""

import csv
import io

from django.contrib import admin, messages
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import path

from api.v1.v1_datasets.importer import (
    REQUIRED_COLUMNS,
    has_required_columns,
    import_rows,
)
from api.v1.v1_datasets.models import AdminDatasetValue

TEMPLATE_EXAMPLE_ROWS = [
    [1, "2026-08", "-14.2"],
    [2, "2026-08", "3.1"],
    [3, "2026-08", ""],
]


@admin.register(AdminDatasetValue)
class AdminDatasetValueAdmin(admin.ModelAdmin):
    # change_list_template is found automatically at the model's default path
    # (admin/v1_datasets/admindatasetvalue/change_list.html).
    list_display = ("dataset", "period", "administration", "value")
    list_filter = ("dataset", "period")
    search_fields = ("dataset", "administration__name")
    date_hierarchy = "period"
    raw_id_fields = ("administration",)

    def get_urls(self):
        return [
            path(
                "csv-template/",
                self.admin_site.admin_view(self.csv_template_view),
                name="admin_dataset_csv_template",
            ),
            path(
                "import-csv/",
                self.admin_site.admin_view(self.import_csv_view),
                name="admin_dataset_import_csv",
            ),
        ] + super().get_urls()

    def csv_template_view(self, request):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            "attachment; filename=admin_dataset_template.csv"
        )
        writer = csv.writer(response)
        writer.writerow(REQUIRED_COLUMNS)
        writer.writerows(TEMPLATE_EXAMPLE_ROWS)
        return response

    def import_csv_view(self, request):
        if request.method != "POST" or not request.FILES.get("csv_file"):
            return render(
                request,
                "admin/v1_datasets/import_csv.html",
                {**self.admin_site.each_context(request)},
            )

        key = (request.POST.get("dataset") or "").strip()
        if not key:
            msg = "Dataset key is required."
            self.message_user(request, msg, level=messages.ERROR)
            return redirect("..")

        decoded = request.FILES["csv_file"].read().decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(decoded))
        if not has_required_columns(reader.fieldnames):
            self.message_user(
                request,
                "CSV header must have: administration_id, period, value.",
                level=messages.ERROR,
            )
            return redirect("..")

        result = import_rows(key, reader)
        level = messages.WARNING if result.errors else messages.SUCCESS
        summary = f"{key}: {result.summary()}"
        if result.errors:
            summary += " — " + "; ".join(result.errors[:10])
        self.message_user(request, summary, level=level)
        return redirect("..")
