"use client";

import { Form } from "antd";
import WithRules from "./WithRules";
import PasswordField from "./PasswordField";

const PasswordInput = ({
  name,
  label,
  dependencies = [],
  rules = [],
  hasFeedback = false,
  ...props
}) => {
  return (
    <Form.Item
      name={name}
      label={label}
      dependencies={dependencies}
      rules={rules}
      hasFeedback={hasFeedback}
    >
      <PasswordField {...props} />
    </Form.Item>
  );
};

PasswordInput.WithRules = WithRules;

export default PasswordInput;
