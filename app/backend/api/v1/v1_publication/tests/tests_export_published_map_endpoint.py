import geopandas as gpd
from rest_framework.test import APITestCase
from rest_framework import status
from PIL import Image
from zipfile import ZipFile
from io import BytesIO
from unittest.mock import patch
# from shapely.geometry import Point
from django.urls import reverse
from django.utils import timezone
from django.test.utils import override_settings
from api.v1.v1_publication.models import Publication
from api.v1.v1_publication.constants import DroughtCategory, PublicationStatus


@override_settings(USE_TZ=False, TEST_ENV=True)
class ExportMapAPITest(APITestCase):
    def setUp(self):
        """
        Set up the test environment.
        """
        self.published = Publication.objects.create(
            year_month="2025-02-01",
            cdi_geonode_id=44,
            due_date="2025-03-29",
            initial_values=[
                {"administration_id": 11, "category": DroughtCategory.d2},
                {"administration_id": 12, "category": DroughtCategory.d4},
            ],
            validated_values=[
                {"administration_id": 11, "category": DroughtCategory.d2},
                {"administration_id": 12, "category": DroughtCategory.d1},
            ],
            status=PublicationStatus.published,
            narrative="Lorem ipsum dolor amet...",
            published_at=timezone.now(),
        )
        self.url = reverse(
            "map-export", kwargs={"version": "v1", "pk": self.published.id}
        )

    def mock_gdf(self):
        """
        Mocked version of _load_geodataframe for testing.
        """
        # Step 1: Simulate converting TopoJSON to GeoJSON
        geojson_data = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
                    },
                    "properties": {
                        "administration_id": 4588078,
                        "region": "Hhohho",
                        "name": "Hhukwini",
                    },
                },
                {
                    "type": "Feature",
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[[2, 2], [3, 2], [3, 3], [2, 3], [2, 2]]],
                    },
                    "properties": {
                        "administration_id": 4588079,
                        "region": "Lubombo",
                        "name": "Siteki",
                    },
                },
            ],
        }

        # Step 2: Simulate loading GeoJSON into a GeoDataFrame
        gdf = gpd.GeoDataFrame.from_features(geojson_data)

        # Step 3: Map the categories to the GeoDataFrame
        validated_values = [
            {"administration_id": 4588078, "category": 1},
            {"administration_id": 4588079, "category": 2},
        ]
        validated_dict = {
            item["administration_id"]: item["category"]
            for item in validated_values
        }
        gdf["category"] = gdf["administration_id"].map(validated_dict)

        # Step 5: Add the "cat_name" column
        gdf["cat_name"] = gdf["category"].map(
            DroughtCategory.FieldStr.get
        )

        # Step 6: Handle missing values (optional)
        gdf["category"] = gdf["category"].fillna(DroughtCategory.none)
        gdf["cat_name"] = gdf["cat_name"].fillna(
            DroughtCategory.FieldStr[DroughtCategory.none]
        )

        # Ensure the GeoDataFrame has a CRS
        if gdf.crs is None:
            gdf.set_crs("EPSG:4326", inplace=True)

        return gdf

    @patch("api.v1.v1_publication.views.ExportMapAPI._load_geodataframe")
    def test_export_geojson(self, mock_load_gdf):
        """
        Test exporting the map as GeoJSON.
        """
        mock_load_gdf.return_value = self.mock_gdf()

        # Create a GET request
        response = self.client.get(f"{self.url}?export_type=geojson")

        # Validate the response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/json")
        self.assertIn(
            "cdi_map_2025-02.geojson",
            response["Content-Disposition"]
        )

        # Check the content
        geojson_data = response.content.decode("utf-8")
        self.assertIn('"type": "FeatureCollection"', geojson_data)

    @patch("api.v1.v1_publication.views.ExportMapAPI._load_geodataframe")
    def test_export_shapefile(self, mock_load_gdf):
        """
        Test exporting the map as a Shapefile (zipped).
        """
        mock_load_gdf.return_value = self.mock_gdf()

        # Create a GET request
        response = self.client.get(f"{self.url}?export_type=shapefile")

        # Validate the response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/zip")
        self.assertIn("cdi_map_2025-02.zip", response["Content-Disposition"])

        # Check the content (ensure it's a valid zip file)

        zip_file = ZipFile(BytesIO(response.content))
        self.assertIn("cdi_map_2025-02.shp", zip_file.namelist())
        self.assertIn("cdi_map_2025-02.shx", zip_file.namelist())
        self.assertIn("cdi_map_2025-02.dbf", zip_file.namelist())

    def test_invalid_format(self):
        """
        Test handling of an invalid export format.
        """
        # Create a GET request with an invalid format
        response = self.client.get(f"{self.url}?export_type=invalid")
        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )

    def test_default_format(self):
        """
        Test default export format (GeoJSON).
        """
        # Create a GET request without specifying a format
        response = self.client.get(self.url)

        # Validate the response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "application/json")

    @patch("api.v1.v1_publication.views.ExportMapAPI._load_geodataframe")
    def test_export_svg(self, mock_load_gdf):
        """
        Test exporting the map as an SVG image.
        """
        gdf = self.mock_gdf()
        mock_load_gdf.return_value = gdf

        # Create a GET request
        response = self.client.get(f"{self.url}?export_type=svg")

        # Validate the response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "image/svg+xml")
        self.assertIn("cdi_map_2025-02.svg", response["Content-Disposition"])

        # Check the content (ensure it's valid SVG)
        svg_content = response.content.decode("utf-8")
        self.assertIn("<svg", svg_content)

    @patch("api.v1.v1_publication.views.ExportMapAPI._load_geodataframe")
    def test_export_png(self, mock_load_gdf):
        """
        Test exporting the map as an PNG image.
        """
        gdf = self.mock_gdf()
        mock_load_gdf.return_value = gdf

        # Create a GET request
        response = self.client.get(f"{self.url}?export_type=png")

        # Validate the response
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertIn("cdi_map_2025-02.png", response["Content-Disposition"])

        # Check the content (ensure it's a valid PNG image)
        img = Image.open(BytesIO(response.content))
        self.assertEqual(img.format, "PNG")
