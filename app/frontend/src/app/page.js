import dynamic from "next/dynamic";
import { api, auth } from "@/lib";
import { FeedbackSection, LogoSection, Navbar } from "@/components";
import Link from "next/link";
import { Button } from "antd";
import { CaretRight } from "@/components/Icons";
import dayjs from "dayjs";
import advancedFormat from "dayjs/plugin/advancedFormat";
import customParseFormat from "dayjs/plugin/customParseFormat";
import { APP_SETTINGS } from "@/static/config";

dayjs.extend(advancedFormat);
dayjs.extend(customParseFormat);

const PublicMap = dynamic(() => import("../components/Map/PublicMap"), {
  ssr: false,
});

const Home = async () => {
  const session = await auth.getSession();
  const { data } = await api("GET", "/maps?page_size=1");
  const map = data?.[0] || null;
  return (
    <div className="w-full min-h-screen">
      <Navbar session={session} />
      <div className="container w-full h-full relative space-y-4 xl:space-y-8 pt-3 pb-9">
        <div className="w-full space-y-2">
          <div className="w-full border-b border-b-neutral-200 pb-4">
            <h1 className="text-2xl xl:text-3xl font-bold">
              {APP_SETTINGS.title}
            </h1>
          </div>
          {map && (
            <div className="w-full flex flex-row align-center justify-between">
              <div>
                <h1 className="text-xl xl:text-2xl font-bold">
                  Composite Drought Map -{" "}
                  {dayjs(map.year_month, "DD-MM-YYYY").format("MMMM YYYY")}
                </h1>
                <p className="text-neutral-600">
                  Published at:{" "}
                  {dayjs(map.published_at).format("MMMM Do, YYYY - h:mm A")}
                </p>
              </div>
              <Link href="/browse">
                <Button
                  type="link"
                  icon={<CaretRight />}
                  iconPosition="end"
                  size="large"
                >
                  Browse All
                </Button>
              </Link>
            </div>
          )}
        </div>
        {map && (
          <div className="w-full flex items-start gap-6">
            <PublicMap {...map} />
          </div>
        )}
        {map && (
          <div className="w-full overflow-x-auto" id="edh-narrative">
            <div dangerouslySetInnerHTML={{ __html: map.narrative }} />
          </div>
        )}
      </div>
      <LogoSection />
      <FeedbackSection />
    </div>
  );
};

export default Home;
