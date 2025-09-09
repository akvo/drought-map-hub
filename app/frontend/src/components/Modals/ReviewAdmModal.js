"use client";

import { useAppContext, useAppDispatch } from "@/context/AppContextProvider";
import {
  Modal,
  Form,
  Flex,
  Input,
  Select,
  Typography,
  Tag,
  message,
  Button,
} from "antd";

import {
  DROUGHT_CATEGORY,
  DROUGHT_CATEGORY_LABEL,
  DROUGHT_CATEGORY_VALUE,
} from "@/static/config";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib";

const { TextArea } = Input;
const { useForm } = Form;
const { Title, Text } = Typography;

const ReviewAdmModal = ({ review }) => {
  const [showSuggestion, setShowSuggestion] = useState(false);
  const [comment, setComment] = useState("");
  const { activeAdm } = useAppContext();
  const appDispatch = useAppDispatch();
  const [form] = useForm();
  const router = useRouter();

  const isModalOpen = useMemo(() => {
    return activeAdm?.administration_id ? true : false;
  }, [activeAdm]);

  const onFinish = async (values) => {
    try {
      const map_values =
        review?.suggestion_values || review?.publication?.initial_values;
      const suggestion_values = map_values?.map((m) => {
        if (activeAdm?.administration_id === m?.administration_id) {
          // Fix: properly handle the category value to ensure it's not null
          const categoryValue = showSuggestion
            ? values.suggestedCategory
            : activeAdm?.category?.raw || 0;

          return {
            ...m,
            category: categoryValue, // Use the properly calculated category value
            comment: values.comment || comment, // Ensure comment is captured
            reviewed: true,
          };
        }
        return m;
      });
      await api("PUT", `/reviewer/review/${review?.id}`, {
        suggestion_values,
      });
      appDispatch({
        type: "REFRESH_MAP_TRUE",
      });
      onClose();
      setTimeout(() => {
        appDispatch({
          type: "REFRESH_MAP_FALSE",
        });
      }, 500);
      router.refresh();
    } catch (err) {
      message.error("An error occurred, please report this issue!");
      console.error(err);
    }
  };

  const onClose = () => {
    setShowSuggestion(false);
    form.resetFields();
    appDispatch({
      type: "REMOVE_ACTIVE_ADM",
    });
  };

  const updateForm = useCallback(() => {
    if (
      activeAdm?.administration_id &&
      activeAdm?.comment !== form.getFieldValue("comment")
    ) {
      // Ensure we're setting the right field for category
      if (activeAdm?.reviewed) {
        form.setFieldValue("computedCategory", activeAdm.category?.reviewed);
      } else {
        form.setFieldValue("computedCategory", activeAdm.category?.raw);
        if (showSuggestion) {
          form.setFieldValue("suggestedCategory", activeAdm.category?.reviewed);
        }
      }
      form.setFieldValue("comment", activeAdm.comment);
      if (activeAdm.comment) {
        setComment(activeAdm.comment);
      }
    }
    if (!activeAdm?.category?.raw && !showSuggestion) {
      setShowSuggestion(true);
    }
  }, [activeAdm, form, showSuggestion]);

  useEffect(() => {
    updateForm();
  }, [updateForm]);

  useEffect(() => {
    if (form) {
      form.validateFields(["comment", "suggestedCategory"]);
    }
  }, [showSuggestion, form]);

  return (
    <Form form={form} onFinish={onFinish}>
      <Modal
        title={"INKHUNDLA STATUS"}
        open={isModalOpen}
        onCancel={onClose}
        maskClosable={false}
        width={768}
        footer={
          <Flex
            align="center"
            justify={review?.is_completed ? "end" : "space-between"}
          >
            {!review?.is_completed && (
              <Button
                key="close"
                type="primary"
                onClick={() => {
                  if (activeAdm?.reviewed) {
                    setShowSuggestion(true);
                    appDispatch({
                      type: "UPDATE_ACTIVE_ADM",
                      payload: {
                        reviewed: false,
                      },
                    });
                  } else {
                    setShowSuggestion(!showSuggestion);
                  }
                }}
                ghost
              >
                {activeAdm?.reviewed
                  ? "Edit"
                  : showSuggestion
                  ? "Cancel"
                  : "Suggest new value"}
              </Button>
            )}

            <Button
              key="submit"
              type="primary"
              onClick={() => {
                if (!activeAdm?.reviewed) {
                  form
                    .validateFields()
                    .then(() => {
                      form.submit();
                    })
                    .catch((error) => {
                      console.log("Validation failed:", error);
                    });
                } else {
                  onClose();
                }
              }}
              disabled={
                (showSuggestion && comment?.trim()?.length === 0) ||
                (activeAdm?.category?.raw === DROUGHT_CATEGORY_VALUE.none &&
                  !showSuggestion) ||
                (!activeAdm?.category?.raw &&
                  !activeAdm?.category?.reviewed &&
                  !showSuggestion)
              }
            >
              {activeAdm?.reviewed
                ? "OK"
                : showSuggestion
                ? "Suggest New Value"
                : "Approve Computed Value"}
            </Button>
          </Flex>
        }
        destroyOnClose
      >
        <div className="w-full space-y-3">
          <Flex align="center" justify="space-between">
            <Title level={4} className="pt-2">
              {activeAdm?.name}
            </Title>

            <Tag color={activeAdm?.reviewed ? "green" : null}>
              {activeAdm?.reviewed ? "Reviewed" : "Not Reviewed"}
            </Tag>
          </Flex>

          {activeAdm?.reviewed ? (
            <Form.Item label="Computed Value" name="computedCategory">
              <Text strong>
                {DROUGHT_CATEGORY_LABEL?.[activeAdm.category?.reviewed]}
              </Text>
            </Form.Item>
          ) : (
            <Flex align="center" justify="space-between" className="w-full">
              <Form.Item label="Computed Value" name="computedCategory">
                <Text strong>
                  {DROUGHT_CATEGORY_LABEL?.[activeAdm?.category?.raw]}
                </Text>
              </Form.Item>
              {showSuggestion && (
                <Form.Item
                  label="Suggested Value"
                  name="suggestedCategory"
                  className="w-1/2"
                  rules={[
                    {
                      required: true,
                      message: "Please select a drought category",
                    },
                  ]}
                >
                  <Select
                    options={DROUGHT_CATEGORY.slice(
                      0,
                      DROUGHT_CATEGORY.length - 1
                    )}
                    placeholder="Select Drought category"
                    disabled={activeAdm?.reviewed}
                    allowClear={false}
                  />
                </Form.Item>
              )}
            </Flex>
          )}
          <Form.Item
            name="comment"
            rules={[
              {
                required: showSuggestion,
                message: "Please provide a comment",
              },
            ]}
          >
            <TextArea
              placeholder={activeAdm?.reviewed ? "" : "Add a comment"}
              disabled={review?.is_completed || activeAdm?.reviewed}
              value={comment}
              onChange={(e) => {
                setComment(e.target.value);
                form.setFieldsValue({ comment: e.target.value });
              }}
            />
          </Form.Item>
        </div>
      </Modal>
    </Form>
  );
};

export default ReviewAdmModal;
