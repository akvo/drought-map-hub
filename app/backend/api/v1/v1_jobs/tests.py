from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Jobs, JobTypes, JobStatus


class JobAPITestCase(APITestCase):
    def setUp(self):
        """
        Set up initial data for the tests.
        """
        self.job = Jobs.objects.create(
            type=JobTypes.test, status=JobStatus.done, result="Sample Job"
        )

    def test_view_job_success(self):
        """
        Test fetching an existing job by ID.
        """
        url = reverse(
            "view_job",
            kwargs={"version": "v1", "job_id": self.job.id}
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.job.id)
        self.assertEqual(response.data["result"], self.job.result)

    def test_view_job_not_found(self):
        """
        Test fetching a job that does not exist.
        """
        url = reverse("view_job", kwargs={"version": "v1", "job_id": 9999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_create_job_success(self):
        """
        Test creating a new job with a valid name.
        """
        url = reverse("create_job", kwargs={"version": "v1"})
        response = self.client.get(url, {"name": "Test Job"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Verify the job is created in the database
        job_id = response.data["job_id"]
        created_job = Jobs.objects.get(pk=job_id)
        self.assertEqual(created_job.result, "Test Job")
        self.assertEqual(created_job.type, JobTypes.test)
        self.assertEqual(created_job.status, JobStatus.on_progress)

    def test_create_job_missing_name(self):
        """
        Test creating a new job without providing a name.
        """
        url = reverse("create_job", kwargs={"version": "v1"})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_feedback_success(self):
        """
        Test submitting feedback successfully.
        """
        url = reverse("feedback", kwargs={"version": "v1"})
        response = self.client.post(
            url,
            {
                "email": "visitor@mail.com",
                "feedback": "This is a test feedback",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["message"], "Feedback received successfully"
        )
