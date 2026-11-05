"use client";

import { useAppContext } from "@/context/AppContextProvider";

/**
 * DIH-3: read optional-module flags on the client.
 *
 * Source is `appConfig.modules` (delivered by SetupResponseSerializer -> the
 * appConfig cookie/context). Mirrors the backend contract: when no modules are
 * configured, everything is on. Accepts either the dict shape
 * ({geonode: true, ...}) or a plain list of enabled names.
 *
 * Usage: a disabled module's tab/menu/layer is simply not rendered.
 *   const weatherOn = useModule("weather");
 */
export const useModule = (name) => {
  const ctx = useAppContext();
  const modules = ctx?.appConfig?.modules;
  if (!modules) {
    return true;
  }
  if (Array.isArray(modules)) {
    return modules.includes(name);
  }
  return Boolean(modules[name]);
};
