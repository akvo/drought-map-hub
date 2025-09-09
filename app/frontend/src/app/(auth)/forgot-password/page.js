"use client";

import { SubmitButton } from "@/components";
import { api } from "@/lib";
import { Button, Card, Form, Input, message, Typography } from "antd";
import { useRouter } from "next/navigation";
import { useState } from "react";

const { Title, Text } = Typography;
const { useForm } = Form;

const ForgotPasswordPage = () => {
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const router = useRouter();
  const [form] = useForm();

  const onFinish = async (values) => {
    setLoading(true);
    try {
      const { message: res } = await api(
        "POST",
        "/auth/forgot-password",
        values
      );
      if (res === "OK") {
        setSuccess(true);
        setLoading(false);
      } else {
        message.error(res);
        setLoading(false);
      }
    } catch (error) {
      setLoading(false);
      console.error(error);
    }
  };

  return (
    <Card
      style={{ width: 400 }}
      classNames={{
        header: "text-center",
      }}
      title={<Title level={3}>Forgot Your Password?</Title>}
    >
      {success ? (
        <div className="text-center">
          <Title level={4}>Email sent successfully</Title>
          <Text>Please check your email to reset your password</Text>
        </div>
      ) : (
        <>
          <Text className="w-72">
            {`Enter your email address below and we\'ll send you a link to reset
            your password.`}
          </Text>
          <Form layout="vertical" form={form} onFinish={onFinish}>
            <Form.Item label="Email" name="email">
              <Input type="email" placeholder="Your Email" />
            </Form.Item>
            <SubmitButton form={form} loading={loading} block>
              Send reset link
            </SubmitButton>
          </Form>
        </>
      )}
      <Button
        htmlType="button"
        type="primary"
        className="my-3"
        onClick={() => router.push("/login")}
        ghost
        block
      >
        Back to Login
      </Button>
    </Card>
  );
};

export default ForgotPasswordPage;
