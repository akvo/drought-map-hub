#!/bin/bash

# Get the root directory of the project (cdi folder)
root_path="$(dirname "$(dirname "$(dirname "$(realpath "$0")")")")"

download_file() {
    local TARGET_DIR=$1
    local BASE_URL=$2
    local GES_FILE=$3

    wget --load-cookies ./.urs_cookies \
        --keep-session-cookies --user="${EARTHDATA_USERNAME}" \
        --content-disposition --content-disposition -r -c -nH -nd -np -A ".nc4" \
        -P "${TARGET_DIR}" "${BASE_URL}/${GES_FILE}" -O "${TARGET_DIR}/${GES_FILE}.tmp" >/dev/null 2>&1

    if [ $? -ne 0 ]; then
        echo "Download failed: ${BASE_URL}/${GES_FILE}. Exiting."
        exit 1
    fi

    if [ -f "${TARGET_DIR}/${GES_FILE}.tmp" ]; then
        mv "${TARGET_DIR}/${GES_FILE}.tmp" "${TARGET_DIR}/${GES_FILE}"
    fi
}

remove_tmp_files() {
    local dir=$1
    for file in "${dir}"/*.tmp; do
        if [ -f "$file" ]; then
            rm "$file"
        fi
    done
}

get_num_files_in_dir() {
    local dir=$1
    find "${dir}" \( -name "FLDAS*.nc" -o -name "*.hdf" -o -name "*.tif" \) | wc -l
}

get_num_files_in_log() {
    local log_file=$1
    wc -l <"${log_file}"
}

download_missing_files() {
    local dir=$1
    local missing_files=("${@:2}")

    # Process files in batches of 10 with 30 seconds delay between batches
    for ((i = 0; i < ${#missing_files[@]}; i += 10)); do
        echo "START: Batch $((i / 10 + 1))"
        for ((j = i; j < i + 10 && j < ${#missing_files[@]}; j++)); do
            (
                file_name=$(basename "${missing_files[j]}")
                prefix_url=$(dirname "${missing_files[j]}")

                if [[ -z "${file_name}" ]]; then
                    echo "Error: file_name is empty. Skipping download."
                    return
                fi
                echo "Downloading: ${file_name} from ${prefix_url}"
                download_file "${dir}" "${prefix_url}" "${file_name}"
            ) &
        done
        wait # Wait for all background jobs in the current batch to finish
        echo "Batch $((i / 10 + 1)) complete. Waiting for 30 seconds..."
        sleep 30
    done
}

# Function to validate files based on dataset name
validate_files() {
    local dataset_name=$1
    local input_dir="$root_path/input_data/${dataset_name}"
    local log_file="$root_path/logs/all-${dataset_name}_URLS.log"

    missing_files=()
    IS_UP_TO_DATE=true

    echo "Validating files for dataset: $dataset_name"

    # Read each URL line by line from the log file
    while IFS= read -r url; do
        [[ -z "$url" ]] && continue

        filename=$(basename "$url")
        filepath="${input_dir}/${filename}"
        filepath_h5="${input_dir}/${filename%.*}_h5.hdf"

        if [[ ! -f "$filepath" && ! -f "$filepath_h5" ]]; then
            echo "Missing: $filename"
            IS_UP_TO_DATE=false
            missing_files+=("$url")
        fi
    done < "$log_file"

    if $IS_UP_TO_DATE; then
        echo "${dataset_name} dataset is up to date."
    else
        echo "Some files are missing. Downloading now..."
        download_missing_files "$input_dir" "${missing_files[@]}"
    fi
}

check_and_create_download_log() {
    local BASE_URL=$1
    local GES_PATTERN=$2
    local NAME=$3
    LOG_NAME="all-${NAME}_URLS.log"

    remove_tmp_files "$root_path/input_data/${NAME}"

    echo "Downloading list of available ${NAME} data and saving to log"
    # Make sure the URL is accessible by checking the response code
    response_code=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}")
    if [ "$response_code" -ne 200 ]; then
        echo "Error: Unable to access ${BASE_URL}. Response code: ${response_code}"
        echo "Exiting script"
        exit 1
    fi
    URL_DIRS=$(curl -s "${BASE_URL}" |
        grep "\[DIR\]" |
        grep -v "doc" |
        grep -oP '(?<=href=")[^"]*')

    if [ ! -f "$root_path/logs/${LOG_NAME}" ]; then
        # Create log file
        for URLS in ${URL_DIRS}; do
            GES_URL="${URL}${URLS}"
            # Grab all files
            all_files=$(curl -s "${BASE_URL}${GES_URL}")

            # Choose only matched files by GES_PATTERN
            matched_files=$(echo "${all_files}" | grep "${GES_PATTERN}" | pup | grep -v "href" | grep "${GES_PATTERN}" | grep -v "\.xml" | sed "s/\ //g")

            # Insert to log file
            echo "${matched_files}" | sed "s|^|${BASE_URL}${GES_URL}|" >>"$root_path/logs/${LOG_NAME}.tmp"
            sleep 5
        done
        mv "$root_path/logs/${LOG_NAME}.tmp" "$root_path/logs/${LOG_NAME}"
        sed -i '/xml/d' "$root_path/logs/${LOG_NAME}"
    fi

    # get last item from URL_DIRS. eg:
    last_item=$(echo "${URL_DIRS}" | tail -n 1)
    # Check if last_item doenst exists in log file
    if ! grep -q "${BASE_URL}${last_item}" "$root_path/logs/${LOG_NAME}"; then
        # Add last_item to log file
        echo "${BASE_URL}${last_item}" >>"$root_path/logs/${LOG_NAME}"
    fi

    if [ -f "$root_path/logs/${LOG_NAME}" ]; then
        # Fix incomplete URLs by refetching them
        incomplete_urls=$(grep -E '/$' "$root_path/logs/${LOG_NAME}")
        if [ ! -z "$incomplete_urls" ]; then
            for url in $incomplete_urls; do
                # Grab all files
                all_files=$(curl -s "${url}")

                # Choose only matched files by GES_PATTERN
                matched_files=$(echo "${all_files}" | grep "${GES_PATTERN}" | pup | grep -v "href" | grep "${GES_PATTERN}" | grep -v "\.xml" | sed "s/\ //g")

                # Insert to log file
                echo "${url}${matched_files}" >> "$root_path/logs/${LOG_NAME}"
            done

            # delete all incomplete URLs
            sed -i '/\/$/d' "$root_path/logs/${LOG_NAME}"
        fi

        echo "Checking if new data was expected for new month"

        current_month=$(date +%Y.%m)
        expected_month=$(date -d "1 month ago" +%Y.%m)
        # if NAME is equal "SM" then change format expected_month to %Y%m
        if [ "${NAME}" == "SM" ]; then
            expected_month=$(date -d "1 month ago" +%Y%m)
        fi

        echo "Current month: ${current_month}. Expecting new data for: ${expected_month}"

        if ! grep -q "${expected_month}" "$root_path/logs/${LOG_NAME}"; then
            echo "No data for ${expected_month} found for ${NAME}"
            # echo "Exiting script"
            # exit 1
        fi

        echo "Comparing existing downloading data in ${NAME} directory to list saved to log"
        validate_files "${NAME}"
    fi
}


cleanup_output_data() {
    echo "Cleaning up output data directory"
    find "$root_path/output_data" -type f -name "*.nc" -delete
    find "$root_path/output_data/GeoTiffs" -type f -name "*.tif" -delete
    docker compose exec cdi find /app/working_data/LST -type f -name "*.nc" -delete
    docker compose exec cdi find /app/working_data/NDVI -type f -name "*.nc" -delete
    docker compose exec cdi find /app/working_data/SPI -type f -name "*.nc" -delete

    echo "Cleanup complete"
}