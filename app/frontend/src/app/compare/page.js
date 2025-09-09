import { CompareMapForm, FeedbackSection, LogoSection, Navbar } from "@/components";
import { api, auth } from "@/lib";
import { APP_SETTINGS } from "@/static/config";
import dynamic from "next/dynamic";

const ComparisonSlider = dynamic(
  () => import("@/components/ComparisonSlider"),
  {
    ssr: false,
  }
);

const ComparePage = async ({ searchParams }) => {
  const session = await auth.getSession();
  const dates = await api("GET", "/dates");
  const baseURL = process.env.WEBDOMAIN;
  return (
    <div className="w-full min-h-screen">
      <Navbar session={session} />
      <div className="container w-full h-full relative space-y-4 xl:space-y-8 pt-3 pb-9">
        <div className="w-full space-y-2">
          <div className="w-full border-b border-b-neutral-200 pb-4">
            <h1 className="text-2xl xl:text-3xl font-bold">
              {APP_SETTINGS.title} - Compare Map
            </h1>
          </div>
          <div className="w-full py-3">
            <CompareMapForm dates={dates} searchParams={searchParams} />
          </div>
        </div>
        <ComparisonSlider {...{ baseURL, searchParams }} />
      </div>
      <LogoSection />
      <FeedbackSection />
    </div>
  );
};

export default ComparePage;
