"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Button, Form, Input, Typography, Select } from "antd";
import { setupApiFormData, storage } from "@/lib";
import { useAppContext, useAppDispatch } from "@/context/AppContextProvider";
import { useRouter } from "next/navigation";

const { useForm } = Form;
const { Title } = Typography;

const Step3Page = () => {
  const [loading, setLoading] = useState(false);
  const [organizations, setOrganizations] = useState([]);

  const [form] = useForm();
  const router = useRouter();
  const { appConfig } = useAppContext();
  const appDispatch = useAppDispatch();

  const loadAppConfig = useCallback(() => {
    const appStorage = storage.get("APP_CONFIG");
    if (!appConfig?.name && appStorage?.name) {
      appDispatch({ type: "SET_APP_CONFIG", payload: appStorage });
      const orgs = appStorage?.organizations?.filter((o) => o?.is_twg) || [];
      setOrganizations(orgs);
    }
  }, [appConfig, appDispatch]);

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
      <h1>Step 3: Users Setup</h1>
      <p>This is the third step of the installation process.</p>
      <Form
        form={form}
        layout="vertical"
        onFinish={onFinish}
        initialValues={{ reviewers: [{}] }}
      >
        <Title level={4}>Admin User</Title>
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
        <Title level={4}>Reviewers</Title>
        <Form.List name="reviewers">
          {(fields, { add, remove }) => (
            <>
              {fields.map(({ key, name, ...restField }) => (
                <div key={key}>
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
                  <Button onClick={() => remove(name)}>Remove</Button>
                </div>
              ))}
              <Form.Item>
                <Button type="dashed" onClick={() => add()}>
                  Add Reviewer
                </Button>
              </Form.Item>
            </>
          )}
        </Form.List>
        <Button type="primary" htmlType="submit" loading={loading}>
          Next
        </Button>
      </Form>
    </div>
  );
};

export default Step3Page;
