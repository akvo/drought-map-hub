"use client";

import dynamic from "next/dynamic";

// The step-2 UI renders a Leaflet map and statically imports react-leaflet,
// which touches `window` when the module is evaluated. Load it client-side
// only (ssr: false) so the production build can prerender this route without
// hitting Leaflet's browser globals. Mirrors the map pattern used elsewhere
// (e.g. components/Map/Map.js, browse/compare pages).
const Step2Content = dynamic(() => import("./Step2Content"), { ssr: false });

const Step2Page = () => <Step2Content />;

export default Step2Page;
