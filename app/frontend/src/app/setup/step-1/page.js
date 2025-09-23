"use client";

import React, { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Form, Input, Button, Space, Upload, Checkbox } from "antd";
import { setupApiFormData } from "@/lib/api";
import { storage } from "@/lib";
import { useAppDispatch } from "@/context/AppContextProvider";

const { useForm } = Form;

const Step1Page = () => {
  const [loading, setLoading] = useState(false);
  const [preloading, setPreloading] = useState(true);
  const [form] = useForm();
  const router = useRouter();

  const appDispatch = useAppDispatch();

  const onFinish = async (values) => {
    setLoading(true);
    try {
      // Process the form data to handle file uploads properly
      const formData = new FormData();
      // Handle simple fields
      if (values.name) {
        formData.append("name", values.name);
      }
      // Handle file upload for geojson_file
      if (values.geojson_file && values.geojson_file.fileList) {
        const file = values.geojson_file.fileList[0];
        if (file?.originFileObj) {
          formData.append("geojson_file", file.originFileObj);
          // store GeoJSON content in localStorage for later use
          const reader = new FileReader();
          reader.onload = (e) => {
            try {
              const geojsonContent = JSON.parse(e.target.result);
              console.log("GeoJSON content loaded:", geojsonContent);
              // Store in localStorage
              storage.set("topojson", geojsonContent);
              // Set geoData in context
              appDispatch({
                type: "SET_SETUP_GEODATA",
                payload: geojsonContent,
              });
            } catch (err) {
              console.error("Error parsing GeoJSON file:", err);
            }
          };
          reader.readAsText(file.originFileObj);
        }
      }
      // Handle organizations array
      if (values.organizations && values.organizations.length > 0) {
        values.organizations.forEach((org, index) => {
          if (org.name)
            formData.append(`organizations[${index}][name]`, org.name);
          if (org.website)
            formData.append(`organizations[${index}][website]`, org.website);
          if (org.is_twg) {
            formData.append(`organizations[${index}][is_twg]`, "true");
          }
          if (org.is_collaborator) {
            formData.append(`organizations[${index}][is_collaborator]`, "true");
          }
          // Handle logo file
          if (org.logo && org.logo.fileList) {
            const logoFile = org.logo.fileList[0];
            if (logoFile?.originFileObj) {
              formData.append(
                `organizations[${index}][logo]`,
                logoFile.originFileObj,
              );
            }
          }
        });
      }
      // Use the setupApiFormData function instead of direct fetch
      const appStorage = storage.get("APP_CONFIG");
      if (appStorage?.uuid) {
        const data = await setupApiFormData(
          "PUT",
          `/manage-setup/${appStorage.uuid}`,
          formData,
        );
        // Update data into localStorage
        storage.set("APP_CONFIG", data);
        // Update appStorage in context
        appDispatch({
          type: "SET_APP_CONFIG",
          payload: data,
        });
        // Proceed to next step or show success message
        router.push("/setup/step-2");
        return;
      }
      const data = await setupApiFormData("POST", "/setup", formData);
      // Store data into localStorage
      storage.set("APP_CONFIG", data);
      // Store appStorage in context
      appDispatch({
        type: "SET_APP_CONFIG",
        payload: data,
      });
      // Proceed to next step or show success message
      router.push("/setup/step-2");
    } catch (error) {
      console.error("Error:", error);
    } finally {
      setLoading(false);
    }
  };

  const onFirstLoad = useCallback(() => {
    if (!preloading) {
      return;
    }
    const appStorage = storage.get("APP_CONFIG");

    if (appStorage) {
      appDispatch({
        type: "SET_APP_CONFIG",
        payload: appStorage,
      });
      // If appStorage exists, set form values
      form.setFieldsValue({
        name: appStorage.name || "",
        // Note: File inputs cannot be set programmatically for security reasons
        organizations: appStorage.organizations?.map((org) => ({
          name: org.name || "",
          website: org.website || "",
          is_twg: org.is_twg || false,
          is_collaborator: org.is_collaborator || false,
        })) || [{}],
      });
    }
    setPreloading(false);
  }, [form, preloading, appDispatch]);

  useEffect(() => {
    onFirstLoad();
  }, [onFirstLoad]);

  return (
    <div>
      <h1>Step 1: Application Setup</h1>
      <p>This is the first step of the installation process.</p>
      <Form
        name="step1"
        layout="vertical"
        onFinish={onFinish}
        form={form}
        initialValues={{ organizations: [{}] }}
      >
        <Form.Item
          label="Application Name"
          name="name"
          rules={[
            { required: true, message: "Please input the application name" },
          ]}
        >
          <Input placeholder="Application Name" />
        </Form.Item>
        <Form.Item
          label="Country Boundary (GeoJSON)"
          name="geojson_file"
          rules={[
            { required: true, message: "Please upload the country boundary" },
          ]}
        >
          <Upload.Dragger
            multiple={false}
            accept="application/geo+json,application/json,.geojson,.json"
            beforeUpload={(file) => {
              // Prevent automatic upload
              return false;
            }}
            maxCount={1}
          >
            <p className="ant-upload-drag-icon">
              <span>📁</span>
            </p>
            <p className="ant-upload-text">
              Click or drag file to this area to upload
            </p>
            <p className="ant-upload-hint">
              Support for a single GeoJSON file.
            </p>
          </Upload.Dragger>
        </Form.Item>
        <Form.List name="organizations">
          {(fields, { add, remove }) => (
            <>
              {fields.map(({ key, name, ...restField }) => (
                // image upload input
                <div key={key}>
                  <Form.Item
                    {...restField}
                    label="Organization Logo"
                    name={[name, "logo"]}
                    rules={[
                      { required: true, message: "Please upload a logo" },
                    ]}
                  >
                    <Upload
                      accept="image/*"
                      beforeUpload={() => false}
                      maxCount={1}
                      listType="picture-card"
                    >
                      <div>
                        <span>📷</span>
                        <div style={{ marginTop: 8 }}>Upload</div>
                      </div>
                    </Upload>
                  </Form.Item>
                  <Form.Item
                    {...restField}
                    name={[name, "name"]}
                    rules={[
                      {
                        required: true,
                        message: "Please input the organization name",
                      },
                    ]}
                  >
                    <Input placeholder="Organization Name" />
                  </Form.Item>
                  <Form.Item
                    {...restField}
                    name={[name, "website"]}
                    rules={[
                      {
                        required: true,
                        message: "Please input the organization website",
                      },
                      {
                        type: "url",
                        message: "Please enter a valid URL",
                      },
                    ]}
                  >
                    <Input placeholder="Organization Website" />
                  </Form.Item>
                  <Form.Item
                    {...restField}
                    name={[name, "is_twg"]}
                    valuePropName="checked"
                  >
                    <Checkbox>Is Technical Working Group</Checkbox>
                  </Form.Item>
                  <Form.Item
                    {...restField}
                    name={[name, "is_collaborator"]}
                    valuePropName="checked"
                  >
                    <Checkbox>Is Collaborator</Checkbox>
                  </Form.Item>
                  <Button type="button" onClick={() => remove(name)} danger>
                    Remove
                  </Button>
                </div>
              ))}
              <Form.Item>
                <Button onClick={() => add()}>Add Logo</Button>
              </Form.Item>
            </>
          )}
        </Form.List>
        <Space>
          <Button type="primary" htmlType="submit" loading={loading}>
            Next
          </Button>
        </Space>
      </Form>
    </div>
  );
};

export default Step1Page;
