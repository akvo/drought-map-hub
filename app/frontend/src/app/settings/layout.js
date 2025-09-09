import { UserContextProvider } from "@/context";
import { auth } from "@/lib";
import { DashboardLayout } from "@/components";

const SettingsLayout = async ({ children }) => {
  const session = await auth.getSession();
  const abilities = session?.abilities || [];
  return (
    <UserContextProvider abilities={abilities}>
      <DashboardLayout user={session}>{children}</DashboardLayout>
    </UserContextProvider>
  );
};

export default SettingsLayout;
