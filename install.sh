#!/bin/bash

# Drought Map Hub Installation Script
# This script generates .env files for each component based on user inputs

set -e

echo "========================================"
echo "  Drought Map Hub Configuration Setup  "
echo "========================================"
echo

# Function to read input with default value
read_with_default() {
    local prompt="$1"
    local default="$2"
    local value
    
    if [ -n "$default" ]; then
        read -p "$prompt [$default]: " value
        echo "${value:-$default}"
    else
        read -p "$prompt: " value
        echo "$value"
    fi
}

# Function to validate latitude
validate_latitude() {
    local lat="$1"
    if ! [[ "$lat" =~ ^-?[0-9]+\.?[0-9]*$ ]] || (( $(echo "$lat < -90" | bc -l) )) || (( $(echo "$lat > 90" | bc -l) )); then
        echo "Invalid latitude. Must be between -90 and 90."
        return 1
    fi
    return 0
}

# Function to validate longitude
validate_longitude() {
    local lon="$1"
    if ! [[ "$lon" =~ ^-?[0-9]+\.?[0-9]*$ ]] || (( $(echo "$lon < -180" | bc -l) )) || (( $(echo "$lon > 180" | bc -l) )); then
        echo "Invalid longitude. Must be between -180 and 180."
        return 1
    fi
    return 0
}

# Function to validate URL format
validate_url() {
    local url="$1"
    if [[ ! "$url" =~ ^https?:// ]]; then
        echo "Invalid URL format. Must start with http:// or https://"
        return 1
    fi
    return 0
}

# Function to backup existing files
backup_file() {
    local file="$1"
    if [ -f "$file" ]; then
        cp "$file" "$file.backup.$(date +%Y%m%d_%H%M%S)"
        echo "Backed up existing $file"
    fi
}

echo "Please provide the following information to configure your Drought Map Hub:"
echo

# 1. Country Name
COUNTRY_NAME=$(read_with_default "1. Your Country" "Eswatini")

# 2. Technical Working Group
echo
echo "2. Technical Working Group (separate with comma)"
TWG_LIST=$(read_with_default "   Enter organizations" "NDMA, MoAg, MET, DWA, UNESWA (University of Eswatini)")

# 3. Country Boundaries
echo
echo "3. Your Country Boundaries:"
while true; do
    NORTH_LAT=$(read_with_default "   3.1 North latitude" "-25.675")
    if validate_latitude "$NORTH_LAT"; then
        break
    fi
done

while true; do
    SOUTH_LAT=$(read_with_default "   3.2 South latitude" "-27.825")
    if validate_latitude "$SOUTH_LAT"; then
        break
    fi
done

while true; do
    WEST_LON=$(read_with_default "   3.3 West longitude" "30.675")
    if validate_longitude "$WEST_LON"; then
        break
    fi
done

while true; do
    EAST_LON=$(read_with_default "   3.4 East longitude" "32.825")
    if validate_longitude "$EAST_LON"; then
        break
    fi
done

# 4. TopoJSON path location
echo
echo "4. TopoJSON file path"
TOPOJSON_PATH=$(read_with_default "   Path to your country's TopoJSON file" "")

# 5. Earth data credentials
echo
echo "5. Earth data credentials (for NASA data access)"
EARTHDATA_USERNAME=$(read_with_default "   5.1 Username" "")
EARTHDATA_PASSWORD=$(read_with_default "   5.2 Password" "")

# 6. Domain configuration
echo
echo "6. Domain Configuration"
while true; do
    DROUGHT_HUB_DOMAIN=$(read_with_default "   6.1 Drought-map Hub Domain" "http://localhost:3000")
    if validate_url "$DROUGHT_HUB_DOMAIN"; then
        break
    fi
done

while true; do
    GEONODE_DOMAIN=$(read_with_default "   6.2 Geonode Domain" "http://localhost")
    if validate_url "$GEONODE_DOMAIN"; then
        break
    fi
done

# 7. Service selection
echo
echo "7. Which services would you like to run? Choose by number 1-4 (default 1):"
echo "   1. All services"
echo "   2. Drought-Map Hub only"
echo "   3. CDI-Script only"
echo "   4. Geonode only"
while true; do
    SERVICE_CHOICE=$(read_with_default "   Enter your choice (1-4)" "1")
    if [[ "$SERVICE_CHOICE" =~ ^[1-4]$ ]]; then
        case $SERVICE_CHOICE in
            1) SERVICE_PARAM="all" ;;
            2) SERVICE_PARAM="app" ;;
            3) SERVICE_PARAM="cdi" ;;
            4) SERVICE_PARAM="geonode" ;;
        esac
        break
    else
        echo "Invalid choice. Please enter a number between 1 and 4."
    fi
done

# 8. Mode selection
echo
echo "8. Would you like to run in development or production mode? Choose by number 1-2 (default 1):"
echo "   1. Development mode"
echo "   2. Production mode"
while true; do
    MODE_CHOICE=$(read_with_default "   Enter your choice (1-2)" "1")
    if [[ "$MODE_CHOICE" =~ ^[1-2]$ ]]; then
        case $MODE_CHOICE in
            1) MODE_PARAM="dev" ;;
            2) MODE_PARAM="prod" ;;
        esac
        break
    else
        echo "Invalid choice. Please enter 1 or 2."
    fi
done

echo
echo "========================================"
echo "  Generating Configuration Files...     "
echo "========================================"

