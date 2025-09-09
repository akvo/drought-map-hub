"use client";

import {
  DROUGHT_CATEGORY_COLOR,
  DROUGHT_CATEGORY_LABEL,
  EXPORT_FORMAT_OPTIONS,
} from "@/static/config";
import {
  Button,
  Dropdown,
  message,
  Modal,
  Skeleton,
  Space,
  Typography,
} from "antd";
import { DownloadIcon, ExternalLinkIcon } from "../Icons";
import { useEffect, useState } from "react";
import CDIMap from "./CDIMap";

const { Title } = Typography;

const PublicMap = ({ id, validated_values: data = [], bulletin_url }) => {
  const [currentID, setCurrentID] = useState(null);
  const [downloading, setDownloading] = useState(false);

  const handleOnDownload = async ({ key: export_type }) => {
    setDownloading(true);
    try {
      const response = await fetch(
        `/api/v1/map/${id}/export?export_type=${export_type}`,
        {
          method: "GET",
        }
      );
      if (response.status === 200) {
        const res = await response.blob();
        const url = window.URL.createObjectURL(new Blob([res]));
        const a = document.createElement("a");
        a.href = url;
        const contentDisposition = response.headers.get("Content-Disposition");
        let filename = "map_export";
        if (contentDisposition) {
          const match = contentDisposition.match(/filename="(.+)"/);
          if (match.length === 2) {
            filename = match[1];
          }
        }
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
      } else {
        message.error("Unable to export map");
      }

      setDownloading(false);
    } catch (err) {
      console.error(err);
      setDownloading(false);
    }
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
    Modal.info({
      title: feature?.properties?.name,
      content: (
        <Title level={3}>{DROUGHT_CATEGORY_LABEL?.[findAdm?.category]}</Title>
      ),
    });
  };

  useEffect(() => {
    if (currentID !== id) {
      setTimeout(() => {
        setCurrentID(id);
      }, 500);
    }
  }, [id, currentID]);

  return (
    <div className="w-full flex flex-row gap-6">
      {currentID !== id && (
        <Skeleton.Image style={{ width: "50vw", height: "60vh" }} active />
      )}
      <Skeleton
        loading={currentID !== id}
        paragraph={{ rows: 16 }}
        title
        active
      >
        <div className="w-full">
          <CDIMap dragging={false} {...{ onFeature, onClick }} height={180}>
            <div className="w-1/3 xl:w-1/4 absolute top-0 right-0 z-10 p-2">
              <CDIMap.Legend isPublic />
              <div className="px-6 py-4 border-x border-x-neutral-100 bg-white">
                <Space>
                  <DownloadIcon />
                  <strong>MAP DOWNLOAD</strong>
                </Space>
              </div>
              <div className="p-4 border border-neutral-100 bg-white">
                <Dropdown
                  menu={{
                    items: EXPORT_FORMAT_OPTIONS,
                    onClick: handleOnDownload,
                  }}
                  trigger={["click"]}
                >
                  <Button type="primary" loading={downloading} block>
                    Download
                  </Button>
                </Dropdown>
              </div>
              {bulletin_url && (
                <div className="w-full">
                  <div className="px-6 py-4 border-x border-x-neutral-100 bg-white">
                    <Space>
                      <ExternalLinkIcon />
                      <strong>PUBLICATION BULLETIN</strong>
                    </Space>
                  </div>
                  <div className="p-4 border border-neutral-100 bg-white">
                    <Button
                      type="primary"
                      href={bulletin_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      block
                    >
                      Open Bulletin
                    </Button>
                  </div>
                </div>
              )}
            </div>
          </CDIMap>
        </div>
      </Skeleton>
    </div>
  );
};

export default PublicMap;
