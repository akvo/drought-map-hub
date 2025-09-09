"use client";

import { useState } from "react";
import { Form, Button, Modal } from "antd";
import { api } from "@/lib";
import dayjs from "dayjs";
import { useRouter } from "next/navigation";

const { useForm } = Form;

const SubmitReviewButton = ({ review = {} }) => {
  const [loading, setLoading] = useState(false);
  const [form] = useForm();
  const router = useRouter();

  const onFinish = async () => {
    setLoading(true);
    try {
      await api("PUT", `/reviewer/review/${review?.id}`, {
        is_completed: true,
        completed_at: dayjs().format("YYYY-MM-DD HH:mm:ss"),
      });
      setLoading(false);
      router.refresh(`/reviews/${review?.id}`);
    } catch (err) {
      console.error(err);
      setLoading(false);
    }
  };
  return (
    <Form initialValues={review} form={form} onFinish={onFinish}>
      <Button
        type="primary"
        loading={loading}
        onClick={() => {
          Modal.confirm({
            content: "Are you sure?",
            onOk: () => {
              form.submit();
            },
          });
        }}
      >
        Submit Review
      </Button>
    </Form>
  );
};

export default SubmitReviewButton;
