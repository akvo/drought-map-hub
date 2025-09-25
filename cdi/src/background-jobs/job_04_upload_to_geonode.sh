upload_to_geonode () {
    source ~/.myenv/bin/activate
    python -u upload_to_geonode/upload_to_geonode_job.py
    if [[ $? -ne 0 ]]; then
        echo "Upload to Geonode script execution failed!"
        exit 1
    fi
    deactivate
}

upload_cdi_to_geonode () {
    source ~/.myenv/bin/activate
    # Run the script without changing directories
    python -u upload_to_geonode/upload_cdi_to_geonode_job.py
    if [[ $? -ne 0 ]]; then
        echo "Upload CDI to Geonode script execution failed!"
        exit 1
    fi
    deactivate
}