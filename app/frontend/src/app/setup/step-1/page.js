"use client";

import React, { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Form,
  Input,
  Button,
  Space,
  Upload,
  Checkbox,
  Select,
  Divider,
  Table,
  Radio,
  Flex,
  Typography,
} from "antd";
import { api, setupApiFormData } from "@/lib/api";
import { indexedDBStorage, storage } from "@/lib";
import { calculateGeoJSONCenter, extractGeoJSONProperties } from "@/lib/geo";
import { useAppContext, useAppDispatch } from "@/context/AppContextProvider";

const { useForm } = Form;
const { Title } = Typography;

const Step1Page = () => {
  const [loading, setLoading] = useState(false);
  const [preloading, setPreloading] = useState(true);
  const [countries, setCountries] = useState([]);
  const [geoProperties, setGeoProperties] = useState([]);
  const [geoPropIsLoaded, setGeoPropIsLoaded] = useState(false);
  const [db, setDB] = useState(null);
  const [admNameSelection, setAdmNameSelection] = useState(null);
  const [mapCenter, setMapCenter] = useState(null);
  const [form] = useForm();
  const router = useRouter();

  const { setupGeoData } = useAppContext();
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
      if (values.country) {
        formData.append("country", values.country);
      }
      // Handle file upload for geojson_file
      if (values.geojson_file && values.geojson_file?.[0]) {
        const file = values.geojson_file[0];
        if (file?.originFileObj) {
          formData.append("geojson_file", file.originFileObj);
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
      if (admNameSelection) {
        formData.append("map_name_key", admNameSelection);
      }
      if (mapCenter) {
        formData.append("map_center", JSON.stringify(mapCenter));
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

  const onFirstLoad = useCallback(async () => {
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

    const indexDB = await indexedDBStorage.dbPromise();
    if (indexDB) {
      setDB(indexDB);
      // Load existing GeoJSON data if available
      try {
        const geoStorage = await indexedDBStorage.get(indexDB, "APP_GEOJSON");
        if (geoStorage) {
          appDispatch({ type: "SET_SETUP_GEODATA", payload: geoStorage });
          // Recalculate center from stored GeoJSON
          const center = calculateGeoJSONCenter(geoStorage);
          if (center) {
            setMapCenter(center);
          }
        }
      } catch (error) {
        console.error("Error loading stored GeoJSON data:", error);
      }
    }
    setPreloading(false);
  }, [form, preloading, appDispatch]);

  const fetchCountries = useCallback(async () => {
    try {
      const _countries = await api("GET", "/countries");
      setCountries(_countries);
    } catch (error) {
      console.error("Error fetching countries:", error);
    }
  }, []);
  const onSetGeoProperties = useCallback(() => {
    if (setupGeoData && !geoPropIsLoaded) {
      const propArray = extractGeoJSONProperties(setupGeoData);
      if (propArray.length > 0) {
        setGeoProperties(propArray);
        setGeoPropIsLoaded(true);
      }
    }
  }, [setupGeoData, geoPropIsLoaded]);

  const getTransposedTableData = useCallback(() => {
    if (!geoProperties || geoProperties.length === 0) return [];

    // Create the transposed data structure
    const transposedData = [
      {
        key: "values",
        property: "Value",
        ...geoProperties.reduce((acc, prop, index) => {
          acc[`field_${index}`] = prop.value;
          return acc;
        }, {}),
      },
      {
        key: "adm_name",
        property: "Which is ADM Name?",
        ...geoProperties.reduce((acc, prop, index) => {
          acc[`field_${index}`] = (
            <Radio
              checked={admNameSelection === prop.name}
              onChange={() => setAdmNameSelection(prop.name)}
            />
          );
          return acc;
        }, {}),
      },
    ];

    return transposedData;
  }, [geoProperties, admNameSelection]);

  const getTransposedTableColumns = useCallback(() => {
    if (!geoProperties || geoProperties.length === 0) return [];

    const columns = [
      {
        title: "Property",
        dataIndex: "property",
        key: "property",
        fixed: "left",
        width: 150,
      },
    ];

    // Add columns for each field
    geoProperties.forEach((prop, index) => {
      columns.push({
        title: prop.name,
        dataIndex: `field_${index}`,
        key: `field_${index}`,
        align: "center",
      });
    });

    return columns;
  }, [geoProperties]);

  useEffect(() => {
    onSetGeoProperties();
  }, [onSetGeoProperties]);

  useEffect(() => {
    onFirstLoad();
  }, [onFirstLoad]);

  useEffect(() => {
    fetchCountries();
  }, [fetchCountries]);

  return (
    <div>
      <div className="w-full flex flex-col items-center mb-4">
        <p className="w-full max-w-3xl text-center text-md">
          Configure and customize your{" "}
          <strong>Advanced Drought Monitoring Platform</strong> — designed for
          real-time insights, early warning alerts, and data-driven decision
          making.
        </p>
      </div>
      <Form
        name="step1"
        layout="vertical"
        className="w-full flex flex-col items-center"
        onFinish={onFinish}
        form={form}
        initialValues={{ organizations: [{}] }}
      >
        <div className="w-full max-w-3xl mb-6">
          <Form.Item
            label="Application Name"
            name="name"
            help={
              "The public-facing name of your drought monitoring dashboard."
            }
            rules={[
              { required: true, message: "Please input the application name" },
            ]}
          >
            <Input placeholder="Application Name" />
          </Form.Item>
          <Form.Item
            label="Country"
            name="country"
            help="Select the primary country for your drought monitoring operations."
            rules={[{ required: true, message: "Please input the country" }]}
          >
            <Select placeholder="Select Country" showSearch>
              {countries?.map((country) => (
                <Select.Option key={country?.alpha_2} value={country?.name}>
                  {country?.name}
                </Select.Option>
              ))}
            </Select>
          </Form.Item>
          <Form.Item
            label="Country Boundary (GeoJSON)"
            name="geojson_file"
            valuePropName="fileList"
            help="Define your operational area by uploading your country’s geographic boundary."
            extra={
              <Space>
                <i>Don’t have GeoJSON?</i>
                <span>
                  Use{" "}
                  <a
                    href="https://gadm.org/download_country.html"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <strong>gadm.org</strong>
                  </a>{" "}
                  to get the GeoJSON for administration level-2.
                </span>
              </Space>
            }
            getValueFromEvent={(e) => (Array.isArray(e) ? e : e && e.fileList)}
            rules={[
              { required: true, message: "Please upload the country boundary" },
            ]}
          >
            <Upload.Dragger
              multiple={false}
              accept="application/geo+json,application/json,.geojson,.json"
              beforeUpload={(file) => {
                // Validate file type
                const isGeoJson =
                  file.type === "application/geo+json" ||
                  file.type === "application/json";
                if (!isGeoJson) {
                  form.setFields([
                    {
                      name: "geojson_file",
                      errors: ["You can only upload GeoJSON files"],
                    },
                  ]);
                  return Upload.LIST_IGNORE;
                }
                // Prevent automatic upload
                return false;
              }}
              onChange={(info) => {
                // Store GeoJSON content in localStorage for later use
                if (info.file) {
                  const file = info.file;
                  const reader = new FileReader();
                  reader.onload = (e) => {
                    try {
                      const geojsonContent = JSON.parse(e.target.result);

                      // Calculate the center of the GeoJSON
                      const center = calculateGeoJSONCenter(geojsonContent);
                      setMapCenter(center); // Update state

                      // Store in indexedDB
                      if (db) {
                        indexedDBStorage.set(db, "APP_GEOJSON", geojsonContent);
                        setGeoPropIsLoaded(false); // Reset to re-extract properties
                        // Reset radio selections when new file is uploaded
                        setAdmNameSelection(null);
                      }
                      // Set geoData in context
                      appDispatch({
                        type: "SET_SETUP_GEODATA",
                        payload: geojsonContent,
                      });
                    } catch (err) {
                      console.error("Error parsing GeoJSON file:", err);
                    }
                  };
                  reader.readAsText(file);
                }
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
          {geoProperties.length > 0 && (
            <div style={{ marginBottom: 24 }}>
              <h3>GeoJSON Properties Configuration</h3>
              <Table
                dataSource={getTransposedTableData()}
                columns={getTransposedTableColumns()}
                pagination={false}
                scroll={{ x: "max-content" }}
                bordered
                size="small"
              />
              {admNameSelection && (
                <div style={{ marginTop: 16 }}>
                  <p>
                    <strong>Selected ADM Name:</strong>{" "}
                    {admNameSelection || "None"}
                  </p>
                </div>
              )}
            </div>
          )}
          {mapCenter && (
            <div style={{ marginBottom: 24 }}>
              <h3>Map Center (Calculated from GeoJSON)</h3>
              <div className="p-3 bg-blue-50 border border-blue-200 rounded">
                <p>
                  <strong>Latitude:</strong> {mapCenter.lat.toFixed(6)}°
                </p>
                <p>
                  <strong>Longitude:</strong> {mapCenter.lng.toFixed(6)}°
                </p>
                <p className="text-sm text-gray-600 mt-2">
                  <em>
                    This center point is automatically calculated from your
                    uploaded GeoJSON boundary.
                  </em>
                </p>
              </div>
            </div>
          )}
        </div>
        <Divider>
          <Title level={4}>Organizations</Title>
        </Divider>
        <p className="text-sm">
          Personalize your platform with your organization’s logo (PNG
          recommended, max 1MB per file).
        </p>
        <Form.List name="organizations">
          {(fields, { add, remove }) => (
            <div className="w-full max-w-3xl mb-6 flex flex-col gap-4">
              {fields.map(({ key, name, ...restField }) => (
                // image upload input
                <div key={key} className="p-4 border rounded-lg">
                  <Flex justify="space-between">
                    <Form.Item
                      {...restField}
                      label="Organization Logo"
                      name={[name, "logo"]}
                      valuePropName="fileList"
                      getValueFromEvent={(e) =>
                        Array.isArray(e) ? e : e && e.fileList
                      }
                      help="Upload the logo of the organization."
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
                    <span>
                      <Button onClick={() => remove(name)} type="dashed" danger>
                        Remove
                      </Button>
                    </span>
                  </Flex>
                  <Form.Item
                    {...restField}
                    name={[name, "name"]}
                    label="Organization Name"
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
                    label="Organization Website"
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
                    <Input placeholder="Organization Website" type="url" />
                  </Form.Item>
                  <Form.Item
                    {...restField}
                    name={[name, "is_twg"]}
                    help="This organization is part of the Technical Working Group as a Reviewer."
                    valuePropName="checked"
                  >
                    <Checkbox>Is Technical Working Group</Checkbox>
                  </Form.Item>
                  <Form.Item
                    {...restField}
                    name={[name, "is_collaborator"]}
                    help="This organization will be listed as a collaborator on the platform."
                    valuePropName="checked"
                  >
                    <Checkbox>Is Collaborator</Checkbox>
                  </Form.Item>
                </div>
              ))}
              <Form.Item>
                <Button onClick={() => add()}>Add Logo</Button>
              </Form.Item>
            </div>
          )}
        </Form.List>
        <Divider />
        <Flex justify="end" className="w-full">
          <Button type="primary" htmlType="submit" loading={loading}>
            Next
          </Button>
        </Flex>
      </Form>
    </div>
  );
};

export default Step1Page;
