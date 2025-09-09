"use client";

import { getProfileDropdownItems } from "@/lib";
import { Button, Dropdown } from "antd";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { UserCircle } from "./Icons";
import classNames from "classnames";
import { PUBLIC_MENU_ITEMS } from "@/static/config";

const NavItem = ({ pathname, url, label }) => {
  return (
    <Link href={url} className="text-neutral-50">
      <button
        className={classNames(
          "text-white px-6 py-3 transition-colors duration-300",
          {
            "bg-rose-800 hover:bg-rose-900 ring-b ring-b-white":
              pathname === url,
            "hover:bg-rose-800": pathname !== url,
          }
        )}
      >
        {label}
      </button>
    </Link>
  );
};

const Navbar = ({ session }) => {
  const pathname = usePathname();
  const profileItems = getProfileDropdownItems(session, true);
  return (
    <div className="w-full bg-primary">
      <div className="w-full container flex flex-row justify-between items-center">
        <nav className="w-full text-base">
          {PUBLIC_MENU_ITEMS.map((m, mx) => (
            <NavItem {...m} pathname={pathname} key={mx} />
          ))}
        </nav>

        <div className="w-fit px-4">
          {session ? (
            <Dropdown
              placement="bottomRight"
              menu={{
                items: profileItems,
              }}
              trigger={["click"]}
              overlayClassName="dropdown-profile"
            >
              <a role="button" className="text-white" aria-label="Profile">
                <UserCircle size={32} />
              </a>
            </Dropdown>
          ) : (
            <Link href={"/login"}>
              <Button ghost>LOGIN</Button>
            </Link>
          )}
        </div>
      </div>
    </div>
  );
};

export default Navbar;
