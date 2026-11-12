import tempfile
from datetime import date

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from api.v1.v1_datasets.models import AdminDatasetValue
from api.v1.v1_publication.models import Administration


def _csv(rows: str) -> str:
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
    f.write("administration_id,period,value\n")
    f.write(rows)
    f.close()
    return f.name


class ImportAdminDatasetTest(TestCase):
    def setUp(self):
        self.a1 = Administration.objects.create(name="A1")
        self.a2 = Administration.objects.create(name="A2")

    def test_upsert_is_idempotent(self):
        path = _csv(f"{self.a1.id},2026-08,-14.2\n{self.a2.id},2026-08,3.1\n")
        call_command("import_admin_dataset", "ndvi_anomaly", path)
        self.assertEqual(AdminDatasetValue.objects.count(), 2)

        # re-import with a changed value -> update, not duplicate
        path2 = _csv(f"{self.a1.id},2026-08,99.9\n")
        call_command("import_admin_dataset", "ndvi_anomaly", path2)
        self.assertEqual(AdminDatasetValue.objects.count(), 2)
        row = AdminDatasetValue.objects.get(
            administration=self.a1,
            dataset="ndvi_anomaly",
            period=date(2026, 8, 1),
        )
        self.assertEqual(row.value, 99.9)

    def test_unknown_administration_id_rejected(self):
        path = _csv(f"999999,2026-08,1.0\n{self.a1.id},2026-08,2.0\n")
        call_command("import_admin_dataset", "ndvi_anomaly", path)
        # only the valid row is created; the unknown id is not
        self.assertEqual(AdminDatasetValue.objects.count(), 1)
        self.assertFalse(
            AdminDatasetValue.objects.filter(administration_id=999999).exists()
        )

    def test_blank_value_is_null_not_zero(self):
        path = _csv(f"{self.a1.id},2026-08,\n{self.a2.id},2026-08,null\n")
        call_command("import_admin_dataset", "ndvi_anomaly", path)
        for adm in (self.a1, self.a2):
            row = AdminDatasetValue.objects.get(administration=adm)
            self.assertIsNone(row.value)

    def test_period_normalised_to_first_of_month(self):
        path = _csv(f"{self.a1.id},2026-08,1.0\n")
        call_command("import_admin_dataset", "ndvi_anomaly", path)
        row = AdminDatasetValue.objects.get(administration=self.a1)
        self.assertEqual(row.period, date(2026, 8, 1))

    def test_missing_file_fails_loudly(self):
        with self.assertRaises(CommandError):
            call_command("import_admin_dataset", "k", "/no/such/file.csv")

    def test_bad_header_fails_loudly(self):
        f = tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, newline=""
        )
        f.write("wrong,cols\n1,2\n")
        f.close()
        with self.assertRaises(CommandError):
            call_command("import_admin_dataset", "k", f.name)
