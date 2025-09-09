import { DashboardLayout } from "@/components";
import { UserContextProvider } from "@/context";
import { auth } from "@/lib";

const ProfileTemplate = async ({ children }) => {
  const session = await auth.getSession();
  return (
    <UserContextProvider>
      <DashboardLayout user={session}>{children}</DashboardLayout>
    </UserContextProvider>
  );
};

export default ProfileTemplate;
