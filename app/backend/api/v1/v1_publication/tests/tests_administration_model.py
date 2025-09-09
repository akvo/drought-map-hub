from django.test import TestCase
from api.v1.v1_publication.models import Administration


class AdministrationModelTest(TestCase):
    def test_create_administration(self):
        admin = Administration.objects.create(
            name="Test Administration",
            region="Test region",
        )
        self.assertEqual(str(admin), "Test Administration")
        self.assertIsNotNone(admin.created_at)

    def test_administration_fields(self):
        admin = Administration.objects.create(
            name="Another Admin",
        )
        self.assertEqual(admin.region, None)
        self.assertEqual(admin.name, "Another Admin")
