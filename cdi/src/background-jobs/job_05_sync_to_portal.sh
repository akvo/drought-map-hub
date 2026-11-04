sync_geonode_to_portal () {
    activate_python_env
    local PY
    PY=$(python_bin) || { echo "Portal sync failed: no Python interpreter."; exit 1; }
    if ! "${PY}" -u upload_to_geonode/sync_geonode_publications_job.py; then
        echo "Portal sync script execution failed!"
        deactivate_python_env
        exit 1
    fi
    deactivate_python_env
}
