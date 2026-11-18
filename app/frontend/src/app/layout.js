import "./globals.css";
import dynamic from "next/dynamic";
import { AntdRegistry } from "@ant-design/nextjs-registry";
import { ConfigProvider } from "antd";
import { AppContextProvider } from "@/context";
import { inter, roboto, robotoMono } from "./fonts";
import classNames from "classnames";
import { Footer } from "@/components";
import { APP_SETTINGS } from "@/static/config";
import { getAppConfig, resolveTheme } from "@/lib";

export async function generateMetadata() {
  const appConfig = await getAppConfig();
  return {
    title: appConfig?.name || APP_SETTINGS.title,
    description: appConfig?.about || APP_SETTINGS.about,
  };
}

const DynamicScript = dynamic(() => import("@/components/DynamicScript"), {
  ssr: false,
});

export default async function RootLayout({ children }) {
  const appConfig = await getAppConfig();
  // DIH-9: resolve the operator's chosen theme (by name) to its colour set,
  // then expose it to both the Ant theme and the `bg-primary` /
  // `text-primary-foreground` / `bg-primary-active` Tailwind classes.
  const theme = resolveTheme(appConfig?.theme);
  return (
    <html lang="en">
      <body
        style={{
          "--primary-color": theme.background,
          "--primary-foreground": theme.foreground,
          "--primary-active": theme.active,
        }}
        className={classNames(
          "antialiased",
          inter.variable,
          roboto.variable,
          robotoMono.variable,
        )}
      >
        <AppContextProvider appConfig={appConfig}>
          <AntdRegistry>
            <ConfigProvider
              theme={{
                token: {
                  borderRadius: 0,
                  fontFamily: "inherit",
                  fontFamilyCode: "--font-geist-sans",
                  colorPrimary: theme.button,
                  colorLink: theme.link,
                },
                components: {
                  Form: {
                    itemMarginBottom: 16,
                  },
                  Tabs: {
                    inkBarColor: theme.link,
                    itemActiveColor: theme.link,
                    itemColor: "#3E4958",
                    itemHoverColor: "#3E4958",
                    itemSelectedColor: theme.link,
                    titleFontSize: 16,
                    titleFontSizeLG: 20,
                    titleFontSizeSM: 16,
                  },
                  Table: {
                    cellPaddingInline: 8,
                    cellPaddingBlock: 4,
                  },
                  Descriptions: {
                    labelBg: "#f1f5f9",
                    titleColor: "#020618",
                  },
                },
              }}
            >
              {children}
              <Footer appName={appConfig?.name || APP_SETTINGS.title} />
            </ConfigProvider>
          </AntdRegistry>
          <div suppressHydrationWarning>
            <DynamicScript />
          </div>
        </AppContextProvider>
      </body>
    </html>
  );
}
