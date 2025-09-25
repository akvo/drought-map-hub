"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Button, Form, Input, Typography, Select, Flex, Divider } from "antd";
import Link from "next/link";
import { setupApiFormData, storage } from "@/lib";
import { useAppContext, useAppDispatch } from "@/context/AppContextProvider";
import { useRouter } from "next/navigation";

const { useForm } = Form;
const { Title } = Typography;

const Step3Page = () => {
  const [loading, setLoading] = useState(false);
  const [organizations, setOrganizations] = useState([]);
  const [preloading, setPreloading] = useState(true);

  const [form] = useForm();
  const router = useRouter();
  const { appConfig } = useAppContext();
  const appDispatch = useAppDispatch();

  const loadAppConfig = useCallback(() => {
    if (!preloading) {
      return;
    }
    const appStorage = storage.get("APP_CONFIG");
    if (!appConfig?.name && appStorage?.name) {
      appDispatch({ type: "SET_APP_CONFIG", payload: appStorage });
      const orgs = appStorage?.organizations?.filter((o) => o?.is_twg) || [];
      setOrganizations(orgs);
    }
    if (appConfig?.organizations?.length && organizations.length === 0) {
      const orgs = appConfig?.organizations?.filter((o) => o?.is_twg) || [];
      setOrganizations(orgs);
    }
    setPreloading(false);
  }, [appConfig, appDispatch, organizations, preloading]);

  useEffect(() => {
    loadAppConfig();
  }, [loadAppConfig]);

  const onFinish = async (values) => {
    setLoading(true);
    try {
      const formData = new FormData();
      Object.entries(values).forEach(([key, value]) => {
        if (key === "reviewers" && Array.isArray(value)) {
          // Convert each reviewer object to Python dict string format expected by backend
          value.forEach((reviewer) => {
            // Convert to Python dict string format (single quotes, not JSON)
            const reviewerString = JSON.stringify(reviewer).replace(/"/g, "'");
            formData.append("reviewers", reviewerString);
          });
        } else {
          formData.append(key, value);
        }
      });
      await setupApiFormData("POST", "/user-setup", formData);
      router.push("/setup/complete");
    } catch (error) {
      console.error("Error submitting form:", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div className="w-full flex flex-col items-center mb-4">
        <p className="w-full max-w-3xl text-center text-md">
          Set up secure access for your team — empower decision-makers with the
          right permissions from day one.
        </p>
      </div>
      <Form
        form={form}
        layout="vertical"
        className="w-full flex flex-col items-center"
        onFinish={onFinish}
        initialValues={{ reviewers: [{}] }}
      >
        <div>
          <Title level={4}>Admin Creation</Title>
          <p className="text-md text-gray-600 mb-4">
            Create the primary administrator account (full system control).
          </p>
        </div>
        <div className="w-full max-w-3xl mb-6">
          <Form.Item
            label="Full Name"
            name="name"
            rules={[
              { required: true, message: "Please input the admin full name" },
            ]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            label="E-mail"
            name="email"
            rules={[
              { required: true, message: "Please input the admin e-mail" },
              { type: "email", message: "Please enter a valid e-mail address" },
            ]}
          >
            <Input />
          </Form.Item>
          <Form.Item
            label="Password"
            name="password"
            rules={[
              { required: true, message: "Please input the admin password" },
            ]}
          >
            <Input.Password />
          </Form.Item>
          <Form.Item
            label="Confirm Password"
            name="confirm_password"
            dependencies={["password"]}
            hasFeedback
            rules={[
              { required: true, message: "Please confirm the password" },
              ({ getFieldValue }) => ({
                validator(_, value) {
                  if (!value || getFieldValue("password") === value) {
                    return Promise.resolve();
                  }
                  return Promise.reject(
                    new Error("The two passwords do not match!"),
                  );
                },
              }),
            ]}
          >
            <Input.Password />
          </Form.Item>
        </div>
        <Divider>
          <Title level={4}>Add Reviewers</Title>
        </Divider>
        <p className="w-full max-w-3xl text-md text-gray-600 mb-4">
          Invite regional analysts or validators who will review drought alerts
          and data outputs.
        </p>
        <Form.List name="reviewers">
          {(fields, { add, remove }) => (
            <div className="w-full max-w-3xl mb-6 flex flex-col gap-4">
              {fields.map(({ key, name, ...restField }) => (
                <div key={key} className="p-4 border rounded-lg">
                  <div className="w-full text-right pb-4">
                    <Button onClick={() => remove(name)} type="dashed" danger>
                      Remove
                    </Button>
                  </div>
                  <Form.Item
                    {...restField}
                    name={[name, "name"]}
                    rules={[
                      { required: true, message: "Missing reviewer name" },
                    ]}
                  >
                    <Input placeholder="Reviewer Name" />
                  </Form.Item>
                  <Form.Item
                    {...restField}
                    name={[name, "email"]}
                    rules={[
                      { required: true, message: "Missing reviewer email" },
                      { type: "email", message: "Invalid email" },
                    ]}
                    style={{ flex: 1, marginRight: 8 }}
                  >
                    <Input placeholder="Reviewer Email" />
                  </Form.Item>
                  <Form.Item
                    {...restField}
                    name={[name, "organization_id"]}
                    rules={[{ required: true, message: "Select organization" }]}
                  >
                    <Select placeholder="Select Organization">
                      {organizations.map((org) => (
                        <Select.Option key={org.id} value={org.id}>
                          {org.name}
                        </Select.Option>
                      ))}
                    </Select>
                  </Form.Item>
                </div>
              ))}
              <Form.Item>
                <Button onClick={() => add()}>Add Reviewer</Button>
              </Form.Item>
            </div>
          )}
        </Form.List>
        <Divider />
        <Flex align="center" justify="space-between" className="w-full">
          <Link href="/setup/step-2">
            <Button type="default">Previous</Button>
          </Link>
          <Button type="primary" htmlType="submit" loading={loading}>
            Next
          </Button>
        </Flex>
      </Form>
    </div>
  );
};

export default Step3Page;
