"use client";

import { useMapEvent } from "react-leaflet";
import { useState } from "react";
import { DEFAULT_CENTER } from "@/static/config";

const GetCoordinates = () => {
  const [center, setCenter] = useState(DEFAULT_CENTER);

  useMapEvent("moveend", (e) => {
    setCenter(e.target.getCenter()); // Update center state
  });

  return (
    <div>
      <p>
        Center: {center.lat}, {center.lng}
      </p>
    </div>
  );
};

export default GetCoordinates;
