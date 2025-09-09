"use client";

import { ValidationModal, ValidationTable } from "@/components";
import { useAppContext, useAppDispatch } from "@/context/AppContextProvider";
import { api, transformReviews } from "@/lib";
import {
  DROUGHT_CATEGORY_LABEL,
  DROUGHT_CATEGORY_VALUE,
} from "@/static/config";
import { Button, Skeleton, Tabs, Typography } from "antd";
import dayjs from "dayjs";
import dynamic from "next/dynamic";
import Link from "next/link";
import { redirect, useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

const ValidationMap = dynamic(() => import("@/components/Map/ValidationMap"), {
  ssr: false,
});

const { Title } = Typography;

const ValidationPage = ({ params }) => {
  const [activeTab, setActiveTab] = useState("table");
  const [publication, setPublication] = useState(null);
  const [dataSource, setDataSource] = useState([]);
  const [extraColumns, setExtraColumns] = useState([]);
  const [preload, setPreload] = useState(true);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState({
    nonDisputed: false,
    nonValidated: false,
  });
  const [activeModal, setActiveModal] = useState(null);

  const { administrations, refreshMap } = useAppContext();
  const appDispatch = useAppDispatch();
  const router = useRouter();

  const yearMonth = publication?.year_month
    ? dayjs(publication?.year_month, "YYYY-MM").format("MMMM YYYY")
    : "...";

  const [totalValidated, totalData] = useMemo(() => {
    if (!publication?.id) {
      return [0, 0];
    }
    // const total = publication?.initial_values?.filter(
    //   (v) => v?.category !== DROUGHT_CATEGORY_VALUE.none
    // )?.length;
    const total = publication?.initial_values?.length || 0;
    const validated =
      publication?.validated_values?.filter(
        (v) => v?.category || v?.category === 0
      )?.length || 0;
    return [validated, total];
  }, [publication]);

  const onFilter = async (nonDisputed, nonValidated) => {
    try {
      const { validated_values, reviews, users } = await api(
        "GET",
        `/admin/publication-reviews/${params.id}?non_disputed=${nonDisputed}&non_validated=${nonValidated}`
      );
      const _dataSource = transformReviews(administrations, reviews, users, {
        ...publication,
        validated_values,
      });
      setDataSource(_dataSource);
      return _dataSource;
    } catch (err) {
      console.error(err);
      return [];
    }
  };

  const onRefreshMap = useCallback(() => {
    appDispatch({
      type: "REFRESH_MAP_TRUE",
    });
    setTimeout(() => {
      appDispatch({
        type: "REFRESH_MAP_FALSE",
      });
    }, 500);
  }, [appDispatch]);

  const onSelectValue = useCallback(
    async (val, admID) => {
      try {
        const currentValues =
          publication?.validated_values?.length === administrations?.length
            ? publication.validated_values
            : dataSource;
        const payload = {
          validated_values: administrations?.map(({ administration_id }) => {
            const fd = currentValues?.find(
              (v) => v?.administration_id === administration_id
            );
            const category =
              administration_id === admID
                ? val
                : fd?.category === undefined
                ? null
                : fd?.category;
            return {
              category,
              administration_id,
            };
          }),
        };
        const { validated_values } = await api(
          "PUT",
          `/admin/publication/${params?.id}`,
          payload
        );
        if (activeTab === "map") {
          onRefreshMap();
        }

        if (validated_values) {
          setPublication({
            ...publication,
            validated_values,
          });
          const ds = dataSource?.map((d) => {
            const fd = validated_values?.find(
              (v) => v?.administration_id === d?.administration_id
            );
            const category =
              d?.administration_id === admID
                ? val
                : fd?.category === undefined
                ? d?.category
                : fd?.category;
            return {
              ...d,
              category,
            };
          });
          setDataSource(ds);
        }
      } catch (err) {
        console.error(err);
      }
    },
    [
      dataSource,
      administrations,
      activeTab,
      publication,
      onRefreshMap,
      params?.id,
    ]
  );

  const onNonDisputed = (isChecked = false) => {
    setFilter({
      ...filter,
      nonDisputed: isChecked,
    });
    return new Promise(async (resolve, reject) => {
      try {
        const res = await onFilter(isChecked, filter.nonValidated);
        resolve(res?.map((r) => r?.administration_id));
      } catch {
        reject([]);
      }
    });
  };

  const onNonValidated = async (isChecked = false) => {
    setFilter({
      ...filter,
      nonValidated: isChecked,
    });
    await onFilter(filter.nonDisputed, isChecked);
  };

  const onDetails = (record) => {
    setActiveModal(record);
  };

  const onBulkValidation = async (ids = []) => {
    try {
      const payload = {
        validated_values: administrations?.map(({ administration_id }) => {
          const findData = dataSource?.find(
            (d) => d?.administration_id === administration_id
          );
          const category =
            findData?.category === undefined ? null : findData?.category;
          const data = {
            category,
            administration_id,
          };
          if (ids?.includes(administration_id)) {
            return {
              ...data,
              category: findData?.[extraColumns?.[0]?.dataIndex],
            };
          }
          return data;
        }),
      };

      const { validated_values } = await api(
        "PUT",
        `/admin/publication/${params?.id}`,
        payload
      );
      if (validated_values) {
        setPublication({
          ...publication,
          validated_values,
        });
        const ds = dataSource?.map((d) => {
          const fd = validated_values.find(
            (v) => v?.administration_id === d?.administration_id
          );
          const category =
            fd?.category === undefined ? d?.category : fd?.category;
          return {
            ...d,
            category,
          };
        });

        setDataSource(ds);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const fetchData = useCallback(async () => {
    if (!preload || administrations?.length === 0) {
      return;
    }
    try {
      setPreload(false);
      const apiData = await api("GET", `/admin/publication/${params?.id}`);
      if (!apiData?.id) {
        redirect("/publications");
      }
      setPublication(apiData);
      const { reviews, users } = await api(
        "GET",
        `/admin/publication-reviews/${params.id}`
      );
      setDataSource(transformReviews(administrations, reviews, users, apiData));
      setExtraColumns(
        users.map((r) => ({
          title: r?.technical_working_group,
          dataIndex: r?.id,
          render: (value) => DROUGHT_CATEGORY_LABEL?.[value],
          width: 192,
        }))
      );
      setLoading(false);
    } catch (err) {
      setPreload(false);
      setLoading(false);
      console.error(err);
    }
  }, [params?.id, preload, administrations]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return (
    <div className="w-full">
      <div className="w-full py-3 flex flex-row align-center justify-between">
        <div>
          <Link href={`/publications/${params?.id}`}>
            <Title
              level={2}
            >{`Inkundla CDI Validation for: ${yearMonth}`}</Title>
          </Link>
        </div>
        <div>
          {totalData && totalData === totalValidated ? (
            <Button
              type="primary"
              size="large"
              onClick={() => {
                router.push(`/publications/${params?.id}/publish`);
              }}
            >
              Ready to Publish
            </Button>
          ) : (
            <div className="leading-2 text-center">
              <strong>REMAINING TINKHUNDLA</strong>
              <h2 className="text-2xl">
                {totalData ? totalData - totalValidated : "..."}
              </h2>
            </div>
          )}
        </div>
      </div>
      <Tabs
        activeKey={activeTab}
        onChange={(key) => {
          if (key === "map") {
            onRefreshMap();
          }
          setActiveTab(key);
        }}
        items={[
          {
            key: "table",
            label: "Table View",
            children: (
              <Skeleton loading={loading} title paragraph>
                <ValidationTable
                  data={dataSource}
                  {...{
                    extraColumns,
                    onDetails,
                    onSelectValue,
                    onNonDisputed,
                    onNonValidated,
                    onBulkValidation,
                  }}
                />
              </Skeleton>
            ),
          },
          {
            key: "map",
            label: "Map View",
            children: (
              <ValidationMap {...{ refreshMap, dataSource, onDetails }} />
            ),
          },
        ]}
      />
      <ValidationModal
        data={activeModal}
        isOpen={activeModal?.administration_id}
        onClose={() => setActiveModal(null)}
        onSelectValue={onSelectValue}
      />
    </div>
  );
};

export default ValidationPage;
