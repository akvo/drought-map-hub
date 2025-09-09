"use client";

import { useState } from "react";
import {
  Button,
  Checkbox,
  DatePicker,
  Flex,
  Form,
  Input,
  List,
  message,
  Space,
  Tooltip,
  Typography,
} from "antd";
import { SubmitButton } from "../Buttons";
import TinyEditor from "../TinyEditor";
import dayjs from "dayjs";
import { useRouter } from "next/navigation";
import { api } from "@/lib";
import { CREATE_PUBLICATION_MAIL } from "@/static/config";
import { VerifiedIcon } from "../Icons";

const { Text, Title } = Typography;
const { useForm } = Form;
const { Search } = Input;

const PublicationForm = ({ geonode, reviewer, reviewerList = [] }) => {
  const [search, setSearch] = useState(null);
  const [searching, setSearching] = useState(false);
  const [loading, setLoading] = useState(false);
  const [loadMore, setLoadMore] = useState(false);
  const [revPage, setRevPage] = useState(1);
  const [errors, setErrors] = useState([]);
  const [checkItems, setCheckItems] = useState([]);
  const [form] = useForm();
  const router = useRouter();

  const loadMoreReviewers =
    reviewer?.total_page > 1 && revPage < reviewer?.total_page;

  const onLoadReviewers = async (page) => {
    setLoadMore(true);
    try {
      const apiURL = search
        ? `/admin/reviewers?page=${page}&search=${search}`
        : `/admin/reviewers?page=${page}`;
      const { data: newReviewerList, current: currPage } = await api(
        "GET",
        apiURL
      );
      const _reviewers = [
        ...form.getFieldValue("reviewers"),
        ...newReviewerList,
      ].map((r) => ({
        ...r,
        checked: checkItems.includes(r?.id),
      }));
      setRevPage(currPage);
      form.setFieldValue("reviewers", _reviewers);
      setLoadMore(false);
    } catch (err) {
      console.error(err);
      setLoadMore(false);
    }
  };

  const onFinish = async (values) => {
    setLoading(true);
    try {
      const payload = {
        ...values,
        cdi_geonode_id: geonode?.pk,
        due_date: dayjs(values?.due_date).format("YYYY-MM-DD"),
        year_month: dayjs(values?.year_month).format("YYYY-MM-DD"),
        initial_values: [],
        reviewers: values?.reviewers
          ?.filter((r) => checkItems.includes(r.id))
          ?.map((r) => r?.id),
        download_url: geonode?.download_url,
      };
      const res = await api("POST", "/admin/publications", payload);
      if (res?.id) {
        setCheckItems([]);
        message.success("New publication successfully created");
        router.push("/publications");
      } else {
        setLoading(false);
        setErrors(res);
      }
    } catch (err) {
      console.error(err);
      message.error("[ADM-P-1] Please report this issue along with the code.");
      setLoading(false);
    }
  };

  const onSearch = async (value) => {
    setSearch(value);
    setSearching(true);
    try {
      setTimeout(async () => {
        const apiURL = value
          ? `/admin/reviewers?page=1&search=${value}`
          : "/admin/reviewers?page=1";
        const { data: _reviewers } = await api("GET", apiURL);
        form.setFieldValue(
          "reviewers",
          _reviewers.map((r) => ({
            ...r,
            checked: checkItems.includes(r?.id),
          }))
        );
        setSearching(false);
      }, 300);
    } catch (err) {
      console.error(err);
      setSearching(false);
    }
  };

  const onCheck = (isChecked, id) => {
    if (isChecked && !checkItems.includes(id)) {
      setCheckItems([...checkItems, id]);
    }

    if (!isChecked) {
      setCheckItems(checkItems.filter((item) => item !== id));
    }
  };

  return (
    <Form
      form={form}
      initialValues={{
        ...geonode,
        reviewers: reviewerList,
        subject: `${CREATE_PUBLICATION_MAIL?.subject} ${dayjs(
          geonode?.year_month
        ).format("YYYY-MM")}`,
        year_month: dayjs(geonode?.year_month),
        message: CREATE_PUBLICATION_MAIL?.message,
      }}
      onFinish={onFinish}
      layout="vertical"
    >
      {(_, formInstance) => (
        <div className="w-full flex flex-row items-start gap-8">
          <div className="w-full lg:w-1/3 xl:w-1/4 mb-4">
            <Form.List
              name="reviewers"
              className="mb-6"
              rules={[
                {
                  validator: async (_, values) => {
                    const selectedItems = values?.filter((v) => v?.checked);
                    if (!selectedItems?.length) {
                      return Promise.reject(
                        new Error("Please select at least one reviewer.")
                      );
                    }
                  },
                },
              ]}
            >
              {(fields) => (
                <List
                  header={
                    <div className="w-full text-right">
                      <Search
                        onChange={(e) => onSearch(e.target.value)}
                        onClear={() => onSearch(null)}
                        placeholder="Search Reviewer"
                        className="w-full"
                        allowClear
                      />
                    </div>
                  }
                  footer={
                    loadMoreReviewers ? (
                      <Button
                        onClick={() => {
                          onLoadReviewers(revPage + 1);
                        }}
                        loading={loadMore}
                        block
                      >
                        Load more
                      </Button>
                    ) : null
                  }
                  dataSource={fields}
                  renderItem={(field) => (
                    <List.Item>
                      <Space align="baseline">
                        <Form.Item
                          valuePropName="checked"
                          name={[field.name, "checked"]}
                        >
                          <Checkbox
                            onChange={(e) =>
                              onCheck(
                                e.target.checked,
                                formInstance.getFieldValue([
                                  "reviewers",
                                  field.name,
                                  "id",
                                ])
                              )
                            }
                          />
                        </Form.Item>
                        <Flex gap={0} vertical>
                          <Text>
                            {formInstance.getFieldValue([
                              "reviewers",
                              field.name,
                              "name",
                            ])}
                          </Text>
                          <Flex gap={2}>
                            {`(`}
                            {formInstance.getFieldValue([
                              "reviewers",
                              field.name,
                              "email",
                            ])}
                            {formInstance.getFieldValue([
                              "reviewers",
                              field.name,
                              "email_verified",
                            ]) && (
                              <Tooltip title="Email has been verified">
                                <span className="text-primary">
                                  <VerifiedIcon />
                                </span>
                              </Tooltip>
                            )}
                            {`)`}
                          </Flex>
                          <Text type="secondary">
                            {formInstance.getFieldValue([
                              "reviewers",
                              field.name,
                              "technical_working_group",
                            ])}
                          </Text>
                        </Flex>
                      </Space>
                    </List.Item>
                  )}
                  loading={searching}
                />
              )}
            </Form.List>
          </div>
          <div className="w-full lg:w-2/3 xl:w-3/4">
            <Form.Item
              label="Publication Date"
              name="year_month"
              rules={[
                {
                  required: true,
                },
              ]}
            >
              <DatePicker
                format={{
                  format: "YYYY-MM",
                  type: "mask",
                }}
                picker="month"
              />
            </Form.Item>
            <Form.Item
              label="Review Deadline"
              name="due_date"
              rules={[
                {
                  required: true,
                },
              ]}
              help={errors?.due_date?.join(", ")}
              validateStatus={errors?.due_date ? "error" : null}
            >
              <DatePicker
                format={{
                  format: "YYYY-MM-DD",
                  type: "mask",
                }}
              />
            </Form.Item>
            <Form.Item
              label="Subject"
              name="subject"
              rules={[
                {
                  required: true,
                },
              ]}
            >
              <Input />
            </Form.Item>
            <Form.Item
              label="Message"
              name="message"
              rules={[
                {
                  required: true,
                },
              ]}
            >
              <TinyEditor
                value={formInstance.getFieldValue("message")}
                setValue={(v) => formInstance.setFieldValue("message", v)}
                height={300}
              />
            </Form.Item>
            <Flex align="center" justify="end" className="pt-6">
              <SubmitButton form={form} loading={loading} size="large">
                Create
              </SubmitButton>
            </Flex>
          </div>
          {/* <Divider orientation="left">Select Reviewers</Divider> */}
        </div>
      )}
    </Form>
  );
};

export default PublicationForm;
