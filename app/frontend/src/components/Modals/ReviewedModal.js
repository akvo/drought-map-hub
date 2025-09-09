"use client";

import { useAppContext, useAppDispatch } from "@/context/AppContextProvider";
import {
  DROUGHT_CATEGORY_COLOR,
  DROUGHT_CATEGORY_LABEL,
} from "@/static/config";
import { Descriptions, Modal } from "antd";
import classNames from "classnames";
import { useMemo } from "react";

const ReviewedModal = ({ initial_values = [] }) => {
  const { activeAdm } = useAppContext();
  const appDispatch = useAppDispatch();

  const items = useMemo(() => {
    if (!activeAdm?.administration_id) {
      return [];
    }
    const findAdm = initial_values?.find(
      (v) => v?.administration_id === activeAdm?.administration_id
    );
    return [
      {
        key: 1,
        label: "Approved Computed Value",
        children: (
          <div
            className={classNames("px-4 py-3", {
              "text-white": activeAdm?.category >= 4,
            })}
            style={{
              backgroundColor: DROUGHT_CATEGORY_COLOR?.[activeAdm?.category],
            }}
          >
            {DROUGHT_CATEGORY_LABEL?.[activeAdm?.category]}
          </div>
        ),
      },
      {
        key: 2,
        label: "Computed Value",
        children: (
          <div
            className={classNames("px-4 py-3", {
              "text-white": findAdm?.category >= 4,
            })}
            style={{
              backgroundColor: DROUGHT_CATEGORY_COLOR?.[findAdm?.category],
            }}
          >
            {DROUGHT_CATEGORY_LABEL?.[findAdm?.category]}
          </div>
        ),
      },
    ];
  }, [activeAdm, initial_values]);

  const onClose = () => {
    appDispatch({
      type: "REMOVE_ACTIVE_ADM",
    });
  };

  return (
    <Modal
      title={activeAdm?.name}
      open={activeAdm?.administration_id ? true : false}
      onCancel={onClose}
      onOk={onClose}
      cancelButtonProps={{
        style: {
          display: "none",
        },
      }}
    >
      <Descriptions
        items={items}
        layout="vertical"
        column={1}
        classNames={{ root: "reviewed-descriptions" }}
        bordered
      />
    </Modal>
  );
};

export default ReviewedModal;
