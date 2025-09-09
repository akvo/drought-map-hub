"use client";

import { Flex } from "antd";
import { useRouter } from "next/navigation";
import { useState } from "react";
import SelectDate from "../SelectDate";


const CompareMapForm = ({ dates = [], searchParams }) => {
  const [leftOptions, setLeftOptions] = useState(dates);
  const [rightOptions, setRightOptions] = useState(dates);

  const initLeft = isNaN(searchParams?.left)
    ? null
    : parseInt(searchParams.left, 10);
  const initRight = isNaN(searchParams?.right)
    ? null
    : parseInt(searchParams.right, 10);
  const [leftDate, setLeftDate] = useState(initLeft);
  const [rightDate, setRightDate] = useState(initRight);
  const router = useRouter();

  const onLeftChange = (excludeID) => {
    try {
      if (excludeID === rightDate) {
        setRightDate(null);
      }
      setLeftDate(excludeID);
      const options = dates.filter((d) => d?.value !== excludeID);
      setRightOptions(options);
      router.push(`/compare?left=${excludeID}&right=${rightDate}`);
    } catch (err) {
      console.error(err);
    }
  };

  const onRightChange = (excludeID) => {
    try {
      if (excludeID === leftDate) {
        leftDate(null);
      }
      setRightDate(excludeID);
      const options = dates.filter((d) => d?.value !== excludeID);
      setLeftOptions(options);
      router.push(`/compare?left=${leftDate}&right=${excludeID}`);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <Flex align="center" justify="space-between">
      <SelectDate
        label="LEFT"
        options={leftOptions}
        onChange={onLeftChange}
        value={leftDate}
      />
      <SelectDate
        label="RIGHT"
        options={rightOptions}
        onChange={onRightChange}
        value={rightDate}
      />
    </Flex>
  );
};

export default CompareMapForm;
