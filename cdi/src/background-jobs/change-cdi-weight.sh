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
    echo "Usage: $0 [--esi_weight=<value>] [--evi2_weight=<value>] [--spi_weight=<value>] [--sm_weight=<value>]"
    echo "Example: $0 --esi_weight=0.3 --evi2_weight=0.3 --spi_weight=0.4 --sm_weight=0.0"
    exit 1
}
# Check if arguments are provided and validate their naming
for arg in "$@"; do
    case $arg in
    --esi_weight=*|--lst_weight=*) ;;    # --lst_weight: legacy alias for ESI
    --evi2_weight=*|--ndvi_weight=*) ;;  # --ndvi_weight: legacy alias for EVI2
    --spi_weight=*) ;;
    --sm_weight=*) ;;
    *)
        echo "Invalid argument: $arg"
        usage
        ;;
    esac
done
# Initialize variables
ESI_WEIGHT=0.3
EVI2_WEIGHT=0.3
SPI_WEIGHT=0.4
SM_WEIGHT=0.0

# Parse command line arguments
for arg in "$@"; do
    case $arg in
    --esi_weight=*|--lst_weight=*)
        ESI_WEIGHT="${arg#*=}"
        ;;
    --evi2_weight=*|--ndvi_weight=*)
        EVI2_WEIGHT="${arg#*=}"
        ;;
    --spi_weight=*)
        SPI_WEIGHT="${arg#*=}"
        ;;
    --sm_weight=*)
        SM_WEIGHT="${arg#*=}"
        ;;
    *)
        usage
        ;;
    esac
done

# Check if all weights are provided
if [ -z "$ESI_WEIGHT" ] || [ -z "$EVI2_WEIGHT" ] || [ -z "$SPI_WEIGHT" ] || [ -z "$SM_WEIGHT" ]; then
    usage
fi
# Path to the config file
BASE_PATH=$(dirname "$(dirname "$(dirname "$(realpath "$0")")")")
CONFIG_FILE="$BASE_PATH/config/cdi_project_settings.json"
# Check if the config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Config file not found: $CONFIG_FILE"
    exit 1
fi
# Read the config file and update the weights
# Use jq to update the weights in the JSON config file
jq --arg esi "$ESI_WEIGHT" \
    --arg evi2 "$EVI2_WEIGHT" \
    --arg spi "$SPI_WEIGHT" \
    --arg sm "$SM_WEIGHT" \
    '.cdi_parameters.weights = {
        esi: ($esi | tonumber),
        evi2: ($evi2 | tonumber),
        spi: ($spi | tonumber),
        sm: ($sm | tonumber)
     }' \
    "$CONFIG_FILE" | jq . --indent 4 >tmp.$$.json && mv tmp.$$.json "$CONFIG_FILE"
# Check if the jq command was successful
if [ $? -ne 0 ]; then
    echo "Failed to update the config file."
    exit 1
fi
echo "Weights updated successfully in $CONFIG_FILE:"
echo "ESI Weight: $ESI_WEIGHT"
echo "EVI2 Weight: $EVI2_WEIGHT"
echo "SPI Weight: $SPI_WEIGHT"
echo "SM Weight: $SM_WEIGHT"
# Print the updated config file
echo "Updated config file:"
cat "$CONFIG_FILE"
# End of script
# Note: This script assumes that the config file is in JSON format and uses jq to parse and update it.
# Ensure jq is installed
# You can install jq using the following command:
# sudo apt-get install jq
# Or for MacOS:
# brew install jq
# Make sure to give execute permission to the script before running it:
# chmod +x change-weight.sh
# Run the script with the desired weights:
# ./change-weight.sh --lst_weight=0.5 --ndvi_weight=0.3 --spi_weight=0.1 --sm_weight=0.1
# This script is designed to be run in a Unix-like environment (Linux, macOS).
# It may not work as expected in Windows without a compatible shell or environment.
# Ensure you have the necessary permissions to modify the config file.
# If you encounter any issues, please check the script for errors or consult the documentation for your environment.
# This script is provided as-is without any warranty. Use it at your own risk.
# The author is not responsible for any damages or data loss resulting from the use of this script.
# Always back up your data before running scripts that modify files.