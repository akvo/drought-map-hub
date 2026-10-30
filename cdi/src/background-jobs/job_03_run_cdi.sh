run_cdi_scripts() {
    local MODE=${1:-recent}
    activate_python_env
    local PY
    PY=$(python_bin) || { echo "CDI script execution failed: no Python interpreter."; exit 1; }
    if ! "${PY}" -u ../cdi-scripts/STEP_0000_execute_all_steps.py --mode="${MODE}"; then
        echo "CDI script execution failed!"
        deactivate_python_env
        exit 1
    fi
    deactivate_python_env
}
