from django.test import TestCase
from django.core.exceptions import ValidationError
from datetime import date
from api.v1.v1_publication.constants import PublicationStatus
from api.v1.v1_publication.models import Publication


class PublicationModelTest(TestCase):
    def test_create_valid_publication(self):
        initial_values = [{"administration_id": 1, "value": 100}]
        publication = Publication.objects.create(
            year_month=date(2025, 1, 1),
            cdi_geonode_id=12345,
            initial_values=initial_values,
            due_date=date(2025, 2, 1),
            status=PublicationStatus.in_review,
        )
        self.assertEqual(
            str(publication),
            "Publication: 12345 - 2025-01"
        )
        self.assertEqual(publication.status, PublicationStatus.in_review)

    def test_validate_json_values_success(self):
        valid_json = [{"administration_id": 1, "value": 50}]
        Publication.objects.create(
            year_month=date(2025, 1, 1),
            cdi_geonode_id=12345,
            initial_values=valid_json,
            due_date=date(2025, 2, 1),
        )

    def test_validate_json_values_failure(self):
        invalid_json = {"invalid": "json"}
        publication = Publication(
            year_month=date(2025, 1, 1),
            cdi_geonode_id=12345,
            initial_values=invalid_json,
            due_date=date(2025, 2, 1),
            status=PublicationStatus.in_review,
        )
        with self.assertRaises(ValidationError):
            publication.full_clean()

    def test_validate_json_item_is_not_dict(self):
        invalid_json = ["invalid", "json"]
        publication = Publication(
            year_month=date(2025, 1, 1),
            cdi_geonode_id=12345,
            initial_values=invalid_json,
            due_date=date(2025, 2, 1),
            status=PublicationStatus.in_review,
        )
        with self.assertRaises(ValidationError) as context:
            publication.full_clean()
        self.assertEqual(
            str(context.exception),
            (
                "{'initial_values': "
                "['Each item in JSON must be a dictionary.']}"
            )
        )

    def test_validate_json_adm_id_not_in_item(self):
        invalid_json = [{
            "value": 11
        }]
        publication = Publication(
            year_month=date(2025, 1, 1),
            cdi_geonode_id=12345,
            initial_values=invalid_json,
            due_date=date(2025, 2, 1),
            status=PublicationStatus.in_review,
        )
        with self.assertRaises(ValidationError) as context:
            publication.full_clean()
        self.assertEqual(
            str(context.exception),
            (
                "{'initial_values': "
                "[\"Each item must contain an 'administration_id' key.\"]}"
            )
        )

    def test_validate_json_value_not_in_item(self):
        invalid_json = [{
            "administration_id": 1100
        }]
        publication = Publication(
            year_month=date(2025, 1, 1),
            cdi_geonode_id=12345,
            initial_values=invalid_json,
            due_date=date(2025, 2, 1),
            status=PublicationStatus.in_review,
        )
        try:
            publication.full_clean()  # Should not raise ValidationError
        except ValidationError:
            self.fail("ValidationError was raised unexpectedly")
