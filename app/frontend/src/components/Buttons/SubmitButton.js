"use client";

import { useState, useEffect } from "react";
import { Button, Form } from "antd";

const SubmitButton = ({ form, children, type = "primary", ...props }) => {
  const [submittable, setSubmittable] = useState(false);
  // Watch all values
  const values = Form.useWatch([], form);
  useEffect(() => {
    form
      .validateFields({
        validateOnly: true,
      })
      .then(() => setSubmittable(true))
      .catch(() => setSubmittable(false));
  }, [form, values]);
  return (
    <Button type={type} htmlType="submit" disabled={!submittable} {...props}>
      {children}
    </Button>
  );
};

export default SubmitButton;
