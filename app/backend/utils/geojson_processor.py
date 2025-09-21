import json
from pathlib import Path
from django.conf import settings
import geopandas as gpd
from topojson import Topology


def process_geojson_file(geojson_file):
    """
    Process uploaded GeoJSON file and convert it to TopoJSON.
    Saves to country.topojson in production or country-test.topojson
    during tests.
    Args:
        geojson_file: Django UploadedFile object containing GeoJSON data
    Returns:
        str: Path to the saved TopoJSON file
    Raises:
        ValueError: If the file cannot be processed or converted
    """
    try:
        # Read the GeoJSON content
        geojson_content = geojson_file.read()
        geojson_data = json.loads(geojson_content.decode('utf-8'))
        # Reset file pointer for potential reuse
        geojson_file.seek(0)
        # Create a GeoDataFrame from the GeoJSON data
        gdf = gpd.GeoDataFrame.from_features(
            geojson_data.get('features', []),
            crs="EPSG:4326"
        )
        # Convert the GeoDataFrame to a TopoJSON topology
        topo = Topology(gdf)
        # Get the TopoJSON. `Topology.to_json()` may return either a
        # JSON string or a dict.
        topojson_raw = topo.to_json()
        # If it's a string, parse it to a Python dict to avoid writing a
        # quoted JSON string into the .topojson file (which would add
        # extra quotes).
        if isinstance(topojson_raw, str):
            try:
                topojson_data = json.loads(topojson_raw)
            except json.JSONDecodeError:
                # If parsing fails, fall back to writing the raw string
                # as-is but wrapped under a key so the output stays JSON.
                topojson_data = {"topojson": topojson_raw}
        else:
            topojson_data = topojson_raw
        # Determine the target filename based on TEST_ENV setting
        if getattr(settings, 'TEST_ENV', False):
            filename = 'country-test.topojson'
        else:
            filename = 'country.topojson'
        # Define the target path (in the source directory)
        source_dir = Path(settings.BASE_DIR) / 'source'
        target_path = source_dir / filename
        # Ensure the source directory exists
        source_dir.mkdir(exist_ok=True)
        # Write the TopoJSON data to the file
        with open(target_path, 'w', encoding='utf-8') as f:
            json.dump(topojson_data, f, ensure_ascii=False, indent=2)
        return str(target_path)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format in GeoJSON file: {str(e)}")
    except Exception as e:
        raise ValueError(f"Failed to process GeoJSON file: {str(e)}")


def validate_geojson_file(geojson_file):
    """
    Validate that the uploaded file is a valid GeoJSON.
    Args:
        geojson_file: Django UploadedFile object
    Returns:
        bool: True if valid, raises ValidationError if not
    Raises:
        ValueError: If the file is not a valid GeoJSON
    """
    if not geojson_file:
        raise ValueError("No file provided")
    if (
        geojson_file.content_type not in [
            'application/geo+json', 'application/json', 'text/json'
        ]
    ):
        raise ValueError(
            "Invalid file format. Please upload a valid GeoJSON file."
        )
    # Try to parse the file as JSON and validate basic GeoJSON structure
    try:
        content = geojson_file.read()
        geojson_data = json.loads(content.decode('utf-8'))
        # Reset file pointer
        geojson_file.seek(0)
        # Basic GeoJSON validation - must have type property
        if not isinstance(geojson_data, dict) or 'type' not in geojson_data:
            raise ValueError("Invalid GeoJSON format: missing 'type' property")
        # Check if it's a valid GeoJSON type
        valid_types = [
            'FeatureCollection', 'Feature', 'Point', 'LineString',
            'Polygon', 'MultiPoint', 'MultiLineString', 'MultiPolygon',
            'GeometryCollection'
        ]
        if geojson_data['type'] not in valid_types:
            raise ValueError(f"Invalid GeoJSON type: {geojson_data['type']}")
        return True
    except json.JSONDecodeError:
        raise ValueError(
            "Invalid file format. Please upload a valid GeoJSON file."
        )
    except UnicodeDecodeError:
        raise ValueError(
            "Invalid file encoding. Please upload a UTF-8 encoded file."
        )
