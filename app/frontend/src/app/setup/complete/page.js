import React from "react";
import Link from "next/link";
import { Button } from "antd";

const CompletePage = () => {
  return (
    <div>
      <h1>Setup Complete</h1>
      <p>Your setup has been completed successfully!</p>
      <Link href="/login">
        <Button type="primary">Go to Login</Button>
      </Link>
    </div>
  );
};

export default CompletePage;
