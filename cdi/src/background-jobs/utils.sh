#!/bin/bash

# --- Python environment helpers ---------------------------------------------
# Activate a Python virtual environment if one is configured and present.
# The path comes from the PYTHON_VENV env var (set it in .env), falling back to
# ~/.myenv for backward compatibility. If no venv is found, the system Python is
# used instead (with a warning) rather than the pipeline hard-failing.
activate_python_env() {
    local venv_path="${PYTHON_VENV:-$HOME/.myenv}"
    if [ -f "${venv_path}/bin/activate" ]; then
        echo "Activating Python virtual environment: ${venv_path}"
        # shellcheck disable=SC1090
        source "${venv_path}/bin/activate"
    else
        echo "No virtual environment found at ${venv_path}; using system Python."
        echo "(set PYTHON_VENV in .env to point at your virtual environment)"
    fi
}

# Deactivate the virtual environment if one is currently active.
deactivate_python_env() {
    if command -v deactivate >/dev/null 2>&1; then
        deactivate
    fi
}

# Echo a usable Python interpreter: prefer 'python' (present inside an active
# venv), otherwise fall back to 'python3'. Returns non-zero if neither exists.
python_bin() {
    if command -v python >/dev/null 2>&1; then
        echo "python"
    elif command -v python3 >/dev/null 2>&1; then
        echo "python3"
    else
        echo "Error: neither 'python' nor 'python3' found on PATH." >&2
        return 1
    fi
}

