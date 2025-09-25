/**
 * Utility functions for GeoJSON processing and geographic calculations
 */

/**
 * Calculate the center (centroid) of a GeoJSON
 * @param {Object} geojsonData - The GeoJSON data
 * @returns {Object|null} - Center coordinates as {lat: number, lng: number} or null if invalid
 */
export const calculateGeoJSONCenter = (geojsonData) => {
  if (
    !geojsonData ||
    !geojsonData.features ||
    geojsonData.features.length === 0
  ) {
    return null;
  }

  let totalLat = 0;
  let totalLng = 0;
  let pointCount = 0;

  // Function to extract coordinates from different geometry types
  const extractCoordinates = (geometry) => {
    if (!geometry || !geometry.coordinates) return;

    switch (geometry.type) {
      case "Point":
        totalLng += geometry.coordinates[0];
        totalLat += geometry.coordinates[1];
        pointCount++;
        break;

      case "LineString":
        geometry.coordinates.forEach((coord) => {
          totalLng += coord[0];
          totalLat += coord[1];
          pointCount++;
        });
        break;

      case "Polygon":
        // Use only the outer ring (first array)
        geometry.coordinates[0].forEach((coord) => {
          totalLng += coord[0];
          totalLat += coord[1];
          pointCount++;
        });
        break;

      case "MultiPoint":
        geometry.coordinates.forEach((coord) => {
          totalLng += coord[0];
          totalLat += coord[1];
          pointCount++;
        });
        break;

      case "MultiLineString":
        geometry.coordinates.forEach((lineString) => {
          lineString.forEach((coord) => {
            totalLng += coord[0];
            totalLat += coord[1];
            pointCount++;
          });
        });
        break;

      case "MultiPolygon":
        geometry.coordinates.forEach((polygon) => {
          // Use only the outer ring of each polygon
          polygon[0].forEach((coord) => {
            totalLng += coord[0];
            totalLat += coord[1];
            pointCount++;
          });
        });
        break;

      case "GeometryCollection":
        geometry.geometries.forEach((geom) => {
          extractCoordinates(geom);
        });
        break;
    }
  };

  // Extract coordinates from all features
  geojsonData.features.forEach((feature) => {
    if (feature.geometry) {
      extractCoordinates(feature.geometry);
    }
  });

  if (pointCount === 0) {
    return null;
  }

  // Calculate the centroid
  return {
    lat: totalLat / pointCount,
    lng: totalLng / pointCount,
  };
};

/**
 * Extract properties from the first feature of a GeoJSON FeatureCollection
 * @param {Object} geojsonData - The GeoJSON data
 * @returns {Array} - Array of property objects with name and value
 */
export const extractGeoJSONProperties = (geojsonData) => {
  if (
    !geojsonData ||
    geojsonData.type !== "FeatureCollection" ||
    !geojsonData.features ||
    geojsonData.features.length === 0
  ) {
    return [];
  }

  const properties = geojsonData.features[0].properties || {};
  return Object.keys(properties).map((key) => ({
    name: key,
    value: properties[key],
  }));
};

/**
 * Validate if the data is a valid GeoJSON structure
 * @param {Object} data - Data to validate
 * @returns {boolean} - True if valid GeoJSON structure
 */
export const isValidGeoJSON = (data) => {
  if (!data || typeof data !== "object") {
    return false;
  }

  // Check if it has a type property
  if (!data.type) {
    return false;
  }

  // Check for valid GeoJSON types
  const validTypes = [
    "FeatureCollection",
    "Feature",
    "Point",
    "LineString",
    "Polygon",
    "MultiPoint",
    "MultiLineString",
    "MultiPolygon",
    "GeometryCollection",
  ];

  return validTypes.includes(data.type);
};
