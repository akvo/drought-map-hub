#!/bin/bash

# All four datasets come from the NDMC Regional Percentiles endpoint and share the
# same 2-level {BASE_URL}/{DATASET}/{YYYY}/ layout. MODE (recent|all) is forwarded
# to control how many years are traversed.

check_and_download_ESI_dataset() {
    local MODE=${1:-recent}
    printf "\n===Check and download ESI dataset===\n\n"
    check_and_create_download_log_ndmc "${DOWNLOAD_NDMC_BASE_URL}" "${DOWNLOAD_ESI_DATASET}" "ESI" "${MODE}"
}

check_and_download_EVI2_dataset() {
    local MODE=${1:-recent}
    printf "\n===Check and download EVI2 dataset===\n\n"
    check_and_create_download_log_ndmc "${DOWNLOAD_NDMC_BASE_URL}" "${DOWNLOAD_EVI2_DATASET}" "EVI2" "${MODE}"
}

check_and_download_SPI_dataset() {
    local MODE=${1:-recent}
    printf "\n===Check and download SPI dataset===\n\n"
    check_and_create_download_log_ndmc "${DOWNLOAD_NDMC_BASE_URL}" "${DOWNLOAD_SPI_DATASET}" "SPI" "${MODE}"
}

check_and_download_SM_dataset() {
    local MODE=${1:-recent}
    printf "\n===Check and download SM dataset===\n\n"
    check_and_create_download_log_ndmc "${DOWNLOAD_NDMC_BASE_URL}" "${DOWNLOAD_SM_DATASET}" "SM" "${MODE}"
}
