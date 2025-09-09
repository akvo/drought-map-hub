from django.test import TestCase


# Create your tests here.
class HealthCheckTestCase(TestCase):
    def test_healthcheck_endpoint(self):
        res = self.client.get("/api/v1/health/check")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data, {"message": "OK"})
