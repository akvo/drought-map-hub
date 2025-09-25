#!/bin/bash

# Get the root directory of the project
root_path="$(dirname "$(dirname "$(dirname "$(realpath "$0")")")")"

skip_download=false

# Parse command line arguments
for arg in "$@"; do
    case $arg in
    --skip-download)
        skip_download=true
        echo "Skip download mode enabled"
        ;;
    *)
        echo "Unknown argument: $arg"
        echo "Usage: $0 [--skip-download]"
        exit 1
        ;;
    esac
done

# Load environment variables from .env file in the root directory
export $(grep -v '^#' "$root_path/.env" | xargs)

# Change to the directory of the script
cd "$(dirname "$0")"

source ./utils.sh
source ./job_00_login.sh
source ./job_01_check-dataset.sh
source ./job_02_extract-n-rename-chirps.sh
source ./job_03_run_cdi.sh
source ./job_04_upload_to_geonode.sh

# Exit if wget, pup, gunzip, and curl aren't available
for cmd in wget pup gunzip curl; do
    if ! command -v $cmd &>/dev/null; then
        echo "$cmd could not be found, please install it to proceed."
        exit 1
    fi
done
echo "All required commands are available."

# Function to get weight values from config file
get_weight_from_config() {
    local dataset_name="$1"
    local config_file="$root_path/config/cdi_project_settings.json"

    if [ ! -f "$config_file" ]; then
        echo "Config file not found: $config_file" >&2
        return 1
    fi

    # Extract weight value using jq
    local weight=$(jq -r ".cdi_parameters.weights.${dataset_name}" "$config_file" 2>/dev/null)

    if [ -z "$weight" ] || [ "$weight" = "null" ]; then
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

# Execute download commands only if --skip-download is not set
if [ "$skip_download" = false ]; then
    echo "Starting download phase..."
    login_and_download_cookies

    check_and_download_chirps_dataset
    extract_and_rename_chirps

    # Get weight values from config
    weight_lst=$(get_weight_from_config "lst")
    weight_ndvi=$(get_weight_from_config "ndvi")
    weight_sm=$(get_weight_from_config "sm")

    echo "Dataset weights from config: LST=$weight_lst, NDVI=$weight_ndvi, SM=$weight_sm"

    # Conditional dataset downloads based on weights
    if is_weight_positive "$weight_lst"; then
        echo "LST weight ($weight_lst) > 0, downloading LST dataset..."
        check_and_download_LST_dataset
    else
        echo "LST weight ($weight_lst) = 0, skipping LST dataset download"
    fi

    if is_weight_positive "$weight_ndvi"; then
        echo "NDVI weight ($weight_ndvi) > 0, downloading NDVI dataset..."
        check_and_download_NDVI_dataset
    else
        echo "NDVI weight ($weight_ndvi) = 0, skipping NDVI dataset download"
    fi

    if is_weight_positive "$weight_sm"; then
        echo "SM weight ($weight_sm) > 0, downloading SM dataset..."
        check_and_download_SM_dataset
    else
        echo "SM weight ($weight_sm) = 0, skipping SM dataset download"
    fi
else
    echo "Download phase skipped due to --skip-download flag"
fi

cleanup_output_data

run_cdi_scripts
upload_to_geonode
