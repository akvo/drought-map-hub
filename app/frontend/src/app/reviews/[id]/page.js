import { ReviewAdmModal, ReviewList, SubmitReviewButton } from "@/components";
import { api } from "@/lib";
import { Flex } from "antd";
import dayjs from "dayjs";
import dynamic from "next/dynamic";
import { redirect } from "next/navigation";

const ReviewerMap = dynamic(
  () => import("../../../components/Map/ReviewerMap"),
  {
    ssr: false,
  }
);

const ReviewDetailsPage = async ({ params }) => {
  const review = await api("GET", `/reviewer/review/${params.id}`);
  if (!review?.id) {
    redirect("/reviews");
  }
  const [reviewed, total] = review.progress_review?.split("/");
  const remaining = total - reviewed;
  const dataSource = review?.publication?.initial_values?.map(
    ({ category, ...v }) => {
      if (review?.suggestion_values?.length) {
        const suggestion =
          review?.suggestion_values?.find(
            (s) => s?.administration_id === v?.administration_id
          ) || {};
        return {
          ...v,
          ...suggestion,
          category: {
            reviewed: suggestion?.category,
            raw: category,
          },
        };
      }
      return {
        ...v,
        category: {
          reviewed: null,
          raw: category,
        },
      };
    }
  );
  return (
    <div className="w-full min-h-screen">
      <Flex align="center" justify="space-between" gap={4}>
        <div className="leading-4 py-4">
          <h1 className="text-3xl font-bold">{`Inkundla CDI Review for: ${dayjs(review?.publication?.year_month, "YYYY-MM").format("MMMM YYYY")}`}</h1>
          <h2 className="text-xl">{`Review Deadline: ${review?.publication?.due_date}`}</h2>
        </div>
        {!review?.is_completed && remaining === 0 && (
          <SubmitReviewButton review={review} />
        )}
        {!review?.is_completed && remaining > 0 && (
          <div className="leading-2 p-4 text-center">
            <strong>REMAINING TINKHUNDLA</strong>
            <h2 className="text-2xl">{remaining}</h2>
          </div>
        )}
        {review?.is_completed && (
          <div className="leading-2 p-4 text-center">
            <strong>Review Completed</strong>
            <br />
            <small>{` at ${dayjs(review?.completed_at).format(
              "DD/MM/YYYY h:mm A"
            )}`}</small>
          </div>
        )}
      </Flex>
      <div className="w-full flex flex-row items-start">
        <div
          className="w-full lg:w-4/12 2xl:w-3/12 border-l border-b border-t border-neutral-200 relative"
          style={{ borderStyle: "solid" }}
        >
          <ReviewList
            dataSource={dataSource}
            id={review?.id}
            isCompleted={review?.is_completed}
            remaining={remaining}
          />
        </div>
        <div className="w-full lg:w-8/12 2xl:w-9/12 border border-neutral-200">
          <ReviewerMap data={dataSource} />
        </div>
      </div>
      <ReviewAdmModal review={review} />
    </div>
  );
};

export default ReviewDetailsPage;