# Create app/.env
echo "Creating app/.env..."
backup_file "app/.env"
cat > app/.env << EOF
APP_COUNTRY_NAME="${COUNTRY_NAME}"
APP_TWG_LIST="['$(echo "$TWG_LIST" | sed "s/, /', '/g")']"
GEONODE_BASE_URL="${GEONODE_DOMAIN}"
GEONODE_ADMIN_USERNAME="youradminusernameoremail"
GEONODE_ADMIN_PASSWORD="youradminpassword"
EMAIL_HOST="smtp.gmail.com"
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER="your-email@example.com"
EMAIL_HOST_PASSWORD="your-email-password"
EMAIL_FROM="noreply@example.com"
WEBDOMAIN=${DROUGHT_HUB_DOMAIN}
SESSION_SECRET=$(openssl rand -base64 32)
SECRET_KEY=$(python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())' | sed 's/\$/\$\$/g')
RUNDECK_API_URL="http://localhost:4440/api/50"
RUNDECK_API_TOKEN=secret
CSRF_TRUSTED_ORIGINS="${DROUGHT_HUB_DOMAIN}"
EOF

# Create cdi/.env
echo "Creating cdi/.env..."
backup_file "cdi/.env"
cat > cdi/.env << EOF
DOWNLOAD_CHIRPS_BASE_URL="https://data.chc.ucsb.edu/products/CHIRPS-2.0/global_monthly/tifs/"
DOWNLOAD_CHIRPS_PATTERN=".tif.gz"
DOWNLOAD_SM_BASE_URL="https://hydro1.gesdisc.eosdis.nasa.gov/data/FLDAS/FLDAS_NOAH01_C_GL_M.001/"
DOWNLOAD_SM_PATTERN="FLDAS.*\.nc"
DOWNLOAD_LST_BASE_URL="https://e4ftl01.cr.usgs.gov/MOLT/MOD21C3.061/"
DOWNLOAD_LST_PATTERN=".hdf"
DOWNLOAD_NDVI_BASE_URL="https://e4ftl01.cr.usgs.gov/MOLT/MOD13C2.061/"
DOWNLOAD_NDVI_PATTERN=".hdf"
EARTHDATA_USERNAME="${EARTHDATA_USERNAME}"
EARTHDATA_PASSWORD="${EARTHDATA_PASSWORD}"
GEONODE_URL="${GEONODE_DOMAIN}"
GEONODE_USERNAME="yourgeonodeusernameoremail"
GEONODE_PASSWORD="yourgeonodepassword"
EOF

# Update cdi/config/cdi_project_settings.json
echo "Updating cdi/config/cdi_project_settings.json..."
backup_file "cdi/config/cdi_project_settings.json"
cat > cdi/config/cdi_project_settings.json << EOF
{
  "region_name": "${COUNTRY_NAME}",
  "bounds": {
    "n_lat": ${NORTH_LAT},
    "s_lat": ${SOUTH_LAT},
    "w_lon": ${WEST_LON},
    "e_lon": ${EAST_LON}
  },
  "spi_periods": [3],
  "cdi_parameters": {
    "names": {
      "lst": "lst_anom_pct_rank",
      "ndvi": "ndvi_anom_pct_rank",
      "spi": "spi_3_anom_pct_rank",
      "sm": "RootZone2_SM_pct_rank"
    },
    "weights": {
      "lst": 0.3,
      "ndvi": 0.3,
      "spi": 0.4,
      "sm": 0.0
    }
  },
  "map_template": "dmh_template.qpt",
  "map_project": "dmh_CDI.qgs"
}
EOF

# Create geonode/.env (copy from example and update as needed)
echo "Creating geonode/.env..."
backup_file "geonode/.env"
cp geonode/env.example geonode/.env

# Create traefik/.env
echo "Creating traefik/.env..."
backup_file "traefik/.env"
cat > traefik/.env << EOF
WEBDOMAIN=${DROUGHT_HUB_DOMAIN}
WEBDOMAIN_GEONODE=${GEONODE_DOMAIN}
EOF

# Handle TopoJSON file if provided
if [ -n "$TOPOJSON_PATH" ]; then
    if [ -f "$TOPOJSON_PATH" ]; then
        echo "Copying TopoJSON file to app/backend/source/country.topojson..."
        backup_file "app/backend/source/country.topojson"
        cp "$TOPOJSON_PATH" app/backend/source/country.topojson
        echo "TopoJSON file copied successfully."
    else
        echo "Warning: TopoJSON file not found at $TOPOJSON_PATH"
        echo "Please manually copy your TopoJSON file to app/backend/source/country.topojson"
    fi
else
    echo "No TopoJSON file provided. Please manually copy your TopoJSON file to app/backend/source/country.topojson"
fi

echo
echo "========================================"
echo "  Configuration Complete!               "
echo "========================================"
echo
echo "Configuration files created:"
echo "  ✓ app/.env"
echo "  ✓ cdi/.env"
echo "  ✓ cdi/config/cdi_project_settings.json"
echo "  ✓ geonode/.env"
echo "  ✓ traefik/.env"
echo
echo "Next steps:"
echo "  1. Review and update the generated .env files if needed"
echo "  2. Update EMAIL settings in app/.env"
echo "  3. Update GEONODE admin credentials in app/.env and cdi/.env"
echo "  4. Make sure your TopoJSON file is at app/backend/source/country.topojson"
echo "  5. Run your application using the appropriate startup script"
echo
echo "Note: Backup files were created for any existing configuration files."
echo

# Execute run.sh based on user choices
echo "========================================"
echo "  Starting Services...                  "
echo "========================================"
echo "Selected service: $SERVICE_PARAM"
echo "Selected mode: $MODE_PARAM"
echo

# Make run.sh executable if it isn't already
chmod +x ./run.sh

# Execute the run script
echo "Executing: ./run.sh mode=$MODE_PARAM service=$SERVICE_PARAM"
./run.sh mode=$MODE_PARAM service=$SERVICE_PARAM