run_cdi_scripts() {
    echo "Running CDI scripts..."
    docker compose exec cdi python STEP_0000_execute_all_steps.py
    if [[ $? -ne 0 ]]; then
        echo "CDI script execution failed!"
        exit 1
    fi
}