download_file() {
    local TARGET_DIR=$1
    local BASE_URL=$2
    local GES_FILE=$3

    mkdir -p "${TARGET_DIR}"

    # NDMC endpoint is public HTTP — no authentication required.
    # Download a single file to a .tmp path, then promote on success.
    wget -c "${BASE_URL}/${GES_FILE}" -O "${TARGET_DIR}/${GES_FILE}.tmp" >/dev/null 2>&1

    if [ $? -ne 0 ]; then
        echo "Download failed: ${BASE_URL}/${GES_FILE}. Exiting."
        rm -f "${TARGET_DIR}/${GES_FILE}.tmp"
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
    local input_dir="../../input_data/${dataset_name}"
    local log_file="../../logs/all-${dataset_name}_URLS.log"

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

# Generic function to check and download any dataset (for simple single-directory datasets like CHIRPS)
check_and_download_dataset() {
    local BASE_URL=$1
    local PATTERN=$2
    local NAME=$3

    printf "\n===Check and download ${NAME} dataset===\n\n"
    remove_tmp_files "../../input_data/${NAME}"

    # Check if log file exists
    if [ ! -f "../../logs/all-${NAME}.log" ]; then
        touch "../../logs/all-${NAME}.log"
    fi

    LOG_IS_EMPTY=$(cat "../../logs/all-${NAME}.log" | wc -l)

    # Check what's being extracted from the last line
    # For CHIRPS pattern: chirps-v2.0.{year}.{month}.tif.gz
    l_date="$(tail -n 1 "../../logs/all-${NAME}.log" | cut -d '.' -f 3,4)"
    # Cross-platform date command (macOS uses BSD date, Linux uses GNU date)
    if date -v-1d > /dev/null 2>&1; then
        # BSD date (macOS)
        current_date="$(date -v-1m "+%Y.%m")"
    else
        # GNU date (Linux)
        current_date="$(date -d "1 month ago" "+%Y.%m")"
    fi

    if [ "$LOG_IS_EMPTY" -eq 0 ] || [ "$l_date" \< "$current_date" ]; then
        echo "Downloading list of available ${NAME} data and saving to log"
        curl -s "${BASE_URL}" \
            | grep "${PATTERN}" \
            | pup \
            | grep -v "href" \
            | grep "${PATTERN}" \
            | sed "s/\ //g" > "../../logs/all-${NAME}.log"
    fi

    if ls ../../input_data/${NAME}/*.tif* 1> /dev/null 2>&1; then
        num_files_in_dir=$(get_num_files_in_dir "../../input_data/${NAME}")
        num_files_in_log=$(get_num_files_in_log "../../logs/all-${NAME}.log")

        echo "Comparing existing downloading data in ${NAME} directory to list saved to log"
        echo "Number of files in ${NAME} directory: ${num_files_in_dir}"
        echo "Number of files in all-${NAME}.log log file: ${num_files_in_log}"

        if [ "$num_files_in_dir" -lt "$num_files_in_log" ]; then
            missing_files=()
            # get last item from all-${NAME}.log
            last_item=$(tail -n 1 "../../logs/all-${NAME}.log")
            # Check if last_item doesn't exist in directory
            if ! find "../../input_data/${NAME}" -type f -name "*${last_item}*" | grep -q .; then
                # Add last_item to missing files
                missing_files+=("${BASE_URL}${last_item}")
            fi
            download_missing_files "../../input_data/${NAME}" $missing_files
        else
            echo "${NAME} log data matches the download directory."
        fi
    else
        echo "Download all ${NAME} dataset"
        ./download.sh "${BASE_URL}" "${PATTERN}" "../../logs/all-${NAME}.log" "../../input_data/${NAME}"
    fi
}

check_and_create_download_log() {
    local BASE_URL=$1
    local GES_PATTERN=$2
    local NAME=$3
    LOG_NAME="all-${NAME}_URLS.log"

    remove_tmp_files "../../input_data/${NAME}"

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

    if [ ! -f "../../logs/${LOG_NAME}" ]; then
        # Create log file
        for URLS in ${URL_DIRS}; do
            GES_URL="${URL}${URLS}"
            # Grab all files
            all_files=$(curl -s "${BASE_URL}${GES_URL}")

            # Choose only matched files by GES_PATTERN
            matched_files=$(echo "${all_files}" | grep "${GES_PATTERN}" | pup | grep -v "href" | grep "${GES_PATTERN}" | grep -v "\.xml" | sed "s/\ //g")

            # Insert to log file
            echo "${matched_files}" | sed "s|^|${BASE_URL}${GES_URL}|" >>"../../logs/${LOG_NAME}.tmp"
            sleep 5
        done
        mv "../../logs/${LOG_NAME}.tmp" "../../logs/${LOG_NAME}"
        sed -i '/xml/d' "../../logs/${LOG_NAME}"
    fi

    # get last item from URL_DIRS. eg:
    last_item=$(echo "${URL_DIRS}" | tail -n 1)
    # Check if last_item doenst exists in log file
    if ! grep -q "${BASE_URL}${last_item}" "../../logs/${LOG_NAME}"; then
        # Add last_item to log file
        echo "${BASE_URL}${last_item}" >>"../../logs/${LOG_NAME}"
    fi

    if [ -f "../../logs/${LOG_NAME}" ]; then
        # Fix incomplete URLs by refetching them
        incomplete_urls=$(grep -E '/$' "../../logs/${LOG_NAME}")
        if [ ! -z "$incomplete_urls" ]; then
            for url in $incomplete_urls; do
                # Grab all files
                all_files=$(curl -s "${url}")

                # Choose only matched files by GES_PATTERN
                matched_files=$(echo "${all_files}" | grep "${GES_PATTERN}" | pup | grep -v "href" | grep "${GES_PATTERN}" | grep -v "\.xml" | sed "s/\ //g")

                # Insert to log file
                echo "${url}${matched_files}" >> "../../logs/${LOG_NAME}"
            done

            # delete all incomplete URLs
            sed -i '/\/$/d' "../../logs/${LOG_NAME}"
        fi

        echo "Checking if new data was expected for new month"

        current_month=$(date +%Y.%m)
        # Cross-platform date command (macOS uses BSD date, Linux uses GNU date)
        if date -v-1d > /dev/null 2>&1; then
            # BSD date (macOS)
            expected_month=$(date -v-1m +%Y.%m)
            # if NAME is equal "SM" then change format expected_month to %Y%m
            if [ "${NAME}" == "SM" ]; then
                expected_month=$(date -v-1m +%Y%m)
            fi
        else
            # GNU date (Linux)
            expected_month=$(date -d "1 month ago" +%Y.%m)
            # if NAME is equal "SM" then change format expected_month to %Y%m
            if [ "${NAME}" == "SM" ]; then
                expected_month=$(date -d "1 month ago" +%Y%m)
            fi
        fi

        echo "Current month: ${current_month}. Expecting new data for: ${expected_month}"

        if ! grep -q "${expected_month}" "../../logs/${LOG_NAME}"; then
            echo "No data for ${expected_month} found for ${NAME}"
            # echo "Exiting script"
            # exit 1
        fi

        echo "Comparing existing downloading data in ${NAME} directory to list saved to log"
        validate_files "${NAME}"
    fi
}

# Build the download log for an NDMC Regional Percentiles dataset and fetch any
# missing files. NDMC layout is a 2-level tree: {BASE_URL}/{DATASET}/{YYYY}/{file}.tif
# where files are named {DATASET}_{YYYY}-{MM}-01.tif. No authentication required.
#   MODE=recent (default): only the last 2 years
#   MODE=all            : full history from 2012 to the current year
check_and_create_download_log_ndmc() {
    local BASE_URL=$1
    local DATASET=$2
    local NAME=$3
    local MODE=${4:-recent}
    local LOG_NAME="all-${NAME}_URLS.log"
    local dataset_url="${BASE_URL}/${DATASET}"

    remove_tmp_files "../../input_data/${NAME}"

    echo "Building NDMC download log for ${NAME} (${DATASET}), mode=${MODE}"

    # Make sure the dataset URL is accessible before traversing year subdirs
    response_code=$(curl -s -o /dev/null -w "%{http_code}" "${dataset_url}/")
    if [ "$response_code" -ne 200 ]; then
        echo "Error: Unable to access ${dataset_url}/. Response code: ${response_code}"
        echo "Exiting script"
        exit 1
    fi

    # Determine the year range to traverse
    local current_year
    current_year=$(date +%Y)
    local years=()
    if [ "${MODE}" == "all" ]; then
        for ((y = 2012; y <= current_year; y++)); do
            years+=("$y")
        done
    else
        years+=("$((current_year - 1))" "${current_year}")
    fi

    # Rebuild the URL log fresh each run so newly published months are picked up
    : > "../../logs/${LOG_NAME}.tmp"
    for YEAR in "${years[@]}"; do
        local year_url="${dataset_url}/${YEAR}/"
        # Skip years whose subdirectory does not exist yet
        response_code=$(curl -s -o /dev/null -w "%{http_code}" "${year_url}")
        if [ "$response_code" -ne 200 ]; then
            echo "  ${NAME} ${YEAR}: no directory (HTTP ${response_code}), skipping"
            continue
        fi
        # Collect .tif files matching {DATASET}_{YYYY}-{MM}-01.tif from the listing.
        # NDMC serves IIS-style listings: <A HREF="/absolute/path/file.tif">. Match
        # HREF case-insensitively and strip the path to the bare filename.
        local tif_files
        tif_files=$(curl -s "${year_url}" |
            grep -oiP '(?<=HREF=")[^"]*\.tif' |
            sed 's|.*/||' |
            grep -E "^${DATASET}_${YEAR}-(0[1-9]|1[0-2])-01\.tif$")
        for f in ${tif_files}; do
            echo "${year_url}${f}" >> "../../logs/${LOG_NAME}.tmp"
        done
        sleep 1
    done
    mv "../../logs/${LOG_NAME}.tmp" "../../logs/${LOG_NAME}"

    echo "Comparing existing data in ${NAME} directory to list saved to log"
    validate_files "${NAME}"
}

