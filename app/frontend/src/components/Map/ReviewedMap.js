"use client";

import {
  DROUGHT_CATEGORY_COLOR,
  DROUGHT_CATEGORY_VALUE,
} from "@/static/config";
import { styleOptions } from "@/static/poly-styles";
import { useAppContext, useAppDispatch } from "@/context/AppContextProvider";

import CDIMap from "./CDIMap";
import { Descriptions } from "antd";

const ReviewedMap = ({ data = [], review = {} }) => {
  const { activeAdm } = useAppContext();
  const appDispatch = useAppDispatch();

  const mapStyle = (feature) => {
    const isHighighted =
      feature?.properties?.administration_id === activeAdm?.administration_id;
    return {
      opacity: isHighighted ? 1 : styleOptions?.opacity,
      weight: isHighighted ? 5 : styleOptions?.weight,
      color: isHighighted ? "#032e15" : styleOptions?.color,
    };
  };

  const onFeature = (feature) => {
    const findAdm = data?.find(
      (d) => d?.administration_id === feature?.properties?.administration_id
    );
    return {
      fillColor: DROUGHT_CATEGORY_COLOR?.[findAdm?.category],
    };
  };

  const onClick = (feature) => {
    const findAdm = data?.find(
      (d) => d?.administration_id === feature?.properties?.administration_id
    );
    // if (findAdm?.category === DROUGHT_CATEGORY_VALUE.none) {
    //   return;
    // }
    appDispatch({
      type: "SET_ACTIVE_ADM",
      payload: { ...findAdm, name: feature?.properties?.name },
    });
  };

  return (
    <CDIMap {...{ onFeature, onClick }} style={mapStyle}>
      <div className="w-1/2 xl:w-1/3 absolute top-0 right-0 z-10 p-2 space-y-4">
        <Descriptions
          items={[
            {
              key: 1,
              label: "Reviewer Name",
              children: review?.user?.name,
            },
            {
              key: 2,
              label: "Reviewer Email",
              children: (
                <a href={`mailto:${review?.user?.email}`}>
                  {review?.user?.email}
                </a>
              ),
            },
            {
              key: 3,
              label: "Technical Working Group",
              children: review?.user?.technical_working_group,
            },
          ]}
          layout="vertical"
          column={1}
          bordered
        />
        <CDIMap.Legend />
      </div>
    </CDIMap>
  );
};

export default ReviewedMap;
