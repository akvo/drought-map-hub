#!/bin/bash

# Get the root directory of the project (cdi folder)
root_path="$(dirname "$(dirname "$(dirname "$(realpath "$0")")")")"

check_and_download_chirps_dataset() {
    printf "\n===Check and download CHIRPS dataset===\n\n"
    remove_tmp_files "$root_path/input_data/CHIRPS"

    # Check if all-CHIRPS.log exists
    if [ ! -f "$root_path/logs/all-CHIRPS.log" ]; then
        touch "$root_path/logs/all-CHIRPS.log"
    fi

    LOG_IS_EMPTY=$(cat "$root_path/logs/all-CHIRPS.log" | wc -l)

    # If the log file is empty or the last line is 2 previous months
    # based on this pattern chirps-v2.0.{year}.{month}.tif.gz
    # then update the log file

    # Check what's being extracted from the last line
    l_chirp_date="$(tail -n 1 "$root_path/logs/all-CHIRPS.log" | cut -d '.' -f 3,4)"
    current_date="$(date -d "1 month ago" "+%Y.%m")"

    if [ "$LOG_IS_EMPTY" -eq 0 ] || [ "$l_chirp_date" \< "$current_date" ]; then
        echo "Downloading list of available CHIRPS data and saving to log"
        curl -s "${DOWNLOAD_CHIRPS_BASE_URL}" \
            | grep "${DOWNLOAD_CHIRPS_PATTERN}" \
            | pup \
            | grep -v "href" \
            | grep "${DOWNLOAD_CHIRPS_PATTERN}" \
            | sed "s/\ //g" > "$root_path/logs/all-CHIRPS.log"
    fi

    if ls $root_path/input_data/CHIRPS/*.tif* 1> /dev/null 2>&1; then
        num_files_in_dir=$(get_num_files_in_dir "$root_path/input_data/CHIRPS")
        num_files_in_log=$(get_num_files_in_log "$root_path/logs/all-CHIRPS.log")

        echo "Comparing existing downloading data in CHIRPS directory to list saved to log"
        echo "Number of files in CHIRPS directory: ${num_files_in_dir}"
        echo "Number of files in all-CHIRPS.log log file: ${num_files_in_log}"

        if [ "$num_files_in_dir" -lt "$num_files_in_log" ]; then
            missing_files=()
            # get last item from all-CHIRPS.log
            last_item=$(tail -n 1 "$root_path/logs/all-CHIRPS.log")
            # Check if last_item doenst exists in log file
            if ! find "$root_path/input_data/CHIRPS" -type f -name "*${last_item}*" | grep -q .; then
                # Add last_item to log file
                missing_files+=("${DOWNLOAD_CHIRPS_BASE_URL}${last_item}")
            fi
            download_missing_files "$root_path/input_data/CHIRPS" $missing_files
        else
            echo "CHIRPS log data matches the download directory."
        fi
    else
        echo "Download all CHIRPS dataset"
        ./download.sh "${DOWNLOAD_CHIRPS_BASE_URL}" "${DOWNLOAD_CHIRPS_PATTERN}" "$root_path/logs/all-CHIRPS.log" "$root_path/input_data/CHIRPS" > /dev/null 2>&1
    fi
}

check_and_download_LST_dataset() {
    printf "\n===Check and download LST dataset===\n\n"
    check_and_create_download_log  "${DOWNLOAD_LST_BASE_URL}" "${DOWNLOAD_LST_PATTERN}" "LST"
}

check_and_download_NDVI_dataset() {
    printf "\n===Check and download NDVI dataset===\n\n"
    check_and_create_download_log  "${DOWNLOAD_NDVI_BASE_URL}" "${DOWNLOAD_NDVI_PATTERN}" "NDVI"
}

check_and_download_SM_dataset() {
    printf "\n===Check and download SM dataset===\n\n"
    check_and_create_download_log  "${DOWNLOAD_SM_BASE_URL}" "${DOWNLOAD_SM_PATTERN}" "SM"
}
