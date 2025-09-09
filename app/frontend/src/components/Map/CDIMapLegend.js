import { Card, Space } from "antd";
import classNames from "classnames";
import { DROUGHT_CATEGORY } from "@/static/config";
import { LegendIcon } from "../Icons";

const CDIMapLegend = ({ isPublic = false }) => {
  const limit = isPublic
    ? DROUGHT_CATEGORY.length - 1
    : DROUGHT_CATEGORY.length;
  return (
    <Card
      title={
        <Space>
          <LegendIcon />
          <span>LEGEND</span>
        </Space>
      }
    >
      <ul>
        {DROUGHT_CATEGORY.slice(0, limit).map((category, index) => (
          <li key={category.value}>
            <span
              className={classNames("inline-block w-4 h-4 mr-2", {
                "border border-gray-400":
                  index === DROUGHT_CATEGORY.length - 1 || index === 0,
              })}
              style={{ backgroundColor: category.color }}
            ></span>
            {category.label}
          </li>
        ))}
      </ul>
    </Card>
  );
};

export default CDIMapLegend;
