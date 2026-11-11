#!/bin/bash

# Processing mode: "recent" (last 2 years, for post-refactor validation) or
# "all" (full 2012-present history, for VM production deployment).
MODE=${1:-recent}

# Get the root directory of the project
root_path="$(dirname "$(dirname "$(dirname "$(realpath "$0")")")")"

# Load environment variables from .env file in the root directory
export $(grep -v '^#' "$root_path/.env" | xargs)

# Change to the directory of the script
cd "$(dirname "$0")"

# Ensure scaffolding dirs exist (container builds / prod named volumes start empty).
mkdir -p ../../logs ../../input_data ../../output_data

# Host runs (Rundeck + venv) don't get the docker bind-mount that maps
# config/cdi_project_settings.json onto the scripts' .conf, so region/bounds/
# weights would stay stale. Sync it here so there's one source of truth
# regardless of how the pipeline is launched (host or container).
client_conf="$root_path/config/cdi_project_settings.json"
runtime_conf="$root_path/src/cdi-scripts/cdi_project_settings.conf"
if [ -f "$client_conf" ] && ! cmp -s "$client_conf" "$runtime_conf"; then
    cp "$client_conf" "$runtime_conf"
    echo "Synced client config -> cdi_project_settings.conf"
fi

source ./utils.sh
source ./job_01_check-dataset.sh
source ./job_03_run_cdi.sh
source ./job_04_upload_to_geonode.sh
source ./job_05_sync_to_portal.sh

echo "Running pipeline in MODE=${MODE}"

# Exit if wget, pup, and curl aren't available
for cmd in wget pup curl; do
    if ! command -v $cmd &>/dev/null; then
        echo "$cmd could not be found, please install it to proceed."
        exit 1
    fi
done
echo "All required commands are available."

# Function to get weight values from config file
get_weight_from_config() {
    local dataset_name="$1"
    local config_file="$root_path/src/cdi-scripts/cdi_project_settings.conf"

    if [ ! -f "$config_file" ]; then
        echo "Config file not found: $config_file" >&2
        return 1
    fi

    # Extract weight value using grep and sed
    local weight=$(grep -A 10 '"weights"' "$config_file" | grep "\"$dataset_name\"" | sed 's/.*: *\([0-9.]*\).*/\1/')

    if [ -z "$weight" ]; then
        echo "0"
    else
        echo "$weight"
    fi
}

# Function to check if weight is greater than 0
is_weight_positive() {
    local weight="$1"
    # Use awk to handle floating point comparison
    awk -v w="$weight" 'BEGIN { exit (w <= 0) }'
}

# Get weight values from config
weight_esi=$(get_weight_from_config "esi")
weight_evi2=$(get_weight_from_config "evi2")
weight_spi=$(get_weight_from_config "spi")
weight_sm=$(get_weight_from_config "sm")

echo "Dataset weights from config: ESI=$weight_esi, EVI2=$weight_evi2, SPI=$weight_spi, SM=$weight_sm"

# Conditional dataset downloads based on weights (datasets with weight 0 are skipped)
if is_weight_positive "$weight_esi"; then
    echo "ESI weight ($weight_esi) > 0, downloading ESI dataset..."
    check_and_download_ESI_dataset "$MODE"
else
    echo "ESI weight ($weight_esi) = 0, skipping ESI dataset download"
fi

if is_weight_positive "$weight_evi2"; then
    echo "EVI2 weight ($weight_evi2) > 0, downloading EVI2 dataset..."
    check_and_download_EVI2_dataset "$MODE"
else
    echo "EVI2 weight ($weight_evi2) = 0, skipping EVI2 dataset download"
fi

if is_weight_positive "$weight_spi"; then
    echo "SPI weight ($weight_spi) > 0, downloading SPI dataset..."
    check_and_download_SPI_dataset "$MODE"
else
    echo "SPI weight ($weight_spi) = 0, skipping SPI dataset download"
fi

if is_weight_positive "$weight_sm"; then
    echo "SM weight ($weight_sm) > 0, downloading SM dataset..."
    check_and_download_SM_dataset "$MODE"
else
    echo "SM weight ($weight_sm) = 0, skipping SM dataset download"
fi

cleanup_output_data

run_cdi_scripts "$MODE"

# A failed upload (e.g. GeoNode briefly down) must not skip the portal sync:
# whatever GeoNode already holds should still reach the hub. Record the
# failure, run the sync, then exit non-zero so the run is still flagged.
upload_to_geonode || upload_failed=1
sync_geonode_to_portal

if [ -n "${upload_failed:-}" ]; then
    echo "Pipeline finished, but GeoNode upload had failures (see ../../logs/upload_failures.json)."
    exit 1
fi
