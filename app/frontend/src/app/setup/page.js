import React from "react";
import Link from "next/link";
import { Button } from "antd";

const InstallPage = () => {
  return (
    <div>
      <div className="w-full flex flex-col items-center mb-4">
        <p className="w-full max-w-2xl text-center text-lg">
          Welcome to the Drought Map Hub setup wizard. This wizard will guide
          you through the initial configuration steps to get your Drought Map
          Hub up and running.
        </p>
      </div>
      <div className="w-full flex flex-col items-center mb-4">
        <p className="w-full max-w-3xl text-center text-md">
          The setup process includes the following steps:
        </p>
        <ul className="list-disc list-inside mt-2 text-left max-w-3xl mb-6">
          <li>Step 1: Application Configuration</li>
          <li>Step 2: Bounding Box Configuration</li>
          <li>Step 3: Users Management</li>
        </ul>
        <Link href="/setup/step-1">
          <Button type="primary" size="large">
            Go to Setup
          </Button>
        </Link>
      </div>
    </div>
  );
};

export default InstallPage;
