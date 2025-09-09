import { api } from "@/lib";
import dynamic from "next/dynamic";
import { redirect } from "next/navigation";

const PublicationForm = dynamic(
  () => import("@/components/Forms/PublicationForm"),
  {
    ssr: false,
  }
);

const CreatePublicationPage = async ({ searchParams }) => {
  const geonode = await api(
    "GET",
    `/admin/cdi-geonode?id=${searchParams?.cdi_geonode_id}`
  );
  const { data: reviewerList = [], ...reviewer } = await api(
    "GET",
    "/admin/reviewers?page=1"
  );
  if (!geonode?.pk) {
    redirect("/publications");
  }

  return (
    <div className="w-full h-full pt-6 pb-4">
      <h1 className="font-bold text-2xl xl:text-3xl py-2">Create A New Publication</h1>
      <PublicationForm
        {...{
          geonode,
          reviewer,
          reviewerList,
        }}
      />
    </div>
  );
};

export default CreatePublicationPage;
