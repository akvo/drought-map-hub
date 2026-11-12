"use client";

import { useAppContext } from "@/context/AppContextProvider";

// Eswatini default; used when the cookie predates the field or no country
// config set one. Keeps rendering stable across a config refresh.
const FALLBACK = { one: "Inkhundla", many: "Tinkhundla" };

/**
 * DIH-6: read the admin-unit noun (singular/plural) from config.
 *
 * Source is `appConfig.admin_label` (delivered by SetupResponseSerializer ->
 * the appConfig cookie/context, the same path as useModule). Another country
 * overrides it (e.g. { one: "District", many: "Districts" }).
 *
 * Usage:
 *   const adminLabel = useAdminLabel();
 *   <Column title={adminLabel.one} />            // "Inkhundla" / "District"
 *   <span>{`REMAINING ${adminLabel.many.toUpperCase()}`}</span>
 */
export const useAdminLabel = () => {
  const ctx = useAppContext();
  const label = ctx?.appConfig?.admin_label;
  return {
    one: label?.one || FALLBACK.one,
    many: label?.many || FALLBACK.many,
  };
};
