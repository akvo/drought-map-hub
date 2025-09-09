"use client";

import Link from "next/link";
import { Dropdown } from "antd";
import { UserCircle } from "./Icons";
import { LogoutButton } from "./Buttons";
import { USER_ROLES } from "@/static/config";
import { getProfileDropdownItems } from "@/lib";

const DashboardLayout = ({ user, children }) => {
  const menuByRoles = getProfileDropdownItems(user);
  const menuItems = [
    ...menuByRoles,
    {
      key: 99,
      label: <LogoutButton className="dropdown-item" />,
    },
  ];
  return (
    <div className="w-full min-h-screen">
      <div className="w-full py-2 bg-primary sticky top-0 z-50">
        <div className="w-full container flex flex-row justify-between items-center">
          <div>
            <Link
              href={
                user?.role === USER_ROLES.admin ? "/publications" : "/reviews"
              }
              className="text-white"
            >
              Dashboard
            </Link>
          </div>
          <div>
            <Dropdown
              placement="bottomRight"
              menu={{
                items: menuItems,
              }}
              trigger={["click"]}
              overlayClassName="dropdown-profile"
            >
              <a
                role="button"
                className="text-white"
                onClick={(e) => e.preventDefault()}
              >
                <UserCircle size={32} />
              </a>
            </Dropdown>
          </div>
        </div>
      </div>
      <main className="w-full container">{children}</main>
    </div>
  );
};

export default DashboardLayout;
