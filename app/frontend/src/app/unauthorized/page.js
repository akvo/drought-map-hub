import Link from "next/link";

const { Button } = require("antd");

const UnauthorizedPage = () => {
  return (
    <div className="w-full min-h-screen flex flex-col items-center justify-center gap-1">
      <h1 className="text-2xl xl:text-3xl font-bold">You’re Not Authorized</h1>
      <p>You need proper authorization to view this page. </p>
      <Link href="/">
        <Button type="primary">Go Back Home</Button>
      </Link>
    </div>
  );
};

export default UnauthorizedPage;
