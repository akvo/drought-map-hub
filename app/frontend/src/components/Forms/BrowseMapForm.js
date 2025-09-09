"use client";

import { Flex } from "antd";
import { useRouter } from "next/navigation";
import { useState } from "react";
import SelectDate from "../SelectDate";

const BrowseMapForm = ({ dates = [], searchParams }) => {
  const defaultValue = isNaN(searchParams?.date)
    ? null
    : parseInt(searchParams.date, 10);
  const [browseDate, setBrowseDate] = useState(defaultValue);
  const router = useRouter();

  const onChange = (id) => {
    try {
      setBrowseDate(id);
      router.push(`/browse?date=${id}`);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <Flex align="center" justify="space-between">
      <SelectDate
        label="DATE"
        options={dates}
        onChange={onChange}
        value={browseDate}
      />
    </Flex>
  );
};

export default BrowseMapForm;
