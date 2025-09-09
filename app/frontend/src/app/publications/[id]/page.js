import dynamic from "next/dynamic";
import { redirect } from "next/navigation";
import { api } from "@/lib";
import { PUBLICATION_STATUS } from "@/static/config";
import { Divider } from "antd";

const PublicationMap = dynamic(
  () => import("@/components/Map/PublicationMap"),
  { ssr: false }
);

const PublicationDetailsPage = async ({ params }) => {
  const geonodeBaseURL = process.env.GEONODE_BASE_URL;
  const publication = await api("GET", `/admin/publication/${params.id}`);
  const dataMap =
    publication?.status === PUBLICATION_STATUS.published
      ? publication?.validated_values
      : publication?.initial_values;

  if (!publication?.id) {
    redirect("/publications");
  }

  if (!publication?.id) {
    redirect("/publications");
  }

  return (
    <div className="w-full h-full space-y-3">
      <PublicationMap data={dataMap} {...{ publication, geonodeBaseURL }} />

      {publication?.narrative && (
        <div className="w-full overflow-x-auto pb-8" id="edh-narrative">
          <Divider orientation="center">Narrative</Divider>
          <div dangerouslySetInnerHTML={{ __html: publication?.narrative }} />
        </div>
      )}
    </div>
  );
};

export default PublicationDetailsPage;
