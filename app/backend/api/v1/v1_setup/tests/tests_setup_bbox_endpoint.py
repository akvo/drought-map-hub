from pathlib import Path
from django.urls import reverse
from django.test.utils import override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from api.v1.v1_setup.models import SiteConfig
import os
import json


@override_settings(
    USE_TZ=False,
    TEST_ENV=True,
    SETUP_SECRET_KEY="test-secret-key"
)
class SetupBboxAPITest(APITestCase):
    def setUp(self):
        self.url = reverse('bbox-setup', kwargs={"version": "v1"})
        self.site_config = SiteConfig.objects.create(
            uuid="123e4567-e89b-12d3-a456-426614174000",
            name="Test Site"
        )
        # Set up the config file path
        self.path = Path(__file__).resolve().parent
        self.config_path = "./source/config/cdi_project_settings.test.json"

        # Initial config with default bounds
        self.initial_bounds = {
            'n_lat': 0.0,
            's_lat': 0.0,
            'w_lon': 0.0,
            'e_lon': 0.0
        }
        with open(self.config_path, 'w') as f:
            json.dump({'bounds': self.initial_bounds}, f)

        self.valid_bbox = {
            'n_lat': 10.0,
            's_lat': -10.0,
            'w_lon': -20.0,
            'e_lon': 20.0
        }
        self.invalid_bbox = {
            'n_lat': -10.0,
            's_lat': 10.0,
            'w_lon': -20.0,
            'e_lon': 20.0
        }
        # Set the secret header
        self.client.credentials(HTTP_X_SETUP_SECRET='test-secret-key')

    def test_get_bounding_box_success(self):
        """Test retrieving the bounding box successfully."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('bounding_box', response.data)
        self.assertIn('message', response.data)
        self.assertEqual(response.data['bounding_box'], self.initial_bounds)
        self.assertEqual(
            response.data['message'], 'Bounding box retrieved successfully.'
        )

    def test_post_bounding_box_success(self):
        """Test updating the bounding box with valid data."""
        response = self.client.post(self.url, self.valid_bbox, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('bounding_box', response.data)
        self.assertIn('message', response.data)
        self.assertEqual(
            response.data['message'], 'Bounding box updated successfully.'
        )
        self.assertEqual(response.data['bounding_box'], {
            'n_lat': 10.0,
            's_lat': -10.0,
            'w_lon': -20.0,
            'e_lon': 20.0
        })
        # Verify the file was updated
        with open(self.config_path, 'r') as f:
            config = json.load(f)
        self.assertEqual(config['bounds'], self.valid_bbox)

    def test_post_bounding_box_invalid_s_lat_out_of_range_low(self):
        """Test POST with south latitude below -90."""
        invalid_data = self.valid_bbox.copy()
        invalid_data['s_lat'] = -100.0
        response = self.client.post(self.url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)
        self.assertIn("South latitude must be between -90 and 90.",
                      str(response.data))

    def test_post_bounding_box_invalid_s_lat_out_of_range_high(self):
        """Test POST with south latitude above 90."""
        invalid_data = self.valid_bbox.copy()
        invalid_data['s_lat'] = 100.0
        response = self.client.post(self.url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)
        self.assertIn("South latitude must be between -90 and 90.",
                      str(response.data))

    def test_post_bounding_box_invalid_n_lat_out_of_range_low(self):
        """Test POST with north latitude below -90."""
        invalid_data = self.valid_bbox.copy()
        invalid_data['n_lat'] = -100.0
        response = self.client.post(self.url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)
        self.assertIn("North latitude must be between -90 and 90.",
                      str(response.data))

    def test_post_bounding_box_invalid_n_lat_out_of_range_high(self):
        """Test POST with north latitude above 90."""
        invalid_data = self.valid_bbox.copy()
        invalid_data['n_lat'] = 100.0
        response = self.client.post(self.url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)
        self.assertIn("North latitude must be between -90 and 90.",
                      str(response.data))

    def test_post_bounding_box_invalid_w_lon_out_of_range_low(self):
        """Test POST with west longitude below -180."""
        invalid_data = self.valid_bbox.copy()
        invalid_data['w_lon'] = -200.0
        response = self.client.post(self.url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)
        self.assertIn("West longitude must be between -180 and 180.",
                      str(response.data))

    def test_post_bounding_box_invalid_w_lon_out_of_range_high(self):
        """Test POST with west longitude above 180."""
        invalid_data = self.valid_bbox.copy()
        invalid_data['w_lon'] = 200.0
        response = self.client.post(self.url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)
        self.assertIn("West longitude must be between -180 and 180.",
                      str(response.data))

    def test_post_bounding_box_invalid_e_lon_out_of_range_low(self):
        """Test POST with east longitude below -180."""
        invalid_data = self.valid_bbox.copy()
        invalid_data['e_lon'] = -200.0
        response = self.client.post(self.url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)
        self.assertIn("East longitude must be between -180 and 180.",
                      str(response.data))

    def test_post_bounding_box_invalid_e_lon_out_of_range_high(self):
        """Test POST with east longitude above 180."""
        invalid_data = self.valid_bbox.copy()
        invalid_data['e_lon'] = 200.0
        response = self.client.post(self.url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)
        self.assertIn("East longitude must be between -180 and 180.",
                      str(response.data))

    def test_post_bounding_box_invalid_n_lat_less_equal_s_lat(self):
        """Test POST with north latitude <= south latitude."""
        response = self.client.post(self.url, self.invalid_bbox, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)
        self.assertIn("North latitude must be greater than south latitude.",
                      str(response.data))

    def test_post_bounding_box_invalid_e_lon_less_equal_w_lon(self):
        """Test POST with east longitude <= west longitude."""
        invalid_data = self.valid_bbox.copy()
        invalid_data['e_lon'] = -20.0
        response = self.client.post(self.url, invalid_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('non_field_errors', response.data)
        self.assertIn("East longitude must be greater than west longitude.",
                      str(response.data))

    def test_post_bounding_box_missing_secret_header(self):
        """Test POST without the required secret header."""
        self.client.credentials()  # Remove credentials
        response = self.client.post(self.url, self.valid_bbox, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        data = response.json()
        self.assertIn('detail', data)
        self.assertEqual(data['detail'], 'Forbidden.')

    def test_get_bounding_box_missing_secret_header(self):
        """Test GET without the required secret header."""
        self.client.credentials()  # Remove credentials
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        data = response.json()
        self.assertIn('detail', data)
        self.assertEqual(data['detail'], 'Forbidden.')

    def tearDown(self):
        # Clean up the config file
        if os.path.exists(self.config_path):
            os.remove(self.config_path)
