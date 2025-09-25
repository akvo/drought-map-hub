#!/bin/bash

# Get the root directory of the project
root_path="$(dirname "$(dirname "$(dirname "$(realpath "$0")")")")"

# Load environment variables from .env file in the root directory
export $(grep -v '^#' "$root_path/.env" | xargs)

# Change to the directory of the script
cd "$(dirname "$0")"

source ./utils.sh

GES_URL="$1"
GES_PATTERN="$2"
DOWNLOAD_LIST="$3"
TARGET_DIR="$4"

curl -s "${GES_URL}" \
	| grep "${GES_PATTERN}" \
	| pup \
	| grep -v "href" \
	| grep "${GES_PATTERN}" \
	| sed "s/\ //g" > "${DOWNLOAD_LIST}"

echo "FILES TOBE DOWNLOADED: $(wc -l "${DOWNLOAD_LIST}")"

# Read the file line by line
while IFS= read -r GES_FILE; do
    echo "Processing line: ${LINE}"
	# Download the file
	download_file "${TARGET_DIR}" "${GES_URL}" "${GES_FILE}"
done < "${DOWNLOAD_LIST}"

