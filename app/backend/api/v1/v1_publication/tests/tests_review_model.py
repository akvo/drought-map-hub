from django.test import TestCase
from django.core.exceptions import ValidationError
from datetime import date
from api.v1.v1_users.models import SystemUser
from api.v1.v1_publication.constants import PublicationStatus
from api.v1.v1_publication.models import Review, Publication


class ReviewModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = SystemUser.objects.create(
            email="testuser@example.com",
            password="password123",
        )
        cls.publication = Publication.objects.create(
            year_month=date(2025, 1, 1),
            cdi_geonode_id=12345,
            initial_values=[{"administration_id": 1, "value": 100}],
            due_date=date(2025, 2, 1),
            status=PublicationStatus.in_review,
        )

    def test_create_valid_review(self):
        review = Review.objects.create(
            publication=self.publication,
            user=self.user,
            is_completed=False,
        )
        self.assertEqual(
            str(review),
            f"Review: 2025-01-01 by {self.user.email}"
        )
        self.assertFalse(review.is_completed)

    def test_suggestion_values_validation_success(self):
        valid_json = [{"administration_id": 1, "value": 75}]
        review = Review.objects.create(
            publication=self.publication,
            user=self.user,
            suggestion_values=valid_json,
        )
        self.assertEqual(review.suggestion_values, valid_json)

    def test_suggestion_values_validation_failure(self):
        invalid_json = "Not a JSON object"
        review = Review(
            publication=self.publication,
            user=self.user,
            suggestion_values=invalid_json,
        )
        with self.assertRaises(ValidationError) as context:
            review.full_clean()
        self.assertEqual(
            str(context.exception),
            (
                "{'suggestion_values': "
                "['JSON values must be a list of objects.']}"
            ),
        )
