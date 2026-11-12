from datetime import date

from rest_framework import status
from rest_framework.test import APITestCase

from api.v1.v1_datasets.models import AdminDatasetValue
from api.v1.v1_publication.models import Administration


class AdminDatasetAPITest(APITestCase):
    def setUp(self):
        self.a1 = Administration.objects.create(name="A1")
        self.a2 = Administration.objects.create(name="A2")
        AdminDatasetValue.objects.create(
            administration=self.a1,
            dataset="ndvi_anomaly",
            period=date(2026, 8, 1),
            value=-14.2,
        )
        AdminDatasetValue.objects.create(
            administration=self.a2,
            dataset="ndvi_anomaly",
            period=date(2026, 8, 1),
            value=None,
        )
        AdminDatasetValue.objects.create(
            administration=self.a1,
            dataset="ndvi_anomaly",
            period=date(2026, 7, 1),
            value=1.0,
        )

    def test_get_returns_house_contract_shape(self):
        res = self.client.get("/api/v1/datasets/ndvi_anomaly?period=2026-08")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        body = res.json()
        self.assertEqual(
            body["meta"],
            {
                "key": "ndvi_anomaly",
                "label": "ndvi_anomaly",
                "unit": None,
                "period": "2026-08",
            },
        )
        self.assertEqual(
            body["data"],
            [
                {"administration_id": self.a1.id, "value": -14.2},
                {"administration_id": self.a2.id, "value": None},
            ],
        )

    def test_get_defaults_to_latest_period(self):
        res = self.client.get("/api/v1/datasets/ndvi_anomaly")
        self.assertEqual(res.json()["meta"]["period"], "2026-08")

    def test_bad_period_is_400(self):
        res = self.client.get("/api/v1/datasets/ndvi_anomaly?period=2026")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_periods_endpoint_lists_ascending(self):
        res = self.client.get("/api/v1/datasets/ndvi_anomaly/periods")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(
            res.json(),
            {"key": "ndvi_anomaly", "periods": ["2026-07", "2026-08"]},
        )

    def test_unknown_key_returns_empty_not_error(self):
        res = self.client.get("/api/v1/datasets/does_not_exist/periods")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.json()["periods"], [])
