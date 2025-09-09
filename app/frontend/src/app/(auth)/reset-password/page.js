"use client";

import { useCallback, useEffect, useState } from "react";
import { Button, Card, Form, message, Modal, Typography } from "antd";
import { useRouter } from "next/navigation";
import { PasswordInput, SubmitButton } from "@/components";
import { api } from "@/lib";

const { Title, Text } = Typography;
const { useForm } = Form;

const ResetPasswordPage = ({ searchParams }) => {
  const [loading, setLoading] = useState(true);
  const [isVerified, setIsVerified] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const router = useRouter();
  const [form] = useForm();
  const { code } = searchParams;

  const verifyToken = useCallback(async () => {
    try {
      const { message: res } = await api(
        "GET",
        `/auth/verify-password-code?code=${code}`
      );

      if (res === "OK") {
        setLoading(false);
        setIsVerified(true);
      } else {
        setLoading(false);
        setIsVerified(false);
        console.error("Failed to verify code");
      }
    } catch (error) {
      console.error("Error verifying code:", error);
      setLoading(false);
      setIsVerified(false);
    }
  }, [code]);

  useEffect(() => {
    verifyToken();
  }, [verifyToken]);

  const onFinish = async (values) => {
    setSubmitting(true);
    const req = await fetch(`/api/v1/auth/reset-password?code=${code}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(values),
    });
    if (req.ok) {
      Modal.success({
        content: "Your password has been successfully reset.",
        onOk: () => {
          router.push("/login");
        },
      });
      setSubmitting(false);
    } else {
      const { message: errorMessage } = await req.json();
      message.error(errorMessage);
      setSubmitting(false);
    }
  };

  if (!loading && (!code || !isVerified)) {
    return (
      <Card
        style={{ width: 400 }}
        classNames={{
          header: "text-center",
        }}
        title={<Title level={3}>Reset Password</Title>}
      >
        <p className="text-gray-600 text-center">
          The link you used is invalid or has expired.
        </p>
        <Button
          type="primary"
          htmlType="button"
          onClick={() => router.push("/forgot-password")}
          block
        >
          Request New Link
        </Button>
      </Card>
    );
  }

  return (
    <Card
      style={{ width: 400 }}
      classNames={{
        header: "text-center",
      }}
      title={<Title level={3}>Reset Password</Title>}
      loading={loading}
    >
      <Text>Enter your new password below to reset it.</Text>
      <Form
        layout="vertical"
        name="reset-password"
        form={form}
        onFinish={onFinish}
      >
        {(_, formInstance) => (
          <>
            <PasswordInput.WithRules
              label="Password"
              placeholder="New Password"
              errors={formInstance.getFieldError("password")}
            />
            <PasswordInput
              label="Confirm Password"
              name="confirm_password"
              rules={[
                {
                  required: true,
                },
              ]}
              placeholder="Confirm new password"
            />
            <SubmitButton form={form} loading={submitting} block>
              Reset Password
            </SubmitButton>
          </>
        )}
      </Form>
    </Card>
  );
};

export default ResetPasswordPage;
