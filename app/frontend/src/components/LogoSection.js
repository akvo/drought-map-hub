import Image from "next/image";
import { getAppConfig } from "@/lib";
import { APP_SETTINGS } from "@/static/config";

const LogoSection = async () => {
  const appConfig = await getAppConfig();
  return (
    <div
      className="w-full min-h-36 bg-image-login bg-no-repeat bg-center bg-cover"
      id="edm-about"
    >
      <div className="container w-full py-9 flex flex-col items-center justify-center gap-9">
        <h2 className="text-xl xl:text-2xl text-primary font-bold">
          ABOUT {appConfig?.name || APP_SETTINGS.title}
        </h2>
        <p className="w-5/12 text-center">{APP_SETTINGS.about}</p>
        <ul className="flex flex-row items-center gap-12 mb-12 logo-list">
          {appConfig?.organizations
            ?.filter((org) => org?.is_collaborator && org?.logo)
            ?.map((org) => (
              <li key={org.id}>
                <a href={org.url} target="_blank" rel="noopener noreferrer">
                  <Image
                    src={org.logo}
                    width={255}
                    height={95}
                    alt={org.name}
                    className="logo-image"
                  />
                </a>
              </li>
            ))}
        </ul>
      </div>
    </div>
  );
};

export default LogoSection;
