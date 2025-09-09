"use client";

import { useAppContext, useAppDispatch } from "@/context/AppContextProvider";
import { api } from "@/lib";
import {
  DROUGHT_CATEGORY_COLOR,
  DROUGHT_CATEGORY_LABEL,
  DROUGHT_CATEGORY_VALUE,
} from "@/static/config";
import {
  Checkbox,
  Flex,
  Form,
  Tag,
  Input,
  Button,
  Modal,
  Space,
  List,
  Typography,
} from "antd";
import classNames from "classnames";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

const { Search } = Input;
const { useForm } = Form;
const { Text, Title } = Typography;

const mergeData = (administrations, dataSource) => {
  return administrations
    ?.map((a) => {
      const findData =
        dataSource.find((d) => d?.administration_id === a?.administration_id) ||
        {};
      return {
        ...a,
        ...findData,
        checked: false,
      };
    })
    ?.sort((a, b) =>
      a?.name?.toLowerCase()?.localeCompare(b?.name?.toLowerCase())
    );
};

const ReviewList = ({
  id,
  dataSource = [],
  isCompleted = false,
  remaining = 0,
}) => {
  const { administrations, refreshMap } = useAppContext();
  const [form] = useForm();
  const [marking, setMarking] = useState(false);
  const [checkAll, setCheckAll] = useState(false);
  const [search, setSearch] = useState(null);
  const router = useRouter();
  const appDispatch = useAppDispatch();

  const onOpen = (data) => {
    appDispatch({
      type: "SET_ACTIVE_ADM",
      payload: data,
    });
  };

  const onCheckAll = (e) => {
    const isChecked = e.target.checked;
    setCheckAll(isChecked);
    const admValues = form.getFieldValue("administrations").map((a) => {
      const checked =
        (isChecked && a?.category?.raw === DROUGHT_CATEGORY_VALUE.none) ||
        (isChecked && !a?.value)
          ? false
          : isChecked;
      return !a?.reviewed ? { ...a, checked } : a;
    });

    appDispatch({
      type: "SET_SELECTED_ADM",
      payload: admValues
        .filter((a) => a?.checked)
        .map((a) => a?.administration_id),
    });
    form.setFieldValue("administrations", admValues);
  };

  const onCheckAdm = (e, administration_id = 0) => {
    const isChecked = e.target.checked;
    appDispatch({
      type: isChecked ? "ADD_SELECTED_ADM" : "REMOVE_SELECTED_ADM",
      payload: parseInt(administration_id, 10),
    });
  };

  const onMarkAll = async () => {
    setMarking(true);
    try {
      const admValues = form
        .getFieldValue("administrations")
        .map(({ checked, category, ...a }) => {
          if (checked) {
            return {
              ...a,
              category: category?.raw,
              reviewed: true,
            };
          }
          return {
            ...a,
            category: category?.reviewed,
          };
        });
      await api("PUT", `/reviewer/review/${id}`, {
        suggestion_values: admValues.map(({ name: _, ...a }) => a),
      });
      appDispatch({
        type: "REFRESH_MAP_TRUE",
      });
      setTimeout(() => {
        appDispatch({
          type: "REFRESH_MAP_FALSE",
        });
      }, 1000);
      setCheckAll(false);
      setMarking(false);
      router.refresh();
    } catch (err) {
      setCheckAll(false);
      setMarking(false);
      console.error(err);
    }
  };

  const confirmMarkAll = () => {
    Modal.confirm({
      title: "Mark all selected as reviewed?",
      content: (
        <List
          dataSource={form
            .getFieldValue("administrations")
            .filter((a) => a?.checked)}
          header={<Title level={3}>Computed value Overview</Title>}
          renderItem={(item) => (
            <List.Item>
              <Space size="middle">
                <Text strong>{item?.name}</Text>
                <span
                  className={classNames("py-1 px-2 rounded text-white", {
                    "border border-neutral-200 text-black":
                      item?.category?.raw === DROUGHT_CATEGORY_VALUE.none,
                  })}
                  style={{
                    backgroundColor: `${
                      DROUGHT_CATEGORY_COLOR?.[item.category?.raw]
                    }`,
                  }}
                >
                  {DROUGHT_CATEGORY_LABEL?.[item.category?.raw]}
                </span>
              </Space>
            </List.Item>
          )}
        />
      ),
      onOk: onMarkAll,
      width: 480,
      okText: "Yes",
      closable: true,
    });
  };

  const resetState = useCallback(() => {
    /**
     * Reset all selected administrations at first render time
     **/
    appDispatch({
      type: "RESET_SELECTED_ADM",
    });
    if (refreshMap) {
      form.setFieldValue(
        "administrations",
        mergeData(administrations, dataSource)
      );
    }
  }, [appDispatch, refreshMap, form, administrations, dataSource]);

  useEffect(() => {
    resetState();
  }, [resetState]);

  if (!administrations?.length) {
    return null;
  }

  return (
    <div className="h-[calc(100vh-160px)] overflow-y-scroll">
      <Form
        form={form}
        initialValues={{
          administrations: mergeData(administrations, dataSource),
        }}
      >
        {(_, formInstance) => {
          const numberChecked = formInstance
            .getFieldValue("administrations")
            ?.filter((a) => a?.checked)?.length;

          return (
            <>
              <div className="p-4 sticky top-0 left-0 border-b border-neutral-200 bg-neutral-100 space-y-4 z-10">
                <Search
                  placeholder="Search Inkhundla"
                  onSearch={setSearch}
                  onClear={() => setSearch(null)}
                  allowClear
                />
                {!isCompleted && (
                  <Flex align="center" justify="space-between">
                    <Checkbox
                      onChange={onCheckAll}
                      disabled={remaining === 0}
                      checked={checkAll}
                    />
                    <div>
                      <Button
                        size="small"
                        disabled={numberChecked === 0}
                        onClick={confirmMarkAll}
                        loading={marking}
                      >{`Mark as Reviewed ${
                        numberChecked ? `(${numberChecked})` : ""
                      }`}</Button>
                    </div>
                  </Flex>
                )}
              </div>
              <Form.List name="administrations">
                {(fields) => (
                  <div className="w-full">
                    {fields
                      .filter((f) => {
                        if (search) {
                          return formInstance
                            .getFieldValue(["administrations", f.name, "name"])
                            ?.toLowerCase()
                            ?.includes(search?.toLowerCase());
                        }
                        return f;
                      })
                      .map((field) => {
                        const isReviewed = formInstance.getFieldValue([
                          "administrations",
                          field.name,
                          "reviewed",
                        ]);
                        const isDisabled =
                          formInstance.getFieldValue([
                            "administrations",
                            field.name,
                            "category",
                          ])?.raw === DROUGHT_CATEGORY_VALUE.none ||
                          !formInstance.getFieldValue([
                            "administrations",
                            field.name,
                            "value",
                          ]) ||
                          isReviewed;
                        return (
                          <div
                            className={classNames(
                              "w-full flex flex-row flex-wrap items-center justify-between px-4 py-2 border-b border-neutral-200",
                              {
                                "bg-neutral-100": isReviewed,
                              }
                            )}
                            key={field.key}
                          >
                            <Space>
                              {!isCompleted && (
                                <Form.Item
                                  valuePropName="checked"
                                  name={[field.name, "checked"]}
                                >
                                  <Checkbox
                                    onClick={(e) =>
                                      onCheckAdm(
                                        e,
                                        formInstance.getFieldValue([
                                          "administrations",
                                          field.name,
                                          "administration_id",
                                        ])
                                      )
                                    }
                                    disabled={isDisabled}
                                  />
                                </Form.Item>
                              )}
                              <Button
                                onClick={() =>
                                  onOpen(
                                    formInstance.getFieldValue([
                                      "administrations",
                                      field.name,
                                    ])
                                  )
                                }
                                type="link"
                                // disabled={
                                //   formInstance.getFieldValue([
                                //     "administrations",
                                //     field.name,
                                //     "category",
                                //   ])?.raw === DROUGHT_CATEGORY_VALUE.none
                                // }
                              >
                                {formInstance.getFieldValue([
                                  "administrations",
                                  field.name,
                                  "name",
                                ])}
                              </Button>
                            </Space>
                            {/* {formInstance.getFieldValue([
                              "administrations",
                              field.name,
                              "category",
                            ])?.raw !== DROUGHT_CATEGORY_VALUE.none &&
                              !isCompleted && ( */}
                            <div>
                              <Tag color={isReviewed ? "success" : null}>
                                {isReviewed ? "Reviewed" : "Pending"}
                              </Tag>
                            </div>
                            {/* )} */}
                          </div>
                        );
                      })}
                  </div>
                )}
              </Form.List>
            </>
          );
        }}
      </Form>
    </div>
  );
};

export default ReviewList;
