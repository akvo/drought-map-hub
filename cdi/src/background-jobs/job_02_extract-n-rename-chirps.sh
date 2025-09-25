#!/bin/bash

# Get the root directory of the project (cdi folder)
root_path="$(dirname "$(dirname "$(dirname "$(realpath "$0")")")")"

extract_and_rename_chirps() {
    local DIR=$root_path/input_data/CHIRPS
    local num_tif=$(find "$DIR" -maxdepth 1 -type f -name "*.tif" | wc -l)
    local num_gz=$(find "$DIR" -maxdepth 1 -type f -name "*.gz" | wc -l)

    if [ "$num_tif" -eq "$num_gz" ]; then
        echo "[CHIRPS] Extraction already completed. Skipping."
        return
    fi

    # Extract all .gz files and remove them after successful extraction
    for gz in "$DIR"/*.gz; do
        [ -e "$gz" ] || continue
        if gunzip -f "$gz"; then
            echo "Successfully extracted and removed: $(basename "$gz")"
        else
            echo "Failed to extract: $(basename "$gz")"
        fi
    done

    # Rename all extracted files matching chirps-v2.0.*.tif
    for file in "$DIR"/chirps-v2.0.*.tif; do
        [ -e "$file" ] || continue
        local year=$(echo "$file" | grep -oP '\d{4}')
        local month=$(echo "$file" | grep -oP '\.\d{2}\.' | tr -d '.')
        mv "$file" "${DIR}/c${year}${month}.tif"
    done
}
