"use client";

import { ReactCompareSlider } from "react-compare-slider";

const ComparisonSlider = ({ baseURL, searchParams }) => {
  return (
    <div className="w-full">
      <ReactCompareSlider
        itemOne={
          <iframe
            width={"100%"}
            height={720}
            src={`${baseURL}/iframe/map?id=${searchParams?.left || 0}`}
          />
        }
        itemTwo={
          <iframe
            width={"100%"}
            height={720}
            src={`${baseURL}/iframe/map?id=${searchParams?.right || 1}`}
          />
        }
        boundsPadding={0}
        clip="both"
        keyboardIncrement="5%"
        position={50}
      />
    </div>
  );
};

export default ComparisonSlider;
