class PublicationStatus:
    in_review = 1
    in_validation = 2
    published = 3

    FieldStr = {
        in_review: "In Review",
        in_validation: "In Validation",
        published: "Published",
    }


class DroughtCategory:
    normal = 0
    d0 = 1
    d1 = 2
    d2 = 3
    d3 = 4
    d4 = 5
    none = -9999

    FieldStr = {
        normal: "Wet/normal conditions",
        d0: "D0 Abnormally Dry",
        d1: "D1 Moderate Drought",
        d2: "D2 Severe Drought",
        d3: "D3 Extreme Drought",
        d4: "D4 Exceptional Drought",
        none: "No Data",
    }


class CDIGeonodeCategory:
    cdi = "cdi-raster-map"
    spi = "spi-raster-map"
    ndvi = "ndvi-raster-map"
    lst = "lst-raster-map"

    FieldStr = {
        cdi: "CDI Raster Map",
        spi: "SPI Raster Map",
        ndvi: "NDVI Raster Map",
        lst: "LST Raster Map",
    }


class DroughtCategoryColor:
    normal = 0
    d0 = 1
    d1 = 2
    d2 = 3
    d3 = 4
    d4 = 5

    FieldStr = {
        normal: "#b9f8cf",
        d0: "#ffff00",
        d1: "#fbd47f",
        d2: "#ffaa00",
        d3: "#e60000",
        d4: "#730000",
    }


class ExportMapTypes:
    geojson = "geojson"
    shapefile = "shapefile"
    png = "png"
    svg = "svg"

    FieldStr = {
        geojson: "GeoJSON",
        shapefile: "Shapefile",
        png: "PNG",
        svg: "SVG",
    }
