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
