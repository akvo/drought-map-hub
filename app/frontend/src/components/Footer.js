"use client";

import { Space } from "antd";
import Image from "next/image";
import dayjs from "dayjs";
import { APP_SETTINGS } from "@/static/config";
import { usePathname } from "next/navigation";

const Footer = () => {
  const pathname = usePathname();
  if (pathname === "/iframe/map") {
    return null;
  }
  return (
    <footer className="w-full px-0 py-6 bg-primary">
      <div className="container w-full text-white text-base flex flex-row items-center justify-between">
        <div>
          <p>
            &copy; {dayjs().format("YYYY")} - {APP_SETTINGS.copy}
          </p>
        </div>
        <div>
          <a href="https://akvo.org/" target="_blank">
            <Space size="middle">
              <p>Powered by </p>
              <Image
                src="/images/logo-akvo.png"
                alt="Akvo Foundation Logo"
                width={64}
                height={24}
              />
            </Space>
          </a>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
