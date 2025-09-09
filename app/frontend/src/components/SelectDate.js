"use client";

import { Select, Space } from "antd";
import dayjs from "dayjs";
import advancedFormat from "dayjs/plugin/advancedFormat";
import customParseFormat from "dayjs/plugin/customParseFormat";

dayjs.extend(advancedFormat);
dayjs.extend(customParseFormat);

const SelectDate = ({ label, options, onChange, value }) => (
  <div className="text-sm font-bold bg-primary text-white pl-6 pr-1 py-1 rounded-md">
    <Space size="large">
      <span>{label}</span>
      <Select
        className="w-48"
        placeholder="Select Publication Date"
        options={options.map((o) => ({
          ...o,
          label: dayjs(o.label).format("MMMM YYYY"),
        }))}
        onChange={onChange}
        value={value}
        allowClear
      />
    </Space>
  </div>
);

export default SelectDate;
