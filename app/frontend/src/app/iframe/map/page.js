"use client";

import { DROUGHT_CATEGORY_COLOR } from "@/static/config";
import { api } from "@/lib";
import { Skeleton } from "antd";
import { useCallback, useEffect, useState } from "react";
import dynamic from "next/dynamic";

const CDIMap = dynamic(() => import("@/components/Map/CDIMap"), { ssr: false });

const IframeMapPage = ({ searchParams }) => {
  const { id } = searchParams;
  const [preload, setPreload] = useState(true);
  const [currentID, setCurrentID] = useState(null);
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState([]);

  const checkCurrentID = useCallback(() => {
    if (currentID && id && currentID !== id && !preload) {
      setCurrentID(id);
      setPreload(true);
    }
  }, [currentID, id, preload]);

  const fetchData = useCallback(async () => {
    try {
      if (preload) {
        setPreload(false);
        if (!isNaN(id)) {
          setLoading(true);
          const { validated_values } = await api("GET", `/map/${id}`);
          if (validated_values) {
            setData(validated_values);
          }
          setLoading(false);
        }
      }
    } catch (err) {
      console.error(err);
      setPreload(false);
    }
  }, [id, preload]);

  const onFeature = (feature) => {
    const findAdm = data?.find(
      (d) => d?.administration_id === feature?.properties?.administration_id
    );
    return {
      fillColor: DROUGHT_CATEGORY_COLOR?.[findAdm?.category] || "white",
    };
  };

  useEffect(() => {
    checkCurrentID();
  }, [checkCurrentID]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  if (loading) {
    return (
      <Skeleton.Image style={{ width: "100vw", height: "100vh" }} active />
    );
  }

  return (
    <div className="w-full">
      <CDIMap onFeature={onFeature} dragging={false} isFullHeight />
    </div>
  );
};

export default IframeMapPage;
