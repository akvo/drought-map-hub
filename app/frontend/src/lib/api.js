"use server";
import { getSession } from "./auth";

export const api = (method, url, payload = {}) =>
  new Promise(async (resolve, reject) => {
    const _session = await getSession();
    const headers = {
      "Content-Type": "application/json",
    };
    if (_session) {
      const { token: authToken } = _session;
      headers["Authorization"] = `Bearer ${authToken}`;
    }
    const fetchProps = {
      method,
      headers,
    };
    if (typeof payload === "object" && Object.keys(payload).length) {
      fetchProps["body"] = JSON.stringify(payload);
    }
    fetch(`${process.env.WEBDOMAIN}/api/v1${url}`, fetchProps)
      .then((res) => res.json())
      .then((res) => resolve(res))
      .catch((err) => reject(err));
  });

// Setup API call with form data (for file uploads)
export const setupApiFormData = async (method, url, formData) => {
  const headers = {
    "X-Setup-Secret": process.env.SETUP_SECRET_KEY,
  };

  const fetchProps = {
    method,
    headers,
    body: formData,
  };

  try {
    const response = await fetch(
      `${process.env.WEBDOMAIN}/api/v1${url}`,
      fetchProps,
    );
    if (!response.ok) {
      throw new Error(await response.text());
    }
    return await response.json();
  } catch (error) {
    throw error;
  }
};
