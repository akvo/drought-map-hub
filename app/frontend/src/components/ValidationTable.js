"use client";

import { ReadCommentIcon, UnreadCommentIcon } from "@/components/Icons";
import {
  DROUGHT_CATEGORY,
  DROUGHT_CATEGORY_COLOR,
  DROUGHT_CATEGORY_LABEL,
} from "@/static/config";
import {
  Button,
  Checkbox,
  Flex,
  Input,
  Modal,
  Select,
  Space,
  Table,
  Typography,
} from "antd";
import classNames from "classnames";
import { useMemo, useState } from "react";

const { Search } = Input;
const { Text } = Typography;

const ValidationTable = ({
  data = [],
  extraColumns = [],
  onDetails,
  onSelectValue,
  onNonDisputed,
  onNonValidated,
  onBulkValidation,
}) => {
  const [selectedRowKeys, setSelectedRowKeys] = useState([]);
  const [updating, setUpdating] = useState(false);
  const [search, setSearch] = useState(null);

  const columns = useMemo(() => {
    return [
      {
        title: "Inkhundla",
        dataIndex: "name",
        defaultSortOrder: "ascend",
        sorter: (a, b) => {
          if (a?.name && b?.name) {
            return a.name.localeCompare(b.name);
          }
          return false;
        },
        fixed: "left",
        width: 192,
      },
      {
        title: "Initial Value",
        dataIndex: "initial_category",
        render: (value) => {
          return DROUGHT_CATEGORY_LABEL?.[value];
        },
        fixed: "left",
        width: 192,
      },
      {
        title: "Validated Value",
        dataIndex: "category",
        render: (value, { administration_id }) => (
          <Select
            onChange={(val) => onSelectValue(val, administration_id)}
            options={DROUGHT_CATEGORY.slice(0, DROUGHT_CATEGORY.length - 1)}
            placeholder="Select Drought category"
            className="w-full"
            defaultValue={value}
            allowClear
          />
        ),
        fixed: "left",
        width: 192,
      },
      ...extraColumns,
      {
        title: "",
        dataIndex: "administration_id",
        render: (_, record) => {
          const comments = extraColumns
            ?.map((col) => record[`${col.dataIndex}_comment`])
            ?.filter((col) => col?.comment) || [];
          return (
            <Button type="text" onClick={() => onDetails(record)}>
              {comments.length === 0 ? (
                <ReadCommentIcon />
              ) : (
                <UnreadCommentIcon />
              )}
            </Button>
          );
        },
        fixed: "right",
        width: 35,
      },
    ];
  }, [extraColumns, onSelectValue, onDetails]);

  const handleNonDisputed = async (e) => {
    setUpdating(true);
    const isChecked = e.target.checked;
    const _selected = await onNonDisputed(isChecked);
    setUpdating(false);
    if (isChecked) {
      setSelectedRowKeys(_selected);
    } else {
      setSelectedRowKeys([]);
    }
  };

  const handleNonValidated = async (e) => {
    const isChecked = e.target.checked;
    await onNonValidated(isChecked);
  };

  const runBulkValidation = async () => {
    setUpdating(true);
    await onBulkValidation(selectedRowKeys);
    setUpdating(false);
    setSelectedRowKeys([]);
  };

  const handleBulkValidation = () => {
    Modal.confirm({
      title: "Confirm Bulk Validation",
      content: (
        <div>
          <Text>
            <strong>{selectedRowKeys.length} Tinkhundla</strong> will copy
            non-disputed values.
          </Text>
          <Text>Are you sure?</Text>
        </div>
      ),
      onOk: runBulkValidation,
    });
  };

  return (
    <div className="w-full space-y-6">
      <Flex align="center" justify="space-between">
        <Space>
          <Search
            placeholder="Search Inkhundla"
            onSearch={setSearch}
            onClear={() => setSearch(null)}
            allowClear
          />

          <Checkbox onClick={handleNonDisputed}>Non-disputed only</Checkbox>

          <Checkbox onClick={handleNonValidated}>Non-validated only</Checkbox>
        </Space>
        <div>
          <Button
            type="primary"
            onClick={handleBulkValidation}
            disabled={selectedRowKeys?.length === 0}
            loading={updating && selectedRowKeys?.length}
          >
            Validate all values
          </Button>
        </div>
      </Flex>
      <Table
        rowSelection={{
          type: "checkbox",
          selectedRowKeys,
          hideSelectAll: true,
          onChange: (newSelectedRowKeys) => {
            setSelectedRowKeys(newSelectedRowKeys);
          },
          getCheckboxProps: (record) => {
            const reviewValues = Object.keys(record)
              .filter((key) => !isNaN(key))
              .map((key) => record[key]);

            const disabled =
              new Set(reviewValues).size > 1 ||
              record?.category ||
              record?.category === 0;
            return {
              // disabled: disabled,
              style: {
                visibility: "hidden",
              },
            };
          },
        }}
        components={{
          body: {
            cell: ({ children, color, className, style }) => (
              <td
                className={classNames(
                  className,
                  "ant-table-cell hover:ant-table-cell-row-hover edh-cell",
                  {
                    [`bg-[${color}]`]: color,
                  }
                )}
                style={style}
              >
                {children}
              </td>
            ),
          },
        }}
        scroll={{
          x: "max-content",
        }}
        columns={columns.map((col) => ({
          ...col,
          onCell: (record) => {
            if (col.dataIndex === "name") {
              return record;
            }
            return {
              record,
              dataIndex: col.dataIndex,
              title: col.title,
              color: DROUGHT_CATEGORY_COLOR?.[record?.[col.dataIndex]],
            };
          },
        }))}
        dataSource={data?.filter((d) =>
          search ? d?.name?.toLowerCase()?.includes(search?.toLowerCase()) : d
        )}
        loading={updating}
        rowClassName="edh-row"
        rootClassName="edh-validation"
      />
    </div>
  );
};

export default ValidationTable;
