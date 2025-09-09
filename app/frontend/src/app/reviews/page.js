"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Table, Tag, Typography } from "antd";
import { Can } from "@/components";
import { api } from "@/lib";
import { PAGE_SIZE } from "@/static/config";
import dayjs from "dayjs";
import advancedFormat from "dayjs/plugin/advancedFormat";

dayjs.extend(advancedFormat);

const { Title } = Typography;

const ReviewsPage = () => {
  const [reviews, setReviews] = useState([]);
  const [loading, setLoading] = useState(false);
  const [totalData, setTotalData] = useState(0);
  const [page, setPage] = useState(1);
  const [preload, setPreload] = useState(true);
  const router = useRouter();

  const columns = [
    {
      title: "DEADLINE",
      dataIndex: "due_date",
      key: "due_date",
      defaultSortOrder: "descend",
      sorter: (a, b) => new Date(a.due_date) - new Date(b.due_date),
      render: (value) => dayjs(value, "YYYY-MM-DD").format("MMMM Do, YYYY"),
    },
    {
      title: "MONTH",
      dataIndex: "year_month",
      key: "year_month",
      render: (value) => dayjs(value, "YYYY-MM").format("MMMM YYYY"),
    },
    {
      title: "TINKHUNDLA",
      dataIndex: "progress_review",
      key: "progress_review",
    },
    {
      title: "STATUS",
      dataIndex: "is_completed",
      key: "is_completed",
      render: (_, { is_completed }) => (
        <Tag color={is_completed ? "success" : "#6b7280"}>
          {is_completed ? "Completed" : "Pending"}
        </Tag>
      ),
    },
  ];

  const fetchData = useCallback(async () => {
    try {
      if (preload) {
        setPreload(false);
        setLoading(true);
        const { data, total } = await api(
          "GET",
          `/reviewer/reviews?page=${page}`
        );
        setTotalData(total);
        const _reviews = data.map((d) => ({ key: d?.id, ...d }));
        setReviews(_reviews);
        setLoading(false);
      }
    } catch (err) {
      console.error(err);
      setPreload(false);
    }
  }, [preload, page]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return (
    <div className="w-full h-auto space-y-4 pt-6">
      <Title level={2}>My reviews</Title>
      <Can I="read" a="Review">
        <Table
          columns={columns}
          dataSource={reviews}
          loading={loading}
          onRow={(record) => {
            return {
              onClick: () => {
                router.push(`/reviews/${record.id}`);
              },
            };
          }}
          rowClassName={"cursor-pointer"}
          pagination={
            totalData < PAGE_SIZE
              ? false
              : {
                  current: page,
                  pageSize: PAGE_SIZE,
                  total: totalData,
                  responsive: true,
                  align: "center",
                  position: ["bottomCenter"],
                  onChange: (_page) => {
                    setPage(_page);
                    setPreload(true);
                  },
                }
          }
        />
      </Can>
    </div>
  );
};

export default ReviewsPage;
