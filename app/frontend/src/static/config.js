export const DEFAULT_CENTER = [0, 0];

export const USER_ROLES = {
  admin: 1,
  reviewer: 2,
};

export const HOME_PAGE = {
  [USER_ROLES.admin]: "/publications",
  [USER_ROLES.reviewer]: "/reviews",
};

export const PAGE_SIZE = 10;

export const DROUGHT_CATEGORY_VALUE = {
  normal: 0,
  d0: 1,
  d1: 2,
  d2: 3,
  d3: 4,
  d4: 5,
  none: -9999,
};

export const DROUGHT_CATEGORY_COLOR = {
  [DROUGHT_CATEGORY_VALUE.normal]: "#b9f8cf",
  [DROUGHT_CATEGORY_VALUE.d0]: "#ffff00",
  [DROUGHT_CATEGORY_VALUE.d1]: "#fbd47f",
  [DROUGHT_CATEGORY_VALUE.d2]: "#ffaa00",
  [DROUGHT_CATEGORY_VALUE.d3]: "#e60000",
  [DROUGHT_CATEGORY_VALUE.d4]: "#730000",
  [DROUGHT_CATEGORY_VALUE.none]: "#ffffff",
};

export const DROUGHT_CATEGORY_LABEL = {
  [DROUGHT_CATEGORY_VALUE.normal]: "Wet/normal conditions",
  [DROUGHT_CATEGORY_VALUE.d0]: "D0 Abnormally Dry",
  [DROUGHT_CATEGORY_VALUE.d1]: "D1 Moderate Drought",
  [DROUGHT_CATEGORY_VALUE.d2]: "D2 Severe Drought",
  [DROUGHT_CATEGORY_VALUE.d3]: "D3 Extreme Drought",
  [DROUGHT_CATEGORY_VALUE.d4]: "D4 Exceptional Drought",
  [DROUGHT_CATEGORY_VALUE.none]: "No Data",
};

export const DROUGHT_CATEGORY = Object.values(DROUGHT_CATEGORY_VALUE).map(
  (v) => ({
    value: v,
    label: DROUGHT_CATEGORY_LABEL[v],
    color: DROUGHT_CATEGORY_COLOR[v],
  }),
);

export const PUBLICATION_STATUS = {
  in_review: 1,
  in_validation: 2,
  published: 3,
};

export const PUBLICATION_STATUS_OPTIONS = [
  {
    value: PUBLICATION_STATUS.in_review,
    label: "In Review",
    color: "orange",
  },
  {
    value: PUBLICATION_STATUS.in_validation,
    label: "In Validation",
    color: "blue",
  },
  {
    value: PUBLICATION_STATUS.published,
    label: "Published",
    color: "green",
  },
];

export const REVIEWER_MAP_FILTER = [
  {
    value: "reviewed",
    label: "Suggested/Approved Values",
  },
  {
    value: "raw",
    label: "Computed Values",
  },
];

export const CREATE_PUBLICATION_MAIL = {
  subject: "CDI Map review requested for month",
  message: `<p>Dear {{reviewer_name}}, The CDI Map for the month of {{year_month}} is available for review. Please submit your review by {{due_date}}.</p>`,
};

export const APP_SETTINGS = {
  title: "DroughtMap Hub",
  about:
    "The DroughtMap Hub is a platform designed to provide streamlined, user-friendly, and validated Combined Drought Indicator (CDI) products. It enhances drought monitoring capabilities by automating data management and promoting public access to critical information.",
};

// DIH-9: curated brand themes for the setup wizard. Each theme sets every
// colour explicitly (no runtime colour maths) so it stays readable and easy
// to maintain. To add a theme later, append one object with the same keys:
//   background  bar (header/footer/badge) background
//   foreground  text + icons sitting on `background`
//   active      active menu item background
//   button      primary buttons (label uses `foreground`)
//   link        links + brand headings on white
// The backend stores only the chosen theme `name` (SiteConfig.theme); the
// frontend resolves the full colour set via resolveTheme().
export const THEME_PRESETS = [
  {
    name: "Ocean Blue",
    background: "#3E5EB9",
    foreground: "#FFFFFF",
    active: "#2A4287",
    button: "#3E5EB9",
    link: "#3E5EB9",
  },
  {
    name: "Indigo",
    background: "#4338CA",
    foreground: "#FFFFFF",
    active: "#312E81",
    button: "#4338CA",
    link: "#4338CA",
  },
  {
    name: "Teal",
    background: "#0F766E",
    foreground: "#FFFFFF",
    active: "#0B5A54",
    button: "#0F766E",
    link: "#0F766E",
  },
  {
    name: "Forest",
    background: "#15803D",
    foreground: "#FFFFFF",
    active: "#0F5F2D",
    button: "#15803D",
    link: "#15803D",
  },
  {
    name: "Maroon",
    background: "#9F1239",
    foreground: "#FFFFFF",
    active: "#7A0E2C",
    button: "#9F1239",
    link: "#9F1239",
  },
  {
    name: "Slate",
    background: "#334155",
    foreground: "#FFFFFF",
    active: "#1E293B",
    button: "#334155",
    link: "#334155",
  },
];
export const DEFAULT_THEME = THEME_PRESETS[0];

export const RUNDECK_JOB_STATUS_COLOR = {
  succeeded: "green",
  failed: "red",
  aborted: "orange",
  running: "blue",
};

export const MAP_CATEGORY_OPTIONS = [
  {
    value: "cdi-raster-map",
    label: "CDI Raster Map",
  },
  {
    value: "spi-raster-map",
    label: "SPI Raster Map",
  },
  {
    value: "evi2-raster-map",
    label: "EVI2 Raster Map",
  },
  {
    value: "esi-raster-map",
    label: "ESI Raster Map",
  },
];

export const EXPORT_FORMAT_OPTIONS = [
  {
    key: "geojson",
    label: "GeoJSON",
  },
  {
    key: "shapefile",
    label: "Shapefile",
  },
  {
    key: "png",
    label: "Image (.PNG)",
  },
  {
    key: "svg",
    label: "Image (.SVG)",
  },
];

export const PUBLIC_MENU_ITEMS = [
  {
    url: "/",
    label: "Home",
  },
  {
    url: "/browse",
    label: "Browse",
  },
  {
    url: "/compare",
    label: "Compare",
  },
  {
    url: "/about",
    label: "About",
  },
];

export const TWG_OPTIONS = [
  {
    value: 1,
    label: "NDMA (National Disaster Management Agency)",
  },
  {
    value: 2,
    label: "MoAg (Ministry of Agriculture)",
  },
  {
    value: 3,
    label: "MET (Meteorological Office)",
  },
  {
    value: 4,
    label: "DWA (Department of Water Affairs)",
  },
  {
    value: 5,
    label: "UNESWA (University of Eswatini)",
  },
];

export const DEFAULT_MAP_HEIGHT = 48;

export const DEFAULT_CDI_WEIGHTS = {
  lst: 0.3,
  ndvi: 0.3,
  spi: 0.4,
  sm: 0.0,
};
