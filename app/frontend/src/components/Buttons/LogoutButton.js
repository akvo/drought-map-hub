"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "antd";
import { auth } from "@/lib";
import classNames from "classnames";

const LogoutButton = ({ className = null }) => {
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const onLogout = async () => {
    setLoading(true);
    await auth.signOut();
    router.push("/");
  };
  return (
    <Button
      type="link"
      onClick={onLogout}
      loading={loading}
      className={classNames(className)}
    >
      Logout
    </Button>
  );
};

export default LogoutButton;
