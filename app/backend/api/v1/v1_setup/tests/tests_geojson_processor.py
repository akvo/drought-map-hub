import json

from django.test import SimpleTestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile

from utils.geojson_processor import process_geojson_file

# Two polygons that share the edge x=1, so TopoJSON must deduplicate the shared
# arc. That dedup path is what broke under NumPy 2.x with topojson 1.9
# (np.in1d was removed in NumPy 2.0). A single-polygon fixture never exercises
# it, so this guards the numpy<->topojson combo in CI.
ADJACENT_FEATURE_COLLECTION = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {"NAME_2": "A"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]],
            },
        },
        {
            "type": "Feature",
            "properties": {"NAME_2": "B"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[1, 0], [2, 0], [2, 1], [1, 1], [1, 0]]],
            },
        },
    ],
}


# TEST_ENV=True so process_geojson_file writes country-test.topojson instead of
# clobbering the real source/country.topojson (same convention as the other
# v1_setup tests).
@override_settings(TEST_ENV=True)
class GeojsonProcessorDedupTest(SimpleTestCase):
    def test_adjacent_polygons_convert_to_topojson(self):
        upload = SimpleUploadedFile(
            "adjacent.geojson",
            json.dumps(ADJACENT_FEATURE_COLLECTION).encode("utf-8"),
            content_type="application/json",
        )

        # Must not raise (it did on numpy 2.x + topojson 1.9).
        path = process_geojson_file(upload, map_name_key="NAME_2")

        with open(path, encoding="utf-8") as f:
            topo = json.load(f)

        self.assertEqual(topo.get("type"), "Topology")
        self.assertTrue(topo.get("arcs"))
        self.assertIn("objects", topo)
