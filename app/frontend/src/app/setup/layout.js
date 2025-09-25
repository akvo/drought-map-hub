"use client";

import { useMemo } from "react";
import { Steps, Typography } from "antd";
import { usePathname } from "next/navigation";

const { Title } = Typography;

const steps = [
  { id: 1, label: "Step 1: Application Setup", href: "/setup/step-1" },
  { id: 2, label: "Step 2: Bounding Box Setup", href: "/setup/step-2" },
  { id: 3, label: "Step 3: Users Setup", href: "/setup/step-3" },
];

const InstallLayout = ({ children }) => {
  const pathName = usePathname();

  // Determine the active step based on the current path
  // get the current path from next router
  const activeIndex = useMemo(() => {
    const step = steps.find((s) => s.href === pathName);
    return step ? steps.indexOf(step) : null;
  }, [pathName]);

  return (
    <div className="container w-full min-h-[calc(100vh-73px)] py-4 flex flex-col gap-3">
      <Title level={2} className="text-center">
        Drought-Map Hub Installation Wizard
      </Title>
      <div className="w-full flex justify-center align-center">
        <Steps current={activeIndex} className="w-full max-w-3xl px-2">
          {steps.map((step) => (
            <Steps.Step key={step.id} title={step.label} />
          ))}
        </Steps>
      </div>
      <main className="container flex-1 p-5">{children}</main>
    </div>
  );
};

export default InstallLayout;
