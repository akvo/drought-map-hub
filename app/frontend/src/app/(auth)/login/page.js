"use client";

import { useState } from "react";
import { Alert, Card, Form, Input, Typography } from "antd";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { auth } from "@/lib";
import { PasswordInput, SubmitButton } from "@/components";
import { HOME_PAGE } from "@/static/config";

const { Title, Text } = Typography;
const { useForm } = Form;

const LoginPage = () => {
  const [submitting, setSubmitting] = useState(false);
  const [invalid, setInvalid] = useState(false);
  const router = useRouter();
  const [form] = useForm();

  const onFinish = async (values) => {
    setSubmitting(true);
    try {
      const { status, role } = await auth.signIn(values);
      if (status === 200) {
        const dashboardURL = HOME_PAGE?.[role] || "/";
        router.push(dashboardURL);
      } else {
        setSubmitting(false);
        setInvalid(true);
      }
    } catch (error) {
      const errorKey = error.message.replace(/^Error:\s*/, "");
      console.error("error", errorKey);
      // message.error(tr(errorKey));
      setSubmitting(false);
    }
  };

  return (
    <Card
      style={{ width: 400 }}
      classNames={{
        header: "text-center",
      }}
      title={<Title level={3}>Log in to your account</Title>}
    >
      {invalid && (
        <Alert
          message="Invalid email or password"
          type="error"
          showIcon
          closeable
        />
      )}
      <Text className="my-4">Welcome back! Please enter your details.</Text>

      <Form layout="vertical" name="login" form={form} onFinish={onFinish}>
        <Form.Item
          label="Email"
          name="email"
          rules={[
            {
              required: true,
              type: "email",
            },
          ]}
        >
          <Input type="email" placeholder="Your Email" />
        </Form.Item>
        <PasswordInput
          label="Password"
          name="password"
          rules={[
            {
              required: true,
            },
          ]}
          placeholder="Your password"
        />
        <div className="w-full py-3 flex items-center justify-between">
          <div></div>
          <div>
            <Link href={"/forgot-password"}>Forgot password</Link>
          </div>
        </div>
        <SubmitButton form={form} loading={submitting} block>
          Sign in
        </SubmitButton>
      </Form>
    </Card>
  );
};

export default LoginPage;
