import React from "react";
import Link from "next/link";
import { Button } from "antd";

const CompletePage = () => {
  return (
    <div>
      <div className="w-full flex flex-col items-center mb-4 space-y-4">
        <p className="w-full max-w-2xl text-center text-lg">
          Congratulations! You have successfully completed the Drought Map Hub
          setup wizard. Thank you for configuring your application.
        </p>
      </div>
      <div className="w-full flex flex-col items-center mb-4 space-y-4">
        <p className="w-full max-w-2xl text-center text-md">
          Click the button below to proceed to the login page.
        </p>
        <Link href="/login">
          <Button type="primary" size="large">
            Go to Login
          </Button>
        </Link>
      </div>
    </div>
  );
};

export default CompletePage;
