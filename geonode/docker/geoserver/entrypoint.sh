#!/bin/bash

# Exit script in case of error
set -e

echo $"\n\n\n"
echo "-----------------------------------------------------"
echo "STARTING GEOSERVER ENTRYPOINT $(date)"
echo "-----------------------------------------------------"

# Check required environment variables
check_env_variables() {
    # Check for NGINX_BASE_URL which is needed for proper configuration
    if [ -n "${NGINX_BASE_URL}" ]; then
        echo "NGINX_BASE_URL is filled: ${NGINX_BASE_URL}"
    else
        echo "WARNING: NGINX_BASE_URL is not set. Using default values for GeoServer connection."
    fi

    # Check for other important variables
    echo "GEOSERVER_ADMIN_USER: ${GEOSERVER_ADMIN_USER:-admin}"
    echo "GEOSERVER_LB_HOST_IP: ${GEOSERVER_LB_HOST_IP:-localhost}"
    echo "GEOSERVER_LB_PORT: ${GEOSERVER_LB_PORT:-8080}"
}

# Simple function to check if GeoServer is ready
check_geoserver_status() {
    # Determine which URL to use for GeoServer
    if [ -n "${NGINX_BASE_URL}" ]; then
        # If NGINX_BASE_URL is set, use it for constructing the GeoServer URL
        GEOSERVER_URL="${NGINX_BASE_URL}/geoserver/ows"
    else
        # Otherwise use the LB host and port values
        GEOSERVER_HOST=${GEOSERVER_LB_HOST_IP:-localhost}
        GEOSERVER_PORT=${GEOSERVER_LB_PORT:-8080}

        # Determine protocol based on host
        if [[ "${GEOSERVER_HOST}" == "localhost" || "${GEOSERVER_HOST}" == "127.0.0.1" || "${GEOSERVER_HOST}" == "geoserver" ]]; then
            PROTOCOL="http"
        else
            PROTOCOL="https"
        fi

        # Construct the URL for health check
        GEOSERVER_URL="${PROTOCOL}://${GEOSERVER_HOST}:${GEOSERVER_PORT}/geoserver/ows"
    fi

    # Simple health check
    RESPONSE_CODE=$(curl -s -k -o /dev/null -w "%{http_code}" "${GEOSERVER_URL}")
    if [ "$RESPONSE_CODE" = "200" ]; then
        return 0  # GeoServer is ready
    else
        return 1  # GeoServer is not ready
    fi
}

# Update GeoServer settings via REST API (once)
update_geoserver_settings() {
    echo "Updating GeoServer settings via REST API..."

    # Use default admin credentials if not set
    ADMIN_USER=${GEOSERVER_ADMIN_USER:-admin}
    ADMIN_PASSWORD="geoserver"

    # Determine which URL to use for GeoServer
    if [ -n "${NGINX_BASE_URL}" ]; then
        # If NGINX_BASE_URL is set, use it for constructing the GeoServer URL
        GEOSERVER_BASE_URL="${NGINX_BASE_URL}"
        echo "Using NGINX_BASE_URL for GeoServer base URL: ${GEOSERVER_BASE_URL}"
    else
        # Otherwise use the LB host and port values
        GEOSERVER_HOST=${GEOSERVER_LB_HOST_IP:-localhost}
        GEOSERVER_PORT=${GEOSERVER_LB_PORT:-8080}

        # Determine protocol based on host
        if [[ "${GEOSERVER_HOST}" == "localhost" || "${GEOSERVER_HOST}" == "127.0.0.1" || "${GEOSERVER_HOST}" == "geoserver" ]]; then
            PROTOCOL="http"
        else
            PROTOCOL="https"
        fi

        # Construct the base URL
        GEOSERVER_BASE_URL="${PROTOCOL}://${GEOSERVER_HOST}:${GEOSERVER_PORT}"
        echo "Using constructed GeoServer base URL: ${GEOSERVER_BASE_URL}"
    fi

    # Try to update the XML external entities setting
    echo "Setting xmlExternalEntitiesEnabled to true..."
    curl -s -k -u "${ADMIN_USER}:${ADMIN_PASSWORD}" \
         -X PUT \
         -H "Content-Type: application/xml" \
         -d '<global>
          <xmlExternalEntitiesEnabled>true</xmlExternalEntitiesEnabled>
         </global>' \
         "${GEOSERVER_BASE_URL}/geoserver/rest/settings.xml"

    echo "GeoServer settings update attempted."
}

# Main execution flow with error handling
main() {
    # Check environment variables first
    check_env_variables

    # Start GeoServer in the background
    echo "Starting GeoServer in the background..."
    "$@" &
    GEOSERVER_PID=$!

    # Check if GeoServer process is running
    if ! ps -p $GEOSERVER_PID > /dev/null; then
        echo "ERROR: GeoServer failed to start."
        exit 1
    fi

    # Periodically check GeoServer status and update settings when ready
    echo "Will check GeoServer status every 2 minutes..."

    SETTINGS_UPDATED=false

    while true; do
        if check_geoserver_status; then
            echo "GeoServer is ready!"

            # Update settings only once
            if [ "$SETTINGS_UPDATED" = false ]; then
                update_geoserver_settings
                SETTINGS_UPDATED=true
                echo "Settings update completed."
            fi
        else
            echo "GeoServer not ready yet. Will check again in 2 minutes."
        fi

        # Wait 2 minutes before checking again
        sleep 120
    done &
 
    # Keep the script running so the container doesn't exit
    echo "GeoServer entrypoint completed, container will continue running."
    wait $GEOSERVER_PID || echo "GeoServer process exited with status $?"
}

# Execute the main function with all arguments
main "$@"

# Execute the main function with all arguments
main "$@"
