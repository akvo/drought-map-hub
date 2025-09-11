#!/bin/bash

# Rundeck initialization entrypoint script
# This script ensures initial setup runs only once when the container starts

set -e

INIT_FLAG_FILE="/home/rundeck/server/data/.initialized"

echo "Starting Rundeck container..."

# Function to wait for Rundeck to be ready
wait_for_rundeck() {
    echo "Waiting for Rundeck to start..."
    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        # Check if Rundeck web interface is accessible
        if curl -f -s $RUNDECK_GRAILS_URL/ > /dev/null 2>&1; then
            echo "Rundeck web interface is ready!"
            # Give it a bit more time for API to be ready
            sleep 5
            return 0
        fi
        echo "Attempt $attempt/$max_attempts: Rundeck not ready yet, waiting..."
        sleep 10
        attempt=$((attempt + 1))
    done

    echo "Error: Rundeck failed to start within the expected time"
    return 1
}

# Function to run initial setup
run_initial_setup() {
    echo "Running initial setup..."

    # Wait for Rundeck to be fully ready
    wait_for_rundeck

    # Setup variables
    PROJECT_NAME="drought_map_hub"
    API_VERSION="50"

    echo "Creating API token..."
    API_TOKEN=$(rd tokens create --user=admin --roles=admin | tail -n 1)

    if [ -z "$API_TOKEN" ]; then
        echo "Error: Failed to create API token"
        return 1
    fi

    echo "API token created successfully: $API_TOKEN"

    # Update RUNDECK_API_TOKEN in the .env file
    echo "Updating RUNDECK_API_TOKEN in .env file..."
    ENV_FILE="/home/rundeck/server/config/.env"

    if [ -f "$ENV_FILE" ]; then
        echo "Found .env file at: $ENV_FILE"

        # Show current content for debugging
        echo "Current RUNDECK_API_TOKEN line:"
        grep "RUNDECK_API_TOKEN=" "$ENV_FILE" || echo "RUNDECK_API_TOKEN line not found"

        # Create a temporary file in a writable location
        TEMP_FILE="/tmp/.env.tmp"
        cp "$ENV_FILE" "$TEMP_FILE"

        # Update the RUNDECK_API_TOKEN value
        if grep -q "^RUNDECK_API_TOKEN=" "$TEMP_FILE"; then
            # Replace existing line using awk (more reliable than sed)
            awk -v token="$API_TOKEN" '/^RUNDECK_API_TOKEN=/ {print "RUNDECK_API_TOKEN=" token; next} {print}' "$TEMP_FILE" > "$TEMP_FILE.new"
            mv "$TEMP_FILE.new" "$TEMP_FILE"
        else
            # Add new line if it doesn't exist
            echo "RUNDECK_API_TOKEN=$API_TOKEN" >> "$TEMP_FILE"
        fi

        # Copy back to original location
        cp "$TEMP_FILE" "$ENV_FILE"
        rm -f "$TEMP_FILE"

        # Verify the update
        echo "Updated RUNDECK_API_TOKEN line:"
        grep "RUNDECK_API_TOKEN=" "$ENV_FILE" || echo "RUNDECK_API_TOKEN line not found after update"

        if grep -q "RUNDECK_API_TOKEN=$API_TOKEN" "$ENV_FILE"; then
            echo "RUNDECK_API_TOKEN updated successfully in .env file"
        else
            echo "Warning: RUNDECK_API_TOKEN update may have failed"
        fi

        echo "Environment file updated. Backend and worker services will read the updated token on next restart."

        # Write the token to a shared file for other services to pick up
        echo "$API_TOKEN" > "/home/rundeck/server/data/rundeck_api_token.txt"
        chmod 644 "/home/rundeck/server/data/rundeck_api_token.txt"
        echo "API token saved to shared file for other services"

    else
        echo "Warning: .env file not found at $ENV_FILE"
        echo "API Token: $API_TOKEN"
        echo "Please manually update RUNDECK_API_TOKEN in your .env file"
    fi

    # Create a new project
    echo "Creating project: $PROJECT_NAME"
    if rd projects create -p="$PROJECT_NAME" -f="/home/rundeck/server/config/templates/project_template.properties"; then
        echo "Project created successfully"
    else
        echo "Warning: Project creation failed or project already exists"
    fi

    # Import Jobs via API
    echo "Importing jobs..."
    if [ -f "/home/rundeck/server/config/templates/job_template.json" ]; then
        curl -H "X-Rundeck-Auth-Token: $API_TOKEN" \
            -H "Content-Type: application/json" \
            --data @/home/rundeck/server/config/templates/job_template.json \
            -X POST $RD_URL/api/$API_VERSION/project/$PROJECT_NAME/jobs/import

        if [ $? -eq 0 ]; then
            echo "Jobs imported successfully"
        else
            echo "Warning: Job import failed"
        fi
    else
        echo "Warning: Job template file not found"
    fi

    # Mark as initialized
    touch "$INIT_FLAG_FILE"
    echo "Initial setup completed successfully!"
}

# Start Rundeck in the background
echo "Starting Rundeck server..."
/home/rundeck/docker-lib/entry.sh &
RUNDECK_PID=$!

# Check if this is the first run
if [ ! -f "$INIT_FLAG_FILE" ]; then
    echo "First time setup detected, will run initialization..."

    # Run initial setup in background after Rundeck starts
    (
        run_initial_setup
    ) &
    SETUP_PID=$!

    echo "Rundeck PID: $RUNDECK_PID, Setup PID: $SETUP_PID"
else
    echo "Rundeck already initialized, skipping setup."
fi

# Wait for Rundeck process
wait $RUNDECK_PID
