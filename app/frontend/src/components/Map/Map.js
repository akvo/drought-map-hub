"use client";

import { DEFAULT_MAP_HEIGHT } from "@/static/config";
import classNames from "classnames";
import dynamic from "next/dynamic";

const DynamicMap = dynamic(() => import("./DynamicMap"), {
  ssr: false,
});

const Map = ({ className, isFullHeight, ...props }) => {
  const { height = DEFAULT_MAP_HEIGHT } = props;
  return (
    <div
      style={{ height: isFullHeight ? "100vh" : `calc(100vh - ${height}px)` }}
      role="figure"
      className={classNames("w-full", className)}
    >
      <DynamicMap {...props} />
    </div>
  );
};

export default Map;
