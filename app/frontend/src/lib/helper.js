import { USER_ROLES } from "@/static/config";
import { Button } from "antd";
import Link from "next/link";

export const transformReviews = (
  administrations = [],
  reviews = [],
  users = [],
  publication = {}
) => {
  return administrations
    ?.map((a) => {
      const initial_category = publication?.initial_values?.find(
        (v) => v?.administration_id === a?.administration_id
      )?.category;
      const category = publication?.validated_values?.find(
        (v) => v?.administration_id === a?.administration_id
      )?.category;
      const twgMapping = users?.reduce((acc, prev) => {
        const findCategory = reviews?.find(
          (r) =>
            r?.user_id === prev.id &&
            r?.administration_id === a?.administration_id
        );
        acc[prev.id] = findCategory?.category;
        acc[`${prev.id}_comment`] = {
          user: `${prev.name} (${prev.email})`,
          twg: prev.technical_working_group,
          comment: findCategory?.comment,
          category: findCategory?.category,
        };
        return acc;
      }, {});
      return {
        ...a,
        key: a?.administration_id,
        initial_category,
        category,
        ...twgMapping,
      };
    })
    ?.sort((a, b) => a?.name?.localeCompare(b?.name))
    ?.filter((a) => {
      return Object.keys(a)
        .filter((a) => !isNaN(a))
        .filter((k) => a?.[k] !== undefined).length;
    });
};

export const getProfileDropdownItems = (user, isPublic = false) => {
  const menuItems = [
    {
      key: 11,
      label: isPublic ? "Dashboard" : "View Map",
      url: isPublic
        ? user?.role === USER_ROLES.admin
          ? "/publications"
          : "/reviews"
        : "/",
    },
    {
      key: 1,
      label: "Profile",
      url: "/profile",
    },
  ];
  const menuByRoles =
    user?.role === USER_ROLES.admin
      ? [
          ...menuItems,
          {
            key: 2,
            label: "User Management",
            url: "/admin/v1_users/systemuser/",
          },
          {
            key: 3,
            label: "Settings",
            url: "/settings",
          }
        ]
      : menuItems;
  return menuByRoles.map(({ key, label, url }) => ({
    key,
    label: (
      <Link href={url}>
        <Button type="link" className="dropdown-item">
          {label}
        </Button>
      </Link>
    ),
  }));
};
