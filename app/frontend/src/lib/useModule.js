"use client";

import { useAppContext } from "@/context/AppContextProvider";

/**
 * DIH-3: read optional-module flags on the client.
 *
 * Source is `appConfig.modules` (delivered by SetupResponseSerializer -> the
 * appConfig cookie/context), derived from the backend env `DIH_MODULES` — the
 * single source of truth (DIH-2). Mirrors the backend gate `module_enabled`:
 * when no modules are configured (`DIH_MODULES` unset), `modules` is null and
 * everything is on; otherwise it is a dict of enabled names ({geonode: true}),
 * and an absent name is off.
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
  return Boolean(modules[name]);
};
