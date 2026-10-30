#!/bin/bash

# Get the root directory of the project
root_path="$(dirname "$(dirname "$(dirname "$(realpath "$0")")")")"

# Load environment variables from .env file in the root directory
export $(grep -v '^#' "$root_path/.env" | xargs)

# Change to the directory of the script
cd "$(dirname "$0")"

# Check that the external datasets for updates
# If data for the previous month is available, the data is downloaded and moved into the appropriate folder
# The NDMC scripts are run only if all datasets are updated to the previous month
# If data is missing, the NDMC scripts are not run and the missing data message is sent (see below)
# Upon completion of the NDMC script, the aggregation script is run
# Upon completion of the aggregation script, the outputs (NDMC + aggregation) are uploaded to the GeoNode
# A success message is sent upon successful completion of the entire process

# check_and_download_chirps_dataset
# check_and_download_LST_dataset
# check_and_download_NDVI_dataset
# check_and_download_SM_dataset

dataset_is_completed=False

notify_rundeck() {
    local message="$1"
    # Replace with the actual Rundeck notification command (e.g., API call, email, webhook, etc.)
    echo "Rundeck Notification: $message"
}

chirps_dataset_is_updated() {
    true
}

LST_dataset_is_updated() {
    SOME_CONDITION=false
    if [ "$SOME_CONDITION" = "true" ]; then
        return 1
    else
        return 0
    fi
}

NDVI_dataset_is_updated() {
    true
}

SM_dataset_is_updated() {
    true
}

run_cdi_scripts() {
    # source ~/.myenv/bin/activate
    python3 -u ../cdi-scripts/STEP_0000_execute_all_steps.py
    if [[ $? -ne 0 ]]; then
        notify_rundeck "CDI script execution failed!"
        exit 1
    fi
    # deactivate
}

run_aggregation_script() {
    echo "Aggregation start!"
    sleep 5
    echo "Aggregation End"
}

upload_outputs () {
    sleep 10
    echo "GeoTiffs successfully uploaded!"
}

send_success_message() {
    echo "send an email: Success!"
}

send_missing_data_message() {
    echo "create log and attach it to the email"
}

if chirps_dataset_is_updated && LST_dataset_is_updated && NDVI_dataset_is_updated && SM_dataset_is_updated; then
    dataset_is_completed=True
fi

if [ "$dataset_is_completed" = "True" ]; then
    # Run the NDMC scripts
    run_cdi_scripts
    # Run the aggregation script
    run_aggregation_script
    # Upload the outputs to the GeoNode
    upload_outputs
    # Send a success message
    send_success_message
else
    # Send a missing data message
    send_missing_data_message
fi
