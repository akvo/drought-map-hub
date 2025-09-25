#!/bin/bash
# Function to display usage information
# Check jq is installed
if ! command -v jq &> /dev/null; then
    echo "jq could not be found. Please install jq to run this script."
    exit 1
fi

# Function to display usage information
# This function displays the usage information for the script
# and exits the script with a non-zero status.
usage() {
    echo "Usage: $0 [--n_lat=<value>] [--s_lat=<value>] [--w_lon=<value>] [--e_lon=<value>] [--region_name=<value>]"
    echo "Example: $0 --n_lat=26.675 --s_lat=20.825 --w_lon=87.975 --e_lon=92.675 --region_name=Bangladesh"
    echo ""
    echo "Parameters:"
    echo "  --n_lat      North latitude boundary"
    echo "  --s_lat      South latitude boundary"
    echo "  --w_lon      West longitude boundary"
    echo "  --e_lon      East longitude boundary"
    echo "  --region_name Region name (optional, defaults to current value)"
    exit 1
}

# Check if arguments are provided and validate their naming
for arg in "$@"; do
    case $arg in
    --n_lat=*) ;;
    --s_lat=*) ;;
    --w_lon=*) ;;
    --e_lon=*) ;;
    --region_name=*) ;;
    *)
        echo "Invalid argument: $arg"
        usage
        ;;
    esac
done

# Initialize variables with current values from config
BASE_PATH=$(dirname "$(dirname "$(dirname "$(realpath "$0")")")")
CONFIG_FILE="$BASE_PATH/config/cdi_project_settings.json"

# Check if the config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Config file not found: $CONFIG_FILE"
    exit 1
fi

# Get current values from config file
N_LAT=$(jq -r '.bounds.n_lat' "$CONFIG_FILE")
S_LAT=$(jq -r '.bounds.s_lat' "$CONFIG_FILE")
W_LON=$(jq -r '.bounds.w_lon' "$CONFIG_FILE")
E_LON=$(jq -r '.bounds.e_lon' "$CONFIG_FILE")
REGION_NAME=$(jq -r '.region_name' "$CONFIG_FILE")

# Parse command line arguments
for arg in "$@"; do
    case $arg in
    --n_lat=*)
        N_LAT="${arg#*=}"
        ;;
    --s_lat=*)
        S_LAT="${arg#*=}"
        ;;
    --w_lon=*)
        W_LON="${arg#*=}"
        ;;
    --e_lon=*)
        E_LON="${arg#*=}"
        ;;
    --region_name=*)
        REGION_NAME="${arg#*=}"
        ;;
    *)
        usage
        ;;
    esac
done

# Validate that we have all required bounds values
if [ -z "$N_LAT" ] || [ -z "$S_LAT" ] || [ -z "$W_LON" ] || [ -z "$E_LON" ]; then
    echo "Error: Missing required boundary values"
    usage
fi

# Validate numeric values
if ! [[ "$N_LAT" =~ ^-?[0-9]+(\.[0-9]+)?$ ]] || \
   ! [[ "$S_LAT" =~ ^-?[0-9]+(\.[0-9]+)?$ ]] || \
   ! [[ "$W_LON" =~ ^-?[0-9]+(\.[0-9]+)?$ ]] || \
   ! [[ "$E_LON" =~ ^-?[0-9]+(\.[0-9]+)?$ ]]; then
    echo "Error: All boundary values must be valid numbers"
    exit 1
fi

# Validate logical bounds
if (( $(echo "$N_LAT <= $S_LAT" | bc -l) )); then
    echo "Error: North latitude ($N_LAT) must be greater than south latitude ($S_LAT)"
    exit 1
fi

if (( $(echo "$E_LON <= $W_LON" | bc -l) )); then
    echo "Error: East longitude ($E_LON) must be greater than west longitude ($W_LON)"
    exit 1
fi

# Validate latitude range (-90 to 90)
if (( $(echo "$N_LAT < -90 || $N_LAT > 90" | bc -l) )) || \
   (( $(echo "$S_LAT < -90 || $S_LAT > 90" | bc -l) )); then
    echo "Error: Latitude values must be between -90 and 90"
    exit 1
fi

# Validate longitude range (-180 to 180)
if (( $(echo "$W_LON < -180 || $W_LON > 180" | bc -l) )) || \
   (( $(echo "$E_LON < -180 || $E_LON > 180" | bc -l) )); then
    echo "Error: Longitude values must be between -180 and 180"
    exit 1
fi

echo "Updating bounds in config file..."
echo "Current bounds:"
jq -r '.bounds' "$CONFIG_FILE"

# Read the config file and update the bounds and region name
# Use jq to update the bounds in the JSON config file
jq --arg n_lat "$N_LAT" \
    --arg s_lat "$S_LAT" \
    --arg w_lon "$W_LON" \
    --arg e_lon "$E_LON" \
    --arg region_name "$REGION_NAME" \
    '.bounds.n_lat = ($n_lat | tonumber) | 
     .bounds.s_lat = ($s_lat | tonumber) | 
     .bounds.w_lon = ($w_lon | tonumber) | 
     .bounds.e_lon = ($e_lon | tonumber) |
     .region_name = $region_name' \
    "$CONFIG_FILE" | jq . --indent 2 >tmp.$$.json && mv tmp.$$.json "$CONFIG_FILE"

# Check if the jq command was successful
if [ $? -ne 0 ]; then
    echo "Failed to update the config file."
    exit 1
fi

echo "Bounds updated successfully in $CONFIG_FILE:"
echo "Region Name: $REGION_NAME"
echo "North Latitude: $N_LAT"
echo "South Latitude: $S_LAT"
echo "West Longitude: $W_LON"
echo "East Longitude: $E_LON"

# Print the updated bounds from config file
echo ""
echo "Updated bounds in config file:"
jq -r '.bounds' "$CONFIG_FILE"

# End of script
# Note: This script assumes that the config file is in JSON format and uses jq to parse and update it.
# Ensure jq is installed and bc (basic calculator) is available for numeric validation
# You can install jq using the following command:
# sudo apt-get install jq bc
# Or for MacOS:
# brew install jq bc
# Make sure to give execute permission to the script before running it:
# chmod +x change-cdi-bounds.sh
# Run the script with the desired bounds:
# ./change-cdi-bounds.sh --n_lat=26.675 --s_lat=20.825 --w_lon=87.975 --e_lon=92.675 --region_name=Bangladesh
# This script is designed to be run in a Unix-like environment (Linux, macOS).
# It may not work as expected in Windows without a compatible shell or environment.
# Ensure you have the necessary permissions to modify the config file.
# If you encounter any issues, please check the script for errors or consult the documentation for your environment.
# This script is provided as-is without any warranty. Use it at your own risk.
# The author is not responsible for any damages or data loss resulting from the use of this script.
# Always back up your data before running scripts that modify files.