"use server";

import { cookies } from "next/headers";

export const getAppConfig = async () => {
  const appConfigCookie = cookies().get("appConfig")?.value || "{}";
  try {
    return JSON.parse(appConfigCookie);
  } catch {
    return {};
  }
};
