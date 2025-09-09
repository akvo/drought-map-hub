"use client";

import { Button, Form, Input, message, Result } from "antd";
import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { LogoSection, Navbar, SubmitButton } from "@/components";
import { api, auth } from "@/lib";

const { useForm } = Form;

const FeedbackPage = () => {
  const [currentUser, setCurrentUser] = useState(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const router = useRouter();
  const [form] = useForm();

  const handleOnFinish = async (values) => {
    setLoading(true);
    try {
      const { message: apiMessage } = await api("POST", "/feedback", values);
      message.info(apiMessage);
      setSuccess(true);
      setLoading(false);
    } catch (err) {
      console.error(err);
      setLoading(false);
    }
  };

  const loadCurrentUser = useCallback(async () => {
    const session = await auth.getSession();
    setCurrentUser(session);
  }, []);

  useEffect(() => {
    loadCurrentUser();
  }, [loadCurrentUser]);

  return (
    <div className="w-full min-h-screen">
      <Navbar session={currentUser} />
      <div className="container w-full h-full relative pt-3 pb-9">
        <div className="w-full space-y-2 px-6">
          <div className="w-full border-b border-b-neutral-200 py-8">
            <h1 className="text-2xl xl:text-3xl font-bold text-gray-800">
              Your Feedback Matters
            </h1>
          </div>
        </div>
        <div className="w-full min-h-[calc(100vh-320px)] flex flex-col md:flex-row px-6">
          <div className="w-full md:w-3/5 pr-4 py-8">
            {success ? (
              <Result
                status="success"
                title="Thank you for your feedback!"
                subTitle="Your feedback has been successfully submitted. We appreciate your input and will use it to improve our services."
                extra={
                  <Button
                    type="primary"
                    key="console"
                    onClick={() => router.push("/")}
                  >
                    Go back to home
                  </Button>
                }
              />
            ) : (
              <Form form={form} onFinish={handleOnFinish} layout="vertical">
                <Form.Item
                  name="email"
                  label="Your E-mail"
                  placeholder="Your E-mail"
                  rules={[
                    {
                      required: true,
                      type: "email",
                    },
                  ]}
                >
                  <Input type="email" placeholder="your@mail.com" />
                </Form.Item>
                <Form.Item
                  name="feedback"
                  label="Your feedback"
                  placeholder="Your feedback"
                  rules={[
                    {
                      required: true,
                    },
                  ]}
                >
                  <Input.TextArea
                    rows={5}
                    placeholder="Share your thoughts with us..."
                  />
                </Form.Item>
                <div>
                  <SubmitButton
                    htmlType="sbmit"
                    type="primary"
                    size="large"
                    form={form}
                    loading={loading}
                  >
                    Send Feedback
                  </SubmitButton>
                </div>
              </Form>
            )}
          </div>
          <div className="w-full md:w-2/5 pl-0 pt-8 md:pl-4 md:pt-0 bg-gray-100">
            <div className="px-4 py-8">
              <h2 className="text-xl font-semibold mb-4">
                How to Send Feedback
              </h2>
              <p className="mb-2 text-sm">
                To ensure your feedback is helpful and constructive, please
                consider the following guidelines:
              </p>
              <ul className="list-disc list-inside space-y-1 text-sm ml-4">
                <li>Be clear and concise in your message.</li>
                <li>
                  Provide specific examples or details to support your feedback.
                </li>
                <li>Be respectful and courteous in your language.</li>
                <li>Focus on the issue, not the person.</li>
                <li>Suggest possible solutions or improvements.</li>
              </ul>
              <div className="mt-6 p-4 bg-blue-100 border-l-4 border-l-blue-800">
                <p className="text-sm text-blue-800 font-medium">
                  Your feedback will be sent to all Eswatini Drought Monitor
                  admins.
                </p>
              </div>
              <p className="mt-4 text-sm">Thank you for helping us improve!</p>
            </div>
          </div>
        </div>
      </div>
      <LogoSection />
    </div>
  );
};

export default FeedbackPage;
