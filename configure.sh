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

# Function to read masked input (shows '*' for each character)
read_with_mask() {
    local prompt="$1"
    local default="$2"
    local value
    local old_stty

    # If running in a non-interactive shell, fall back to default or empty
    if [ ! -t 0 ]; then
        if [ -n "$default" ]; then
            echo "$default"
        else
            echo ""
        fi
        return
    fi

    # Use /dev/tty for prompt and input so the question is visible even when
    # stdin/stdout are redirected (sensible for piped or subshell usage).
    local tty=/dev/tty
    if [ ! -c "$tty" ]; then
        tty=/dev/stdin
    fi

    if [ -n "$default" ]; then
        printf "%s [%s]: " "$prompt" "$default" > "$tty"
    else
        printf "%s: " "$prompt" > "$tty"
    fi

    # Save current stty settings and ensure restoration on exit/interrupt
    old_stty=$(stty -g < "$tty")
    trap 'stty "$old_stty" < "$tty"; echo > "$tty"; exit' INT TERM

    # Disable echo but keep canonical mode so pasted input arrives at once
    stty -echo < "$tty"
    # Read the whole line (supports paste). Use IFS= to preserve spaces.
    IFS= read -r value < "$tty"

    # Restore stty
    stty "$old_stty" < "$tty"
    trap - INT TERM
    echo > "$tty"

    # If user entered nothing and default exists, use default
    if [ -z "$value" ] && [ -n "$default" ]; then
        echo "$default"
    else
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


# 1. Email configuration
echo
echo "1. Email Configuration:"
EMAIL_HOST=$(read_with_default "   1.1 EMAIL_HOST" "smtp.gmail.com")
EMAIL_PORT=$(read_with_default "   1.2 EMAIL_PORT" "587")
EMAIL_USE_TLS=$(read_with_default "   1.3 EMAIL_USE_TLS" "True")
EMAIL_HOST_USER=$(read_with_mask "   1.4 EMAIL_HOST_USER" "your-email@example.com")
EMAIL_HOST_PASSWORD=$(read_with_mask "   1.5 EMAIL_HOST_PASSWORD" "your-email-password")
EMAIL_FROM=$(read_with_default "   1.6 EMAIL_FROM" "noreply@example.com")

# 2. Earth data credentials (for NASA data access)
echo
echo "2. Earth data credentials (for NASA data access)"
EARTHDATA_USERNAME=$(read_with_default "   2.1 Username" "")
EARTHDATA_PASSWORD=$(read_with_mask "   2.2 Password" "")

# 3. Domain configuration
echo
echo "3. Domain Configuration"
while true; do
    DROUGHT_HUB_DOMAIN=$(read_with_default "   3.1 Drought-map Hub Domain" "http://localhost:3000")
    if validate_url "$DROUGHT_HUB_DOMAIN"; then
        break
    fi
done

while true; do
    GEONODE_DOMAIN=$(read_with_default "   3.2 Geonode Domain" "http://localhost")
    if validate_url "$GEONODE_DOMAIN"; then
        break
    fi
done

# Set default GEONODE_HOST based on domain or use default
GEONODE_HOST=$(echo "$GEONODE_DOMAIN" | sed 's|.*://||' | sed 's|/.*||')

# 4. Service selection
echo
echo "4. Which services would you like to run? Choose by number 1-4 (default 1):"
echo "   1. All services"
echo "   2. Drought-Map Hub only"
echo "   3. CDI-Script only"
echo "   4. Geonode only"

while true; do
    SERVICE_CHOICE=$(read_with_default "   Enter your choice (1-4)" "1")
    if [[ "$SERVICE_CHOICE" =~ ^[1-4]$ ]]; then
        case $SERVICE_CHOICE in
            1) SERVICE_PARAM="all" ;;
            2)
                SERVICE_PARAM="app"
                echo
                echo "App service selected. Please provide Geonode instance configuration:"
                GEONODE_BASE_URL=$(read_with_default "   Geonode Base URL" "http://localhost")
                # Set default GEONODE_HOST based on GEONODE_BASE_URL or use default
                GEONODE_HOST=$(echo "$GEONODE_BASE_URL" | sed 's|.*://||' | sed 's|/.*||')
                GEONODE_ADMIN_USERNAME=$(read_with_default "   Geonode Admin Username" "admin")
                GEONODE_ADMIN_PASSWORD=$(read_with_mask "   Geonode Admin Password" "youradminpassword")
                ;;
            3)
                SERVICE_PARAM="cdi"
                echo
                echo "CDI service selected. Please provide Geonode instance configuration:"
                GEONODE_URL=$(read_with_default "   Geonode URL" "http://localhost")
                GEONODE_USERNAME=$(read_with_default "   Geonode Username" "admin")
                GEONODE_PASSWORD=$(read_with_mask "   Geonode Password" "yourgeonodepassword")
                ;;
            4) SERVICE_PARAM="geonode" ;;
        esac
        break
    else
        echo "Invalid choice. Please enter a number between 1 and 4."
    fi
