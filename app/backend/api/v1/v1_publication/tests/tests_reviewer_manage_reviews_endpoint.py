from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.core.management import call_command
from django.test.utils import override_settings
from api.v1.v1_users.models import SystemUser
from api.v1.v1_publication.models import (
    Publication,
    Review,
    PublicationStatus,
)
from api.v1.v1_publication.constants import (
    DroughtCategory,
)
from api.v1.v1_publication.serializers import ReviewSerializer


@override_settings(USE_TZ=False, TEST_ENV=True)
class ReviewViewSetTestCase(APITestCase):
    def setUp(self):
        call_command(
            "generate_administrations_seeder", "--test", True
        )
        call_command(
            "fake_users_seeder", "--test", True, "--repeat", 2
        )
        call_command(
            "fake_publications_seeder", "--test", True
        )

        self.publication = Publication.objects.first()
        self.review = self.publication.reviews.first()
        self.user = SystemUser.objects.get(
            pk=self.review.user_id
        )
        self.client.force_authenticate(user=self.user)

        # URLs
        self.list_url = reverse(
            "review-list",
            kwargs={"version": "v1"}
        )
        self.detail_url = lambda pk: reverse(
            "review-details",
            kwargs={"version": "v1", "pk": pk}
        )

    def test_list_reviews(self):
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            len(response.data["data"]), 2
        )
        self.assertIn(
            "progress_review", response.data["data"][0]
        )

    def test_retrieve_review(self):
        response = self.client.get(
            self.detail_url(self.review.id)
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.review.id)
        serializer = ReviewSerializer(
            instance=self.review,
            context={
                "total": 59
            }
        ).data
        self.assertEqual(
            response.data["progress_review"],
            serializer["progress_review"]
        )
        self.assertEqual(
            list(response.data["publication"]),
            [
                "id",
                "year_month",
                "due_date",
                "initial_values",
                "status",
            ]
        )

    def test_create_review(self):
        payload = {
            "publication_id": self.publication.id,
            "user_id": self.user.id,
            "is_completed": False,
            "suggestion_values": [
                {
                    "value": 40,
                    "category": None,
                    "administration_id": 1253002,
                    "reviewed": False
                },
                {
                    "value": 2,
                    "category": DroughtCategory.d1,
                    "administration_id": 1253053,
                    "reviewed": True
                }
            ],
        }
        response = self.client.post(
            self.list_url,
            data=payload,
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Review.objects.count(), 5)

    def test_update_review(self):
        payload = {
            "is_completed": True,
            "suggestion_values": [
                {
                    "value": 40,
                    "category": DroughtCategory.d2,
                    "administration_id": 1253002,
                    "reviewed": True
                },
                {
                    "value": 2,
                    "category": DroughtCategory.d4,
                    "administration_id": 1253053,
                    "reviewed": True
                }
            ],
        }
        response = self.client.put(
            self.detail_url(self.review.id), data=payload, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        updated_review = Review.objects.get(id=self.review.id)
        self.assertTrue(updated_review.is_completed)
        self.assertTrue(
            updated_review.suggestion_values[0]["reviewed"]
        )

    def test_publication_in_validation_when_all_reviews_are_completed(self):
        other_reviews = self.publication.reviews.exclude(
            id=self.review.id
        ).all()
        for other_review in other_reviews:
            other_review.is_completed = True
            other_review.save()

        payload = {
            "is_completed": True,
            "suggestion_values": [
                {
                    "value": 35,
                    "category": DroughtCategory.d2,
                    "administration_id": 1253002,
                    "reviewed": True
                },
                {
                    "value": 12,
                    "category": DroughtCategory.d1,
                    "administration_id": 1253053,
                    "reviewed": True
                }
            ],
        }
        response = self.client.put(
            self.detail_url(self.review.id), data=payload, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        updated_publication = Publication.objects.get(id=self.publication.id)
        self.assertEqual(
            updated_publication.status,
            PublicationStatus.in_validation
        )

    def test_list_reviews_pagination(self):
        response = self.client.get(f"{self.list_url}?page=1")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("data", response.data)
        self.assertIn("total", response.data)
        self.assertEqual(
            response.data["total"], 2
        )

    def test_permission_denied_for_unauthenticated_user(self):
        self.client.logout()
        response = self.client.get(self.list_url)
        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )

    def test_invalid_review_creation(self):
        payload = {
            "publication_id": None,
            "user_id": self.user.id,
            "is_completed": False,
        }
        response = self.client.post(self.list_url, data=payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_suggestion_values_of_review_creation(self):
        payload = {
            "publication_id": self.publication.id,
            "user_id": self.user.id,
            "is_completed": False,
            "suggestion_values": "OK"
        }
        response = self.client.post(self.list_url, data=payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_reviewed_with_null_category(
        self
    ):
        payload = {
            "publication_id": self.publication.id,
            "user_id": self.user.id,
            "is_completed": False,
            "suggestion_values": [
                {
                    "value": 40,
                    "administration_id": 1253002,
                    "reviewed": True,  # Reviewed but category is None
                    "category": None
                },
                {
                    "value": 2,
                    "administration_id": 1253053,
                    "reviewed": True,
                    "category": None
                }
            ],
        }
        response = self.client.post(self.list_url, data=payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_invalid_update_reviewed_with_null_category(
        self
    ):
        payload = {
            "is_completed": True,
            "suggestion_values": [
                {
                    "value": 40,
                    "administration_id": 1253002,
                    "reviewed": True,  # Invalid: requires category
                    "category": None
                },
                {
                    "value": 2,
                    "administration_id": 1253053,
                    "reviewed": True,
                    "category": None
                }
            ],
        }
        response = self.client.put(
            self.detail_url(self.review.id), data=payload, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_review_by_non_owner(self):
        non_owner = SystemUser.objects.exclude(
            pk=self.user.id
        ).first()
        self.client.force_authenticate(user=non_owner)
        req = self.client.delete(
            self.detail_url(self.review.id)
        )
        self.assertEqual(
            req.status_code,
            status.HTTP_404_NOT_FOUND
        )

    def test_create_with_null_category_when_not_reviewed(self):
        """Test that category can be null when reviewed is False"""
        payload = {
            "publication_id": self.publication.id,
            "user_id": self.user.id,
            "is_completed": False,
            "suggestion_values": [
                {
                    "value": 40,
                    "administration_id": 1253002,
                    "reviewed": False,  # Not reviewed, so category can be null
                    "category": None
                },
                {
                    "value": 2,
                    "administration_id": 1253053,
                    "reviewed": True,
                    "category": DroughtCategory.d1  # Must have value
                }
            ],
        }
        response = self.client.post(
            self.list_url,
            data=payload,
            format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    
    def test_delete_review(self):
        response = self.client.delete(
            self.detail_url(self.review.id)
        )
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            Review.objects.filter(pk=self.review.id).exists()
        )
