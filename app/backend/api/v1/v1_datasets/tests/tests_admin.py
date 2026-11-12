from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from api.v1.v1_datasets.models import AdminDatasetValue
from api.v1.v1_publication.models import Administration

User = get_user_model()

IMPORT_URL = "/admin/v1_datasets/admindatasetvalue/import-csv/"
TEMPLATE_URL = "/admin/v1_datasets/admindatasetvalue/csv-template/"


class AdminImportTest(TestCase):
    def setUp(self):
        self.a1 = Administration.objects.create(name="A1")
        self.a2 = Administration.objects.create(name="A2")
        self.staff = User.objects.create_superuser(
            name="Admin", email="admin@test.com", password="x"
        )
        self.client.force_login(self.staff)

    def _upload(self, body: bytes):
        return SimpleUploadedFile("d.csv", body, content_type="text/csv")

    def test_import_creates_rows_and_rejects_unknown_id(self):
        body = (
            "administration_id,period,value\n"
            f"{self.a1.id},2026-08,-14.2\n"
            f"{self.a2.id},2026-08,\n"
            "999999,2026-08,1.0\n"
        ).encode("utf-8")
        res = self.client.post(
            IMPORT_URL,
            {"dataset": "evi2", "csv_file": self._upload(body)},
            follow=True,
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(AdminDatasetValue.objects.count(), 2)
        # blank value stored as NULL, not 0
        row = AdminDatasetValue.objects.get(administration=self.a2)
        self.assertIsNone(row.value)
        # unknown id rejected, not created
        self.assertFalse(
            AdminDatasetValue.objects.filter(administration_id=999999).exists()
        )

    def test_missing_dataset_key_rejected(self):
        body = b"administration_id,period,value\n1,2026-08,1\n"
        self.client.post(IMPORT_URL, {"csv_file": self._upload(body)})
        self.assertEqual(AdminDatasetValue.objects.count(), 0)

    def test_bad_header_rejected(self):
        body = b"wrong,cols\n1,2\n"
        self.client.post(
            IMPORT_URL,
            {"dataset": "evi2", "csv_file": self._upload(body)},
        )
        self.assertEqual(AdminDatasetValue.objects.count(), 0)

    def test_template_download_is_csv(self):
        res = self.client.get(TEMPLATE_URL)
        self.assertEqual(res.status_code, 200)
        self.assertIn("text/csv", res["Content-Type"])
        self.assertIn(b"administration_id", res.content)

    def test_import_requires_staff_login(self):
        self.client.logout()
        res = self.client.get(IMPORT_URL)
        # admin_view redirects anonymous users to the login page
        self.assertEqual(res.status_code, 302)