# Clean up the output data directory
# Remove all *.nc in ./output_data (STEP_0100 writes its NetCDF intermediates here)
# Remove all *.tif for each subdirectory in ./output_data/GeoTiffs
# STEP_0100 no longer uses the working_data/ scratch dirs that the old HDF pipeline did.

cleanup_output_data() {
    echo "Cleaning up output data directory"
    find ../../output_data -type f -name "*.nc" -delete
    find ../../output_data/GeoTiffs -type f -name "*.tif" -delete

    echo "Cleanup complete"
}

# Variant of check_and_create_download_log for flat (single-level) directories
check_and_create_download_log_flat() {
    local BASE_URL=$1
    local GES_PATTERN=$2
    local NAME=$3
    LOG_NAME="all-${NAME}_URLS.log"

    remove_tmp_files "../../input_data/${NAME}"

    echo "Downloading list of available ${NAME} data and saving to log (flat)"
    # Make sure the URL is accessible by checking the response code
    response_code=$(curl -s -o /dev/null -w "%{http_code}" "${BASE_URL}")
    if [ "$response_code" -ne 200 ]; then
        echo "Error: Unable to access ${BASE_URL}. Response code: ${response_code}"
        echo "Exiting script"
        exit 1
    fi

    # Grab listing of files from BASE_URL and filter by pattern
    all_files=$(curl -s "${BASE_URL}")
    matched_files=$(echo "${all_files}" | grep "${GES_PATTERN}" | pup | grep -v "href" | grep "${GES_PATTERN}" | grep -v "\.xml" | sed "s/\ //g")

    if [ ! -f "../../logs/${LOG_NAME}" ]; then
        # Create log file with full URLs
        echo "${matched_files}" | sed "s|^|${BASE_URL}|" > "../../logs/${LOG_NAME}.tmp"
        mv "../../logs/${LOG_NAME}.tmp" "../../logs/${LOG_NAME}"
        sed -i '/xml/d' "../../logs/${LOG_NAME}"
    fi

    if [ -f "../../logs/${LOG_NAME}" ]; then
        # Fix any incomplete URLs (trailing slash entries)
        incomplete_urls=$(grep -E '/$' "../../logs/${LOG_NAME}")
        if [ ! -z "$incomplete_urls" ]; then
            for url in $incomplete_urls; do
                all_files=$(curl -s "${url}")
                matched_files=$(echo "${all_files}" | grep "${GES_PATTERN}" | pup | grep -v "href" | grep "${GES_PATTERN}" | grep -v "\.xml" | sed "s/\ //g")
                echo "${url}${matched_files}" >> "../../logs/${LOG_NAME}"
            done
            sed -i '/\/$/d' "../../logs/${LOG_NAME}"
        fi

        echo "Checking if new data was expected for new month"

        current_month=$(date +%Y.%m)
        if date -v-1d > /dev/null 2>&1; then
            expected_month=$(date -v-1m +%Y.%m)
            if [ "${NAME}" == "SM" ]; then
                expected_month=$(date -v-1m +%Y%m)
            fi
        else
            expected_month=$(date -d "1 month ago" +%Y.%m)
            if [ "${NAME}" == "SM" ]; then
                expected_month=$(date -d "1 month ago" +%Y%m)
            fi
        fi

        echo "Current month: ${current_month}. Expecting new data for: ${expected_month}"

        if ! grep -q "${expected_month}" "../../logs/${LOG_NAME}"; then
            echo "No data for ${expected_month} found for ${NAME}"
        fi

        echo "Comparing existing downloading data in ${NAME} directory to list saved to log"
        validate_files "${NAME}"
    fi
}