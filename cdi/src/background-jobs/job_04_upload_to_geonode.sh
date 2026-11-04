upload_to_geonode () {
    activate_python_env
    local PY
    PY=$(python_bin) || { echo "Upload to Geonode script execution failed: no Python interpreter."; exit 1; }
    if ! "${PY}" -u upload_to_geonode/upload_to_geonode_job.py; then
        echo "Upload to Geonode script execution failed!"
        deactivate_python_env
        exit 1
    fi
    deactivate_python_env
}

upload_cdi_to_geonode () {
    activate_python_env
    local PY
    PY=$(python_bin) || { echo "Upload CDI to Geonode script execution failed: no Python interpreter."; exit 1; }
    # Run the script without changing directories
    if ! "${PY}" -u upload_to_geonode/upload_cdi_to_geonode_job.py; then
        echo "Upload CDI to Geonode script execution failed!"
        deactivate_python_env
        exit 1
    fi
    deactivate_python_env
}