done

# 5. Mode selection
echo
echo "5. Would you like to run in development or production mode? Choose by number 1-2 (default 1):"
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

# Generate strong password for PostgreSQL
POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)


# Create app/.env
echo "Creating app/.env..."
backup_file "app/.env"
cat > app/.env << EOF
GEONODE_BASE_URL="${GEONODE_BASE_URL:-$GEONODE_DOMAIN}"
GEONODE_HOST="${GEONODE_HOST:-$(echo "$GEONODE_DOMAIN" | sed 's|.*://||' | sed 's|/.*||')}"
GEONODE_ADMIN_USERNAME="${GEONODE_ADMIN_USERNAME:-admin}"
GEONODE_ADMIN_PASSWORD="${GEONODE_ADMIN_PASSWORD:-youradminpassword}"
EMAIL_HOST="${EMAIL_HOST}"
EMAIL_PORT=${EMAIL_PORT}
EMAIL_USE_TLS=${EMAIL_USE_TLS}
EMAIL_HOST_USER="${EMAIL_HOST_USER}"
EMAIL_HOST_PASSWORD="${EMAIL_HOST_PASSWORD}"
EMAIL_FROM="${EMAIL_FROM}"
WEBDOMAIN=${DROUGHT_HUB_DOMAIN}
SESSION_SECRET=$(openssl rand -base64 32)
SECRET_KEY=$(python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())' | sed 's/\$/\$\$/g')
RUNDECK_API_URL="http://localhost:4440/api/50"
RUNDECK_API_TOKEN=placeholder_will_be_updated_by_rundeck
CSRF_TRUSTED_ORIGINS="${DROUGHT_HUB_DOMAIN}"
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
DB_HOST=db
DB_PASSWORD=${POSTGRES_PASSWORD}
DB_SCHEMA=drought_map_hub
DB_USER=akvo
DEBUG=False
SETUP_SECRET_KEY=$(openssl rand -base64 16)
EOF

# Generate strong password for Rundeck
RUNDECK_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)

# Create app/rundeck.env
echo "Creating app/rundeck.env..."
backup_file "app/rundeck.env"
cat > app/rundeck.env << EOF
RUNDECK_GRAILS_URL=http://localhost:4440
RD_URL=http://localhost:4440
RD_USER=admin
RD_PASSWORD=${RUNDECK_PASSWORD}
RUNDECK_MAIL_SMTP_HOST=${EMAIL_HOST}
RUNDECK_MAIL_SMTP_PORT=${EMAIL_PORT}
RUNDECK_MAIL_SMTP_USERNAME=${EMAIL_HOST_USER}
RUNDECK_MAIL_SMTP_PASSWORD=${EMAIL_HOST_PASSWORD}
RUNDECK_MAIL_FROM=${EMAIL_FROM}
EOF

# Create app/rundeck/realm.properties
echo "Creating app/rundeck/realm.properties..."
backup_file "app/rundeck/realm.properties"
cat > app/rundeck/realm.properties << EOF
admin:${RUNDECK_PASSWORD},user,admin
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
GEONODE_URL="${GEONODE_URL:-$GEONODE_DOMAIN}"
GEONODE_USERNAME="${GEONODE_USERNAME:-admin}"
GEONODE_PASSWORD="${GEONODE_PASSWORD:-yourgeonodepassword}"
EOF

echo "Updating cdi/config/cdi_project_settings.json..."
backup_file "cdi/config/cdi_project_settings.json"
cat > cdi/config/cdi_project_settings.json << EOF
{
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

# Create geonode/.env using Python script
echo "Creating geonode/.env..."
backup_file "geonode/.env"
echo "y" | python ./geonode/create-envfile.py

# Create traefik/.env
echo "Creating traefik/.env..."
backup_file "traefik/.env"
cat > traefik/.env << EOF
WEBDOMAIN=${DROUGHT_HUB_DOMAIN}
WEBDOMAIN_GEONODE=${GEONODE_DOMAIN}
EOF


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
echo "  4. Run your application using the appropriate startup script"
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