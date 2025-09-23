"use client";

import React, { useState, useCallback, useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import {
  GeoJSON,
  TileLayer,
  useMap,
  Rectangle,
  Tooltip,
  Marker,
} from "react-leaflet";
import { Button, Form, Space, InputNumber } from "antd";
import { useAppContext, useAppDispatch } from "@/context/AppContextProvider";
import { setupApiFormData, storage } from "@/lib";
import * as turf from "@turf/turf";
import DynamicMap from "@/components/Map/DynamicMap";

const { useForm } = Form;

const BoundingBoxLayer = ({
  boundingBox,
  onBoundingBoxChange,
  isEditable = false,
}) => {
  if (!boundingBox) {
    return null;
  }

  // Convert bounding box [west, south, east, north] to Leaflet bounds [[south, west], [north, east]]
  const bounds = [
    [boundingBox[1], boundingBox[0]], // [south, west]
    [boundingBox[3], boundingBox[2]], // [north, east]
  ];

  const tooltipContent = `
    North: ${boundingBox[3].toFixed(6)}°
    South: ${boundingBox[1].toFixed(6)}°
    East: ${boundingBox[2].toFixed(6)}°
    West: ${boundingBox[0].toFixed(6)}°
  `;

  return (
    <>
      <Rectangle
        bounds={bounds}
        pathOptions={{
          fillColor: isEditable ? "#ff0000" : "#ff7800", // Red when editable, orange when not
          fillOpacity: 0.1,
          color: isEditable ? "#ff0000" : "#ff7800",
          weight: 2,
          dashArray: isEditable ? "5, 5" : "10, 10", // Different dash pattern when editable
        }}
      >
        <Tooltip permanent={false} direction="top">
          <div style={{ whiteSpace: "pre-line", minWidth: "200px" }}>
            {isEditable ? (
              <>
                <h5>
                  <i>Drag corners to resize bounding box.</i>
                </h5>
              </>
            ) : (
              <>
                <strong>Bounding Box:</strong>
                {tooltipContent}
              </>
            )}
          </div>
        </Tooltip>
      </Rectangle>

      {/* Editable corner markers */}
      {isEditable && onBoundingBoxChange && (
        <EditableCorners
          boundingBox={boundingBox}
          onBoundingBoxChange={onBoundingBoxChange}
        />
      )}
    </>
  );
};

const EditableCorners = ({ boundingBox, onBoundingBoxChange }) => {
  const map = useMap();

  const createDivIcon = useCallback(() => {
    if (map && map.L) {
      return map.L.divIcon({
        className: "corner-marker",
        html: '<div style="width: 12px; height: 12px; background: #ff0000; border: 3px solid white; border-radius: 50%; cursor: move; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>',
        iconSize: [18, 18],
        iconAnchor: [9, 9],
      });
    } else if (typeof window !== "undefined" && window.L) {
      return window.L.divIcon({
        className: "corner-marker",
        html: '<div style="width: 12px; height: 12px; background: #ff0000; border: 3px solid white; border-radius: 50%; cursor: move; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>',
        iconSize: [18, 18],
        iconAnchor: [9, 9],
      });
    }
    return null;
  }, [map]);

  const handleCornerDrag = useCallback(
    (corner, newPosition) => {
      const [west, south, east, north] = boundingBox;
      let newBoundingBox;

      switch (corner) {
        case "nw": // Northwest corner
          newBoundingBox = [newPosition.lng, south, east, newPosition.lat];
          break;
        case "ne": // Northeast corner
          newBoundingBox = [west, south, newPosition.lng, newPosition.lat];
          break;
        case "sw": // Southwest corner
          newBoundingBox = [newPosition.lng, newPosition.lat, east, north];
          break;
        case "se": // Southeast corner
          newBoundingBox = [west, newPosition.lat, newPosition.lng, north];
          break;
        default:
          return;
      }

      // Ensure bounds are valid (west < east, south < north)
      const validBounds = [
        Math.min(newBoundingBox[0], newBoundingBox[2]), // west
        Math.min(newBoundingBox[1], newBoundingBox[3]), // south
        Math.max(newBoundingBox[0], newBoundingBox[2]), // east
        Math.max(newBoundingBox[1], newBoundingBox[3]), // north
      ];

      onBoundingBoxChange(validBounds);
    },
    [boundingBox, onBoundingBoxChange],
  );

  const [west, south, east, north] = boundingBox;
  const icon = createDivIcon();

  if (!icon) return null;

  return (
    <>
      {/* Northwest corner */}
      <Marker
        position={[north, west]}
        icon={icon}
        draggable={true}
        eventHandlers={{
          dragend: (e) => {
            const newPos = e.target.getLatLng();
            handleCornerDrag("nw", newPos);
          },
        }}
      />

      {/* Northeast corner */}
      <Marker
        position={[north, east]}
        icon={icon}
        draggable={true}
        eventHandlers={{
          dragend: (e) => {
            const newPos = e.target.getLatLng();
            handleCornerDrag("ne", newPos);
          },
        }}
      />

      {/* Southwest corner */}
      <Marker
        position={[south, west]}
        icon={icon}
        draggable={true}
        eventHandlers={{
          dragend: (e) => {
            const newPos = e.target.getLatLng();
            handleCornerDrag("sw", newPos);
          },
        }}
      />

      {/* Southeast corner */}
      <Marker
        position={[south, east]}
        icon={icon}
        draggable={true}
        eventHandlers={{
          dragend: (e) => {
            const newPos = e.target.getLatLng();
            handleCornerDrag("se", newPos);
          },
        }}
      />
    </>
  );
};

const MapController = ({ boundingBox, triggerZoom }) => {
  const map = useMap();

  useEffect(() => {
    if (!boundingBox || !map || triggerZoom === 0) {
      return;
    }

    const timeoutId = setTimeout(() => {
      try {
        map.fitBounds(
          [
            [boundingBox[1], boundingBox[0]], // [lat, lng] format for Leaflet
            [boundingBox[3], boundingBox[2]],
          ],
          {
            padding: [20, 20], // Add some padding around the bounds
            maxZoom: 10, // Prevent zooming too far in
          },
        );

        // Invalidate size to ensure proper rendering
        map.invalidateSize();
      } catch (error) {
        console.error("Error fitting bounds:", error);
      }
    }, 200); // Increased delay to ensure map is ready

    return () => clearTimeout(timeoutId);
  }, [map, boundingBox, triggerZoom]);

  return null; // This component doesn't render anything
};

const Step2Page = () => {
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [boundingBox, setBoundingBox] = useState(null);
  const [triggerZoom, setTriggerZoom] = useState(0); // Use a counter instead of boolean
  const [showBoundingBox, setShowBoundingBox] = useState(true); // Show bounding box by default
  const [isEditingBounds, setIsEditingBounds] = useState(false); // Edit mode for bounding box
  const { setupGeoData: geoData } = useAppContext();
  const appDispatch = useAppDispatch();

  const [form] = useForm();
  const router = useRouter();

  // Function to manually trigger zoom
  const handleManualZoom = useCallback(() => {
    setTriggerZoom((prev) => prev + 1); // Increment to trigger new zoom
  }, []);

  // Handle bounding box changes from the editable rectangle
  const handleBoundingBoxChange = useCallback(
    (newBoundingBox) => {
      setBoundingBox(newBoundingBox);

      // Update form fields with new values
      form.setFieldsValue({
        s_lat: newBoundingBox[1],
        w_lon: newBoundingBox[0],
        n_lat: newBoundingBox[3],
        e_lon: newBoundingBox[2],
      });
    },
    [form],
  );

  // Handle form field changes to update bounding box
  const handleFormChange = useCallback(
    (changedFields, allFields) => {
      const values = form.getFieldsValue();
      if (values.s_lat && values.w_lon && values.n_lat && values.e_lon) {
        const newBoundingBox = [
          values.w_lon, // west
          values.s_lat, // south
          values.e_lon, // east
          values.n_lat, // north
        ];
        setBoundingBox(newBoundingBox);
      }
    },
    [form],
  );

  const handleOnFinish = async (values) => {
    setSubmitting(true);
    try {
      const formData = new FormData();
      formData.append("s_lat", values.s_lat);
      formData.append("w_lon", values.w_lon);
      formData.append("n_lat", values.n_lat);
      formData.append("e_lon", values.e_lon);
      await setupApiFormData("POST", "/bbox-setup", formData);
      router.push("/setup/step-3");
    } catch (error) {
      console.error("Error submitting form:", error);
    } finally {
      setSubmitting(false);
    }
  };

  const loadMap = useCallback(() => {
    if (!loading) {
      return;
    }
    // Load the map with the GeoDataLayer
    const geoStorage = storage.get("topojson");
    if (!geoData && geoStorage) {
      appDispatch({ type: "SET_SETUP_GEODATA", payload: geoStorage });
    }
    const geoDataToUse = geoData || geoStorage;

    if (!geoDataToUse) {
      console.warn("No geo data available to calculate bounding box");
      setLoading(false);
      return;
    }

    try {
      const bbox = turf.bbox(geoDataToUse);
      setBoundingBox(bbox);

      // Pre-fill the form fields with the bounding box values
      form.setFieldsValue({
        s_lat: bbox[1],
        w_lon: bbox[0],
        n_lat: bbox[3],
        e_lon: bbox[2],
      });

      setLoading(false);
    } catch (error) {
      console.error("Error calculating bounding box:", error);
      setLoading(false);
    }
  }, [geoData, appDispatch, form, loading]);

  useEffect(() => {
    loadMap();
  }, [loadMap]);

  // Trigger zoom when data is loaded (only once)
  useEffect(() => {
    if (!loading && boundingBox && triggerZoom === 0) {
      setTriggerZoom(1); // Trigger initial zoom
    }
  }, [loading, boundingBox, triggerZoom]);

  return (
    <div>
      <h1>Step 2: Bounding Box Setup</h1>
      <p>This is the second step of the setup process.</p>
      {isEditingBounds && (
        <div className="mb-2 p-3 bg-yellow-50 border border-yellow-200 rounded">
          <strong>Edit Mode:</strong> Drag the red corner markers to resize the
          bounding box. The form fields will update automatically.
        </div>
      )}

      {/* Map controls */}
      {!loading && boundingBox && (
        <div className="mb-4">
          <Space>
            <Button
              type="default"
              onClick={handleManualZoom}
              disabled={!boundingBox}
            >
              Zoom to Area
            </Button>
            <Button
              type={showBoundingBox ? "primary" : "default"}
              onClick={() => setShowBoundingBox(!showBoundingBox)}
            >
              {showBoundingBox ? "Hide" : "Show"} Bounding Box
            </Button>
            <Button
              type={isEditingBounds ? "primary" : "default"}
              onClick={() => setIsEditingBounds(!isEditingBounds)}
              disabled={!showBoundingBox}
            >
              {isEditingBounds ? "Stop Editing" : "Edit Bounds"}
            </Button>
          </Space>
        </div>
      )}

      {!loading && (
        <div
          style={{ height: `calc(100vh - 320px)` }}
          role="figure"
          className="w-full mb-4"
        >
          <DynamicMap
            zoom={4}
            minZoom={3}
            scrollWheelZoom={false}
            center={[0, 0]}
            boundingBox={boundingBox}
            dragging={false}
          >
            {() => (
              <>
                <TileLayer
                  attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                  url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                <GeoJSON
                  key="geodata"
                  data={geoData}
                  style={{
                    weight: 2,
                    color: "#3388ff",
                    fillOpacity: 0.2,
                    fillColor: "#3388ff",
                  }}
                />
                {showBoundingBox && (
                  <BoundingBoxLayer
                    boundingBox={boundingBox}
                    onBoundingBoxChange={handleBoundingBoxChange}
                    isEditable={isEditingBounds}
                  />
                )}
                <MapController
                  boundingBox={boundingBox}
                  triggerZoom={triggerZoom}
                />
              </>
            )}
          </DynamicMap>
        </div>
      )}
      <Form
        form={form}
        onFinish={handleOnFinish}
        onFieldsChange={handleFormChange}
      >
        <Space>
          <Form.Item
            label="South Latitude"
            name="s_lat"
            rules={[
              { required: true, message: "South latitude is required" },
              {
                type: "number",
                min: -90,
                max: 90,
                message: "Must be between -90 and 90",
              },
            ]}
          >
            <InputNumber
              step={0.000001}
              precision={6}
              style={{ width: "150px" }}
            />
          </Form.Item>
          <Form.Item
            label="West Longitude"
            name="w_lon"
            rules={[
              { required: true, message: "West longitude is required" },
              {
                type: "number",
                min: -180,
                max: 180,
                message: "Must be between -180 and 180",
              },
            ]}
          >
            <InputNumber
              step={0.000001}
              precision={6}
              style={{ width: "150px" }}
            />
          </Form.Item>
        </Space>
        <Space>
          <Form.Item
            label="North Latitude"
            name="n_lat"
            rules={[
              { required: true, message: "North latitude is required" },
              {
                type: "number",
                min: -90,
                max: 90,
                message: "Must be between -90 and 90",
              },
            ]}
          >
            <InputNumber
              step={0.000001}
              precision={6}
              style={{ width: "150px" }}
            />
          </Form.Item>
          <Form.Item
            label="East Longitude"
            name="e_lon"
            rules={[
              { required: true, message: "East longitude is required" },
              {
                type: "number",
                min: -180,
                max: 180,
                message: "Must be between -180 and 180",
              },
            ]}
          >
            <InputNumber
              step={0.000001}
              precision={6}
              style={{ width: "150px" }}
            />
          </Form.Item>
        </Space>
        <Space>
          <Link href="/setup/step-1">
            <Button type="default">Previous</Button>
          </Link>
          <Button type="primary" htmlType="submit" loading={submitting}>
            Next
          </Button>
        </Space>
      </Form>
    </div>
  );
};

export default Step2Page;
