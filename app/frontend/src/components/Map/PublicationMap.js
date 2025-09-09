"use client";

import {
  Modal,
  Badge,
  Button,
  Descriptions,
  Flex,
  Typography,
  List,
  Tooltip,
} from "antd";
import dayjs from "dayjs";
import {
  PUBLICATION_STATUS,
  PUBLICATION_STATUS_OPTIONS,
} from "@/static/config";
import CDIMap from "./CDIMap";
import {
  DROUGHT_CATEGORY_COLOR,
  DROUGHT_CATEGORY_LABEL,
} from "@/static/config";
import { useRouter } from "next/navigation";
import { api } from "@/lib";
import { useCallback, useMemo, useState } from "react";
import { ClockIcon, VerifiedIcon } from "../Icons";
import classNames from "classnames";

const { Title } = Typography;

const openRawModal = (feature) => {
  const items = feature?.value
    ? [
        {
          key: 1,
          label: "CDI Value",
          children: DROUGHT_CATEGORY_LABEL?.[feature.category],
        },
        {
          key: 2,
          label: "Computed Value",
          children: parseFloat(feature?.value, 10).toFixed(2),
        },
      ]
    : [
        {
          key: 1,
          label: "CDI Value",
          children: DROUGHT_CATEGORY_LABEL?.[feature.category],
        },
      ];
  return Modal.info({
    title: feature?.name,
    content: <Descriptions items={items} layout="horizontal" column={1} />,
  });
};

const PublicationMap = ({
  data = [],
  publication = {},
  geonodeBaseURL = "",
}) => {
  const [loading, setLoading] = useState(false);
  const [number_reviews] = publication?.progress_reviews?.split("/");
  const router = useRouter();
  const [modal, contextHolder] = Modal.useModal();

  const openReviewProgress = useCallback(() => {
    const instance = modal.info({
      title: "Reviews Received",
      content: (
        <List
          dataSource={publication?.reviewers?.sort((_, b) => b?.is_completed)}
          renderItem={(item) => (
            <List.Item
              className={classNames("px-8", {
                "text-grey-600 bg-neutral-100": !item?.is_completed,
                "cursor-pointer text-green-600 bg-green-200":
                  item?.is_completed,
              })}
              onClick={() => {
                if (!item?.is_completed) {
                  return;
                }
                instance.destroy();
                router.replace(
                  `/publications/${publication?.id}/reviews/${item?.review_id}`
                );
              }}
            >
              <List.Item.Meta
                title={`${item?.name} (${item?.email})`}
                description={item?.technical_working_group}
                avatar={
                  <Tooltip
                    title={
                      item?.is_completed
                        ? "✅ Review Submitted"
                        : "⏳ Review In Progress/Pending"
                    }
                  >
                    <span>
                      {item?.is_completed ? (
                        <VerifiedIcon size={28} />
                      ) : (
                        <ClockIcon size={22} />
                      )}
                    </span>
                  </Tooltip>
                }
              />
            </List.Item>
          )}
        />
      ),
      cancelButtonProps: {
        style: {
          display: "none",
        },
      },
    });
  }, [publication, modal, router]);

  const descriptionItems = useMemo(() => {
    const status = PUBLICATION_STATUS_OPTIONS.find(
      (s) => s?.value === publication?.status
    );
    const items = [
      {
        key: 1,
        label: "Publication Date",
        children: dayjs(publication?.year_month).format("YYYY-MM"),
      },
      {
        key: 2,
        label: "Status",
        children: <Badge color={status?.color} text={status?.label} />,
      },
      {
        key: 3,
        label: "Geonode",
        children: (
          <>
            <a
              href={`${geonodeBaseURL}/catalogue/#/dataset/${publication?.cdi_geonode_id}`}
              target="_blank"
            >
              View in Geonode
            </a>
          </>
        ),
      },
      {
        key: 4,
        label: "Bulletin URL",
        children: (
          <>
            {publication?.bulletin_url ? (
              <a href={publication.bulletin_url} target="_blank">
                Open
              </a>
            ) : (
              "-"
            )}
          </>
        ),
      },
    ];
    // if (publication?.status === PUBLICATION_STATUS.in_review) {
    return [
      ...items,
      {
        key: 5,
        label: "Reviews Received",
        children: (
          <Flex
            align="center"
            justify="space-between"
            gap={8}
            className="w-full"
          >
            <span>{publication?.progress_reviews}</span>

            <Button type="link" iconPosition="end" onClick={openReviewProgress}>
              Details
            </Button>
          </Flex>
        ),
      },
    ];
    // }
    // return items;
  }, [publication, geonodeBaseURL, openReviewProgress]);

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
    openRawModal({ ...findAdm, name: feature?.properties?.name });
  };

  const goToValidation = async () => {
    setLoading(true);
    try {
      if (publication?.status === PUBLICATION_STATUS.in_review) {
        await api("PUT", `/admin/publication/${publication?.id}`, {
          status: PUBLICATION_STATUS.in_validation,
        });
        router.replace(`/publications/${publication?.id}/validation`);
        setLoading(false);
      } else {
        router.push(`/publications/${publication?.id}/validation`);
        setLoading(false);
      }
    } catch (err) {
      console.error(err);
      setLoading(false);
    }
  };

  const goToEdit = () => {
    router.push(`/publications/${publication?.id}/publish`);
  };

  return (
    <div className="w-full">
      <Flex align="center" justify="space-between">
        <div className="w-10/12 py-2">
          <Title level={2}>
            {`Inkundla CDI Publication for: ${dayjs(
              publication?.year_month,
              "YYYY-MM"
            ).format("MMMM YYYY")}`}
          </Title>
        </div>
        <div className="w-2/12 py-2 text-right">
          {publication?.status !== PUBLICATION_STATUS.published &&
            number_reviews >= 1 && (
              <Button type="primary" onClick={goToValidation} loading={loading}>
                {publication?.status === PUBLICATION_STATUS.in_review
                  ? "Start Validation"
                  : "Go to Validation"}
              </Button>
            )}
          {publication?.status === PUBLICATION_STATUS.published && (
            <Button type="primary" onClick={goToEdit}>
              Edit Publication
            </Button>
          )}
        </div>
      </Flex>
      {contextHolder}
      <CDIMap {...{ onFeature, onClick }}>
        <div className="w-1/2 xl:w-1/3 absolute top-0 right-0 z-10 p-2 space-y-4">
          <Descriptions
            column={1}
            items={descriptionItems}
            classNames={{
              label: "p-0",
            }}
            bordered
          />
          <CDIMap.Legend
            isPublic={publication?.status === PUBLICATION_STATUS.published}
          />
        </div>
      </CDIMap>
    </div>
  );
};

export default PublicationMap;
