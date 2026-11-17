import path from "path";
import { fileURLToPath } from "url";
import CopyPlugin from "copy-webpack-plugin";

/** @type {import('next').NextConfig} */

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Build the next/image remotePattern for GeoNode-hosted uploads from
// GEONODE_BASE_URL. Required at build time; fail with a clear, actionable
// message instead of Next's cryptic "hostname is missing" validation error.
const geonodeImagePattern = () => {
  const base = process.env.GEONODE_BASE_URL;
  if (!base) {
    throw new Error(
      "GEONODE_BASE_URL is not set. The frontend build needs it (next/image " +
        "remotePatterns) and the app needs it at runtime. Set it to the GeoNode " +
        "base URL including scheme, e.g. https://geonode.example.org.",
    );
  }
  let url;
  try {
    url = new URL(base);
  } catch {
    throw new Error(
      `GEONODE_BASE_URL is not a valid URL: "${base}". ` +
        "Expected a full URL with scheme, e.g. https://geonode.example.org.",
    );
  }
  return {
    protocol: url.protocol.replace(/:$/, ""),
    hostname: url.hostname,
    port: url.port,
    pathname: "/uploaded/**",
    search: "",
  };
};

const nextConfig = {
  reactStrictMode: true,
  webpack: (config) => {
    config.plugins.push(
      new CopyPlugin({
        patterns: [
          {
            from: "node_modules/leaflet/dist/images",
            to: path.resolve(__dirname, "public", "leaflet", "images"),
          },
          {
            from: path.join(__dirname, "node_modules/tinymce/skins"),
            to: path.join(__dirname, "public/assets/libs/tinymce/skins"),
          },
          {
            from: path.join(__dirname, "node_modules/tinymce/themes"),
            to: path.join(__dirname, "public/assets/libs/tinymce/themes"),
          },
          {
            from: path.join(__dirname, "node_modules/tinymce/icons"),
            to: path.join(__dirname, "public/assets/libs/tinymce/icons"),
          },
          {
            from: path.join(__dirname, "node_modules/tinymce/plugins"),
            to: path.join(__dirname, "public/assets/libs/tinymce/plugins"),
          },
          {
            from: path.join(__dirname, "node_modules/tinymce/models"),
            to: path.join(__dirname, "public/assets/libs/tinymce/models"),
          },
        ],
      })
    );
    return config;
  },
  images: {
    remotePatterns: [geonodeImagePattern()],
  },
};

export default nextConfig;
