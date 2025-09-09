export const DEFAULT_CENTER = [-26.573789513879785, 31.626892089843754];

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
  })
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
  copy: "Eswatini National Disaster Management Agency",
  title: "Eswatini Drought Monitor",
  about:
    "The Eswatini Drought Monitor is developed through a collaboration between the National Disaster Management Agency of Eswatini, the Ministry of Agriculture, and the Eswatini Meteorological Service.",
};

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
    value: "ndvi-raster-map",
    label: "NDVI Raster Map",
  },
  {
    value: "lst-raster-map",
    label: "LST Raster Map",
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

export const TWG_LOGOS = [
  {
    id: 1,
    image: "/images/logo-ndma.jpg",
    alt: "National Disaster Management Agency",
    url: "https://ndma.org.sz/",
  },
  {
    id: 2,
    image: "/images/logo-moag.png",
    alt: "MoAg (Ministry of Agriculture)",
    url: "https://www.gov.sz/index.php/ministries-departments/ministry-of-agriculture",
  },
  {
    id: 3,
    image: "/images/logo-dwa.png",
    alt: "DWA (Department of Water Affairs)",
    url: "https://www.gov.sz/index.php/ministries-departments/ministry-of-natural-resources",
  },
  {
    id: 4,
    image: "/images/logo-met-1.png",
    alt: "MET (Meteorological Office) 1",
    url: "https://www.swazimet.gov.sz/",
  },
  {
    id: 5,
    image: "/images/logo-met-2.jpg",
    alt: "MET (Meteorological Office) 2",
    url: "https://www.uneswa.sz/",
  },
];
