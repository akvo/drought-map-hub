import Link from "next/link";
import { Button } from "antd";

const FeedbackSection = () => {
  return (
    <div className="feedback-section py-16 bg-blue-100 rounded-lg shadow-md flex flex-col items-center justify-center">
      <h2 className="text-2xl font-bold mb-2">Your Feedback Matters</h2>
      <p className="mb-4 text-center">
        Get in touch with us for support or feedback on the Eswatini Drought
        Monitor platform.
      </p>
      <Link href="/feedback">
        <Button type="primary" size="large">
          Leave feedback
        </Button>
      </Link>
    </div>
  );
};

export default FeedbackSection;
