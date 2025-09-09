import { ReviewedModal, ReviewList } from "@/components";
import { api } from "@/lib";
import { Flex } from "antd";
import dynamic from "next/dynamic";
import Link from "next/link";
import { redirect } from "next/navigation";
import dayjs from "dayjs";
import advancedFormat from "dayjs/plugin/advancedFormat";
dayjs.extend(advancedFormat);

const ReviewedMap = dynamic(() => import("@/components/Map/ReviewedMap"), {
  ssr: false,
});

const PublicationReviewPage = async ({ params }) => {
  const review = await api("GET", `/admin/publication-review/${params.review}`);
  if (!review?.completed_at) {
    redirect("/publications");
  }
  const yearMonth = dayjs(review?.publication?.year_month, "YYYY-MM").format(
    "MMMM YYYY"
  );
  return (
    <div className="w-full min-h-screen">
      <Flex align="center" justify="space-between" gap={4}>
        <div className="py-4">
          <Link href={`/publications/${review?.publication?.id}`}>
            <h1 className="text-3xl font-bold">
              {`Inkundla CDI Review for: ${yearMonth}`}
            </h1>
          </Link>
          <h2>
            <b>Submitted at:</b>
            {` ${dayjs(review?.completed_at).format("MMMM Do, YYYY - h:mm A")}`}
          </h2>
        </div>
        <div className="w-4/12 xl:w-80"></div>
      </Flex>
      <div className="w-full flex flex-row items-start">
        <div
          className="w-full lg:w-4/12 2xl:w-3/12 border-l border-b border-t border-neutral-200 relative"
          style={{ borderStyle: "solid" }}
        >
          <ReviewList
            dataSource={review?.suggestion_values}
            id={review?.id}
            isCompleted
          />
        </div>
        <div className="w-full lg:w-8/12 2xl:w-9/12 border border-neutral-200">
          <ReviewedMap data={review?.suggestion_values} review={review} />
        </div>
      </div>
      <ReviewedModal {...review?.publication} />
    </div>
  );
};

export default PublicationReviewPage;
