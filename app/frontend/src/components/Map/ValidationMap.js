"use client";

import {
  DROUGHT_CATEGORY_COLOR,
  DROUGHT_CATEGORY_LABEL,
  DROUGHT_CATEGORY_VALUE,
} from "@/static/config";
import { styleOptions } from "@/static/poly-styles";
import { useCallback } from "react";
import { Descriptions, Modal, Spin } from "antd";
import CDIMap from "./CDIMap";

const openFeature = (feature) => {
  const items = [
    {
      key: 1,
      label: "Validated Value",
      children: DROUGHT_CATEGORY_LABEL?.[feature?.category],
    },
    {
      key: 2,
      label: "Computed Value",
      children: DROUGHT_CATEGORY_LABEL?.[feature?.initial_category],
    },
  ];
  return Modal.info({
    title: feature?.name,
    content: <Descriptions items={items} layout="horizontal" column={1} />,
  });
};

const ValidationMap = ({
  refreshMap,
  dataSource,
  onDetails,
  readOnly = false,
}) => {
  const getData = useCallback(
    (admID) => {
      const findData = dataSource?.find((d) => d?.administration_id === admID);
      const isValidated = findData?.category || findData?.category === 0;
      const category = isValidated
        ? findData?.category
        : findData?.initial_category;
      return [isValidated, category, findData];
    },
    [dataSource]
  );

  const mapStyle = useCallback(
    (feature) => {
      const [isValidated] = getData(feature?.properties?.administration_id);
      return {
        opacity: isValidated ? 1 : styleOptions?.opacity,
        weight: isValidated ? 5 : styleOptions?.weight,
        color: isValidated ? "#032e15" : styleOptions?.color,
      };
    },
    [getData]
  );

  const onFeature = useCallback(
    (feature) => {
      const [isValidated, category] = getData(
        feature?.properties?.administration_id
      );
      return {
        fillColor: DROUGHT_CATEGORY_COLOR?.[category],
        weight: isValidated ? 4 : null,
        color: isValidated ? "green" : null,
      };
    },
    [getData]
  );

  const onClick = useCallback(
    (feature) => {
      const data = getData(feature?.properties?.administration_id)?.[2];
      // if (data?.initial_category === DROUGHT_CATEGORY_VALUE.none) {
      //   return;
      // }
      if (readOnly) {
        openFeature({ ...data, name: feature?.properties?.name });
      } else {
        onDetails({ ...data, name: feature?.properties?.name });
      }
    },
    [getData, onDetails, readOnly]
  );

  if (refreshMap) {
    return <Spin spinning />;
  }

  return (
    <CDIMap {...{ onFeature, onClick }} style={mapStyle}>
      <div className="w-1/2 xl:w-1/3 absolute top-0 right-0 z-10 p-2 space-y-4">
        <CDIMap.Legend isPublic />
      </div>
    </CDIMap>
  );
};

export default ValidationMap;
