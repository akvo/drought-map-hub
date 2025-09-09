"use client";

import React, { useState } from "react";
import { Checkbox, Form, Modal, Tooltip } from "antd";
import { WarningCicle } from "@/components/Icons";
import PasswordField from "./PasswordField";

const WithRules = ({ label, placeholder = "Password", errors = [] }) => {
  const [checkedList, setCheckedList] = useState([]);
  const [openPasswordCheck, setOpenPasswordCheck] = useState(false);

  const checkBoxOptions = [
    { name: "Lowercase Character", re: /[a-z]/ },
    { name: "Numbers", re: /\d/ },
    { name: "Uppercase Character", re: /[A-Z]/ },
    { name: "No White Space", re: /^\S*$/ },
    { name: "Minimum 8 Characters", re: /(?=.{8,})/ },
  ];

  const onChangePassword = ({ target }) => {
    const criteria = checkBoxOptions
      .map((x) => {
        const available = x.re.test(target.value);
        return available ? x.name : false;
      })
      .filter((x) => x);
    setCheckedList(criteria);
  };

  return (
    <React.Fragment>
      <Form.Item
        label={label}
        name="password"
        rules={[
          {
            required: true,
          },
          () => ({
            validator() {
              if (checkedList.length === checkBoxOptions.length) {
                return Promise.resolve();
              }
              return Promise.reject(new Error("Invalid Criteria"));
            },
          }),
        ]}
        hasFeedback={false}
        help={
          <div className="w-full flex flex-col lg:flex-row lg:items-center lg:justify-between py-2">
            <div>
              {errors.map((err, ex) => (
                <Tooltip
                  key={ex}
                  title={
                    <ul>
                      {checkBoxOptions.map((cb, cbx) => (
                        <li key={cbx}>
                          {checkedList.includes(cb.name) ? "✅" : "❌"}
                          {` ${cb.name}`}
                        </li>
                      ))}
                    </ul>
                  }
                >
                  <span className="float-left">{err}</span>
                  <span className="float-left ml-1 py-1">
                    <WarningCicle size={14} />
                  </span>
                </Tooltip>
              ))}
            </div>
            <div>
              <button
                type="button"
                onClick={() => setOpenPasswordCheck(true)}
                className="text-sm italic text-dark-3"
              >
                {`Password Strength: ${checkedList.length}/${checkBoxOptions.length} criteria met`}
              </button>
            </div>
          </div>
        }
      >
        <PasswordField
          placeholder={placeholder}
          onChange={onChangePassword}
          className="min-h-10"
        />
      </Form.Item>
      <Modal
        title={`Password Strength: ${checkedList.length}/${checkBoxOptions.length} criteria met`}
        open={openPasswordCheck}
        onOk={() => setOpenPasswordCheck(false)}
        onCancel={() => setOpenPasswordCheck(false)}
        closable
      >
        <Checkbox.Group
          options={checkBoxOptions.map((x) => x.name)}
          value={checkedList}
        />
      </Modal>
    </React.Fragment>
  );
};

export default WithRules;
