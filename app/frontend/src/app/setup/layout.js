import Link from "next/link";

const steps = [
  { id: 1, label: "Step 1: Application Setup", href: "/setup/step-1" },
  { id: 2, label: "Step 2: Bounding Box Setup", href: "/setup/step-2" },
  { id: 3, label: "Step 3: Users Setup", href: "/setup/step-3" },
];

const InstallLayout = ({ children }) => {
  return (
    <div style={{ display: "flex", minHeight: "calc(100vh - 73px)" }}>
      <aside
        style={{
          width: "250px",
          padding: "20px",
          background: "#f0f0f0",
          borderRight: "1px solid #ddd",
        }}
      >
        <h2>Installation Wizard</h2>
        <ul style={{ listStyle: "none", padding: 0 }}>
          {steps.map((step) => (
            <li key={step.id} style={{ marginBottom: "10px" }}>
              <Link href={step.href}>
                <span style={{ textDecoration: "none", color: "#333" }}>
                  {step.label}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </aside>
      <main style={{ flex: 1, padding: "20px" }}>{children}</main>
    </div>
  );
};

export default InstallLayout;
