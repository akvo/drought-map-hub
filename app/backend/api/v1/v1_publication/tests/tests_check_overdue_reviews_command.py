from unittest.mock import patch
from django.utils import timezone
from django.test import TestCase
from django.core.management import call_command
from django.test.utils import override_settings
from api.v1.v1_publication.models import (
    Publication,
    PublicationStatus,
)


@override_settings(USE_TZ=False, TEST_ENV=True)
class OverdueReviewsCommandTestCase(TestCase):
    def setUp(self):
        call_command("fake_users_seeder", "--test", True, "--repeat", 2)
        call_command("fake_publications_seeder", "--test", True)
        publication = (
            Publication.objects.filter(status=PublicationStatus.in_review)
            .order_by("?")
            .first()
        )
        publication.due_date = timezone.datetime(2025, 1, 28)
        publication.save()
        self.publication = publication

    def test_all_incomplete_on_track(self):
        """Ensure no overdue notifications when on track"""
        call_command("check_overdue_reviews", mock_now="2025-01-27")

        number_of_notified = self.publication.reviews.filter(
            is_overdue_notified=True,
        ).count()
        self.assertEqual(number_of_notified, 0)

    @patch("django.utils.timezone.now")
    def test_all_incomplete_overdue(self, mock_timezone_now):
        mock_timezone_now.return_value = timezone.datetime(2025, 1, 29)
        """Ensure overdue notifications are triggered"""
        call_command("check_overdue_reviews")

        number_of_notified = self.publication.reviews.filter(
            is_completed=False,
            is_overdue_notified=True,
        ).count()
        self.assertEqual(number_of_notified, 2)
