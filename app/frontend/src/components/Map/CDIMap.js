"use client";

// import L from "leaflet";
// import "leaflet.pattern";
import { DEFAULT_CENTER } from "@/static/config";
import Map from "./Map";
import { useMap, GeoJSON } from "react-leaflet";
import {
  dotShapeOptions,
  // patternOptions,
  styleOptions,
} from "@/static/poly-styles";
import { useAppContext } from "@/context/AppContextProvider";
import { Flex, Spin } from "antd";
import CDIMapLegend from "./CDIMapLegend";
import { useCallback, useEffect, useState } from "react";
import { getAppConfig } from "@/lib";

const CDIGeoJSON = ({ geoData, onEachFeature, style }) => {
  const map = useMap();
  const { refreshMap } = useAppContext();

  if (refreshMap) {
    return (
      <Flex align="center" justify="center" className="w-full h-full" vertical>
        <Spin tip="Updating..." />
      </Flex>
    );
  }

  return (
    <GeoJSON
      key="geodata"
      data={geoData}
      weight={1}
      onEachFeature={(feature, layer) => onEachFeature(feature, layer, map)}
      style={style}
    />
  );
};

const CDIMap = ({
  children,
  onFeature,
  onClick = () => {},
  style = {},
  ...props
}) => {
  const [mapCenter, setMapCenter] = useState(null);
  const [mapIsReady, setMapIsReady] = useState(false);
  const appContext = useAppContext();
  const geoData = appContext?.geoData || window?.topojson;

  const onEachFeature = (feature, layer) => {
    const { fillColor, weight, color } =
      typeof onFeature === "function" ? onFeature(feature) : {};
    layer.setStyle({
      ...styleOptions,
      fillColor: fillColor || dotShapeOptions?.fillColor,
      weight: weight || styleOptions?.weight,
      color: color || styleOptions?.color,
    });
    layer.on({
      click: () => (typeof onClick === "function" ? onClick(feature) : null),
    });
  };

  const loadMapCenter = useCallback(async () => {
    if (!mapIsReady && mapCenter !== null && geoData) {
      setMapIsReady(true);
    }
    if (mapCenter !== null) {
      return;
    }
    const appConfig = await getAppConfig();
    if (appConfig?.map_center && typeof appConfig?.map_center === "string") {
      try {
        const mapCenter = JSON.parse(appConfig.map_center);
        if (mapCenter?.lat && mapCenter?.lng) {
          setMapCenter([mapCenter.lat, mapCenter.lng]);
        } else {
          setMapCenter(DEFAULT_CENTER);
        }
      } catch (err) {
        console.error("Invalid map_center format in app config:", err);
        setMapCenter(DEFAULT_CENTER);
        return;
      }
    } else {
      setMapCenter(DEFAULT_CENTER);
    }
  }, [mapCenter, mapIsReady, geoData]);

  useEffect(() => {
    loadMapCenter();
  }, [loadMapCenter]);

  if (!mapIsReady) {
    return null;
  }

  return (
    <div className="relative bg-neutral-100">
      {children}
      <Map
        center={mapCenter}
        height={80}
        zoom={9}
        minZoom={6}
        scrollWheelZoom={false}
        {...props}
      >
        {() => <CDIGeoJSON {...{ geoData, onEachFeature }} style={style} />}
      </Map>
    </div>
  );
};

CDIMap.Legend = CDIMapLegend;

export default CDIMap;
