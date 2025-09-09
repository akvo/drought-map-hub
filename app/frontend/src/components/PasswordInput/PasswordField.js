import { useState } from "react";
import { Input } from "antd";
import { Eye, EyeSlash } from "../Icons";

const PasswordField = (props) => {
  const [visible, setVisible] = useState(false);
  return (
    <Input
      type={visible ? "text" : "password"}
      addonAfter={
        <a role="button" onClick={() => setVisible(!visible)}>
          {visible ? <Eye /> : <EyeSlash />}
        </a>
      }
      {...props}
    />
  );
};

export default PasswordField;
