#!/bin/bash

# Drought Map Hub Runner Script
# Usage: ./run.sh mode=<dev|prod> service=<all|geonode|app|cdi> [--dry-run]

set -e

# Default values
MODE=""
SERVICE=""
DRY_RUN=false
DOWN_MODE=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Function to display usage
usage() {
    echo "Usage: $0 mode=<dev|prod> service=<all|geonode|app|cdi> [--dry-run]"
    echo "   or: $0 down [--dry-run]"
    echo ""
    echo "Parameters:"
    echo "  mode=dev|prod    - Development or production mode"
    echo "                     Note: Traefik reverse proxy is only used in production mode"
    echo "  service=all|geonode|app|cdi - Which service to run"
    echo "  down             - Stop all running services"
    echo "  --dry-run        - Show what would be executed without running"
    echo ""
    echo "Examples:"
    echo "  $0 mode=dev service=all      # Development mode with direct port access"
    echo "  $0 mode=prod service=all     # Production mode with Traefik reverse proxy"
    echo "  $0 mode=prod service=app --dry-run"
    echo "  $0 mode=dev service=cdi"
    echo "  $0 down"
    echo "  $0 down --dry-run"
    exit 1
}

# Parse command line arguments
for arg in "$@"; do
    case $arg in
        mode=*)
            MODE="${arg#*=}"
            ;;
        service=*)
            SERVICE="${arg#*=}"
            ;;
        down)
            DOWN_MODE=true
            ;;
        --dry-run)
            DRY_RUN=true
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "Unknown argument: $arg"
            usage
            ;;
    esac
done

# Validate arguments
if [[ "$DOWN_MODE" == "true" ]]; then
    # Down mode doesn't need mode and service parameters
    :
elif [[ -z "$MODE" || -z "$SERVICE" ]]; then
    echo "Error: Both mode and service parameters are required."
    echo ""
    usage
fi

if [[ "$MODE" != "dev" && "$MODE" != "prod" && "$DOWN_MODE" != "true" ]]; then
    echo "Error: mode must be either 'dev' or 'prod'"
    usage
fi

if [[ "$SERVICE" != "all" && "$SERVICE" != "geonode" && "$SERVICE" != "app" && "$SERVICE" != "cdi" && "$DOWN_MODE" != "true" ]]; then
    echo "Error: service must be one of 'all', 'geonode', 'app', or 'cdi'"
    usage
fi

# Function to check if docker-compose file exists
check_compose_file() {
    local dir="$1"
    local mode="$2"
    local compose_file=""
    
    if [[ "$mode" == "dev" ]]; then
        compose_file="$dir/docker-compose.dev.yml"
    else
        compose_file="$dir/docker-compose.yml"
    fi
    
    if [[ -f "$compose_file" ]]; then
        echo "$compose_file"
        return 0
    else
        return 1
    fi
}

# Function to run docker-compose for a specific service
run_service() {
    local service="$1"
    local mode="$2"
    local service_dir="$SCRIPT_DIR/$service"
    
    echo "========================================"
    echo "Starting $service in $mode mode..."
    echo "========================================"
    
    if [[ ! -d "$service_dir" ]]; then
        echo "Warning: Directory $service_dir does not exist, skipping..."
        return 0
    fi
    
    cd "$service_dir"
    
    local compose_file
    if compose_file=$(check_compose_file "$service_dir" "$mode"); then
        echo "Found compose file: $compose_file"
        
        if [[ "$mode" == "dev" ]]; then
            # Check if override file exists
            local override_file="$service_dir/docker-compose.dev.override.yml"
            if [[ -f "$override_file" ]]; then
                if [[ "$DRY_RUN" == "true" ]]; then
                    echo "[DRY RUN] Would execute: docker compose -f docker-compose.dev.yml -f docker-compose.dev.override.yml up -d"
                else
                    echo "Running: docker compose -f docker-compose.dev.yml -f docker-compose.dev.override.yml up -d"
                    docker compose -f docker-compose.dev.yml -f docker-compose.dev.override.yml up -d
                fi
            else
                if [[ "$DRY_RUN" == "true" ]]; then
                    echo "[DRY RUN] Would execute: docker compose -f docker-compose.dev.yml up -d"
                else
                    echo "Running: docker compose -f docker-compose.dev.yml up -d"
                    docker compose -f docker-compose.dev.yml up -d
                fi
            fi
        else
            if [[ "$DRY_RUN" == "true" ]]; then
                echo "[DRY RUN] Would execute: docker compose up -d"
            else
                echo "Running: docker compose up -d"
                docker compose up -d
            fi
        fi
        
        if [[ "$DRY_RUN" == "true" ]]; then
            echo "[DRY RUN] $service would be started successfully!"
        else
            echo "$service started successfully!"
        fi
    else
        echo "Warning: No docker-compose file found for $service in $mode mode, skipping..."
    fi
    
    cd "$SCRIPT_DIR"
    echo ""
}

# Function to run traefik
run_traefik() {
    local mode="$1"
    local traefik_dir="$SCRIPT_DIR/traefik"
    
    echo "========================================"
    echo "Starting traefik in $mode mode..."
    echo "========================================"
    
    if [[ ! -d "$traefik_dir" ]]; then
        echo "Warning: Traefik directory does not exist, skipping..."
        return 0
    fi
    
    cd "$traefik_dir"
    
    # Traefik uses the same docker-compose.yml for both dev and prod
    local compose_file="$traefik_dir/docker-compose.yml"
    
    if [[ -f "$compose_file" ]]; then
        echo "Found compose file: $compose_file"
        
        if [[ "$DRY_RUN" == "true" ]]; then
            echo "[DRY RUN] Would execute: docker compose up -d"
        else
            echo "Running: docker compose up -d"
            docker compose up -d
        fi
        
        if [[ "$DRY_RUN" == "true" ]]; then
            echo "[DRY RUN] Traefik would be started successfully!"
        else
            echo "Traefik started successfully!"
        fi
    else
        echo "Warning: No docker-compose file found for traefik, skipping..."
    fi
    
    cd "$SCRIPT_DIR"
    echo ""
}

# Function to build frontend for production
build_frontend() {
    local frontend_dir="$SCRIPT_DIR/app/frontend"

    echo "========================================"
    echo "Building NextJS frontend for production..."
    echo "========================================"

    if [[ ! -d "$frontend_dir" ]]; then
        echo "Warning: Frontend directory does not exist, skipping build..."
        return 0
    fi

    cd "$frontend_dir"

    local compose_file="$frontend_dir/docker-compose.frontend-build.yml"

    if [[ -f "$compose_file" ]]; then
        echo "Found frontend build compose file: $compose_file"

        # Load environment variables from app/.env for the build process
        local env_file="$SCRIPT_DIR/app/.env"
        local compose_args=""
        if [[ -f "$env_file" ]]; then
            echo "Using environment file: $env_file"
            compose_args="--env-file $env_file"
        fi

        if [[ "$DRY_RUN" == "true" ]]; then
            echo "[DRY RUN] Would execute: docker compose $compose_args -f docker-compose.frontend-build.yml run --rm frontend_build"
        else
            echo "Running: docker compose $compose_args -f docker-compose.frontend-build.yml run --rm frontend_build"
            docker compose $compose_args -f docker-compose.frontend-build.yml run --rm frontend_build
        fi

        if [[ "$DRY_RUN" == "true" ]]; then
            echo "[DRY RUN] Frontend build would be completed successfully!"
        else
            echo "Frontend build completed successfully!"
        fi
    else
        echo "Warning: No frontend build compose file found, skipping build..."
    fi

    cd "$SCRIPT_DIR"
    echo ""
}

# Function to check if Docker is running
check_docker() {
    if ! command -v docker &> /dev/null; then
        echo "Error: Docker is not installed or not in PATH"
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        echo "Error: Docker daemon is not running"
        exit 1
    fi
}

# Function to create network if it doesn't exist
create_network() {
    local network_name="drought-map-hub-network"
    
    if ! docker network ls | grep -q "$network_name"; then
        if [[ "$DRY_RUN" == "true" ]]; then
            echo "[DRY RUN] Would create network: $network_name"
        else
            echo "Creating Docker network: $network_name"
            docker network create "$network_name"
            echo "Network $network_name created successfully!"
        fi
    else
        echo "Network $network_name already exists."
    fi
    echo ""
}

# Function to copy geonode settings to app and cdi when running all services
copy_geonode_settings() {
    local mode="$1"
    local geonode_env="$SCRIPT_DIR/geonode/.env"
    local app_env="$SCRIPT_DIR/app/.env"
    local cdi_env="$SCRIPT_DIR/cdi/.env"

    echo "========================================"
    echo "Copying Geonode settings to app and cdi..."
    echo "========================================"

    if [[ ! -f "$geonode_env" ]]; then
        echo "Warning: $geonode_env not found, skipping settings copy..."
        return 0
    fi

    # Extract values from geonode/.env
    local siteurl=$(grep "^SITEURL=" "$geonode_env" | cut -d'=' -f2-)
    local http_host=$(grep "^HTTP_HOST=" "$geonode_env" | cut -d'=' -f2-)
    local admin_username=$(grep "^ADMIN_USERNAME=" "$geonode_env" | cut -d'=' -f2-)
    local admin_password=$(grep "^ADMIN_PASSWORD=" "$geonode_env" | cut -d'=' -f2-)

    if [[ -z "$siteurl" || -z "$admin_username" || -z "$admin_password" ]]; then
        echo "Warning: Could not extract all required values from geonode/.env, skipping settings copy..."
        return 0
    fi

    # Set GEONODE_BASE_URL based on mode
    local geonode_base_url
    local geonode_host
    if [[ "$mode" == "dev" ]]; then
        # In development mode, use container name for internal Docker networking
        geonode_base_url="http://nginx4drought_map_hub"
        geonode_host="${http_host:-localhost}"
        echo "Development mode: Using container networking"
        echo "  GEONODE_BASE_URL: $geonode_base_url"
        echo "  GEONODE_HOST: $geonode_host"
    else
        # In production mode, use the actual site URL
        geonode_base_url="$siteurl"
        geonode_host="${http_host:-$(echo "$siteurl" | sed 's|http[s]*://||')}"
        echo "Production mode: Using public URLs"
        echo "  GEONODE_BASE_URL: $geonode_base_url"
        echo "  GEONODE_HOST: $geonode_host"
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        echo "[DRY RUN] Would copy GEONODE_BASE_URL=$geonode_base_url to app/.env"
        echo "[DRY RUN] Would copy GEONODE_HOST=$geonode_host to app/.env"
        echo "[DRY RUN] Would copy ADMIN_USERNAME=$admin_username to GEONODE_ADMIN_USERNAME in app/.env"
        echo "[DRY RUN] Would copy ADMIN_PASSWORD=$admin_password to GEONODE_ADMIN_PASSWORD in app/.env"
        echo "[DRY RUN] Would copy SITEURL=$siteurl to GEONODE_URL in cdi/.env"
        echo "[DRY RUN] Would copy ADMIN_USERNAME=$admin_username to GEONODE_USERNAME in cdi/.env"
        echo "[DRY RUN] Would copy ADMIN_PASSWORD=$admin_password to GEONODE_PASSWORD in cdi/.env"
    else
        # Update app/.env
        if [[ -f "$app_env" ]]; then
            # Update or add GEONODE_BASE_URL
            if grep -q "^GEONODE_BASE_URL=" "$app_env"; then
                sed -i "s|^GEONODE_BASE_URL=.*|GEONODE_BASE_URL=$geonode_base_url|" "$app_env"
            else
                echo "GEONODE_BASE_URL=$geonode_base_url" >> "$app_env"
            fi
            
            # Update or add GEONODE_HOST
            if grep -q "^GEONODE_HOST=" "$app_env"; then
                sed -i "s|^GEONODE_HOST=.*|GEONODE_HOST=$geonode_host|" "$app_env"
            else
                echo "GEONODE_HOST=$geonode_host" >> "$app_env"
            fi
            
            # Update or add admin credentials
            if grep -q "^GEONODE_ADMIN_USERNAME=" "$app_env"; then
                sed -i "s|^GEONODE_ADMIN_USERNAME=.*|GEONODE_ADMIN_USERNAME=$admin_username|" "$app_env"
            else
                echo "GEONODE_ADMIN_USERNAME=$admin_username" >> "$app_env"
            fi
            
            if grep -q "^GEONODE_ADMIN_PASSWORD=" "$app_env"; then
                sed -i "s|^GEONODE_ADMIN_PASSWORD=.*|GEONODE_ADMIN_PASSWORD=$admin_password|" "$app_env"
            else
                echo "GEONODE_ADMIN_PASSWORD=$admin_password" >> "$app_env"
            fi
            
            echo "Updated app/.env with Geonode settings for $mode mode"
        else
            echo "Warning: $app_env not found, skipping app settings update..."
        fi

        # Update cdi/.env
        if [[ -f "$cdi_env" ]]; then
            if grep -q "^GEONODE_URL=" "$cdi_env"; then
                sed -i "s|^GEONODE_URL=.*|GEONODE_URL=$siteurl|" "$cdi_env"
            else
                echo "GEONODE_URL=$siteurl" >> "$cdi_env"
            fi
            
            if grep -q "^GEONODE_USERNAME=" "$cdi_env"; then
                sed -i "s|^GEONODE_USERNAME=.*|GEONODE_USERNAME=$admin_username|" "$cdi_env"
            else
                echo "GEONODE_USERNAME=$admin_username" >> "$cdi_env"
            fi
            
            if grep -q "^GEONODE_PASSWORD=" "$cdi_env"; then
                sed -i "s|^GEONODE_PASSWORD=.*|GEONODE_PASSWORD=$admin_password|" "$cdi_env"
            else
                echo "GEONODE_PASSWORD=$admin_password" >> "$cdi_env"
            fi
            
            echo "Updated cdi/.env with Geonode settings"
        else
            echo "Warning: $cdi_env not found, skipping cdi settings update..."
        fi
    fi

    echo ""
}

# Function to stop docker-compose for a specific service
stop_service() {
    local service="$1"
    local service_dir="$SCRIPT_DIR/$service"
    
    echo "========================================"
    echo "Stopping $service..."
    echo "========================================"
    
    if [[ ! -d "$service_dir" ]]; then
        echo "Warning: Directory $service_dir does not exist, skipping..."
        return 0
    fi
    
    cd "$service_dir"
    
    # Check for different compose file patterns
    local compose_files=()
    if [[ -f "docker-compose.dev.yml" && -f "docker-compose.dev.override.yml" ]]; then
        compose_files=("-f" "docker-compose.dev.yml" "-f" "docker-compose.dev.override.yml")
    elif [[ -f "docker-compose.dev.yml" ]]; then
        compose_files=("-f" "docker-compose.dev.yml")
    elif [[ -f "docker-compose.yml" ]]; then
        compose_files=("-f" "docker-compose.yml")
    fi
    
    if [[ ${#compose_files[@]} -gt 0 ]]; then
        if [[ "$DRY_RUN" == "true" ]]; then
            echo "[DRY RUN] Would execute: docker compose ${compose_files[*]} down"
        else
            echo "Running: docker compose ${compose_files[*]} down"
            docker compose "${compose_files[@]}" down
        fi
        
        if [[ "$DRY_RUN" == "true" ]]; then
            echo "[DRY RUN] $service would be stopped successfully!"
        else
            echo "$service stopped successfully!"
        fi
    else
        echo "Warning: No docker-compose file found for $service, skipping..."
    fi
    
    cd "$SCRIPT_DIR"
    echo ""
}

# Function to stop traefik
stop_traefik() {
    local traefik_dir="$SCRIPT_DIR/traefik"
    
    echo "========================================"
    echo "Stopping traefik..."
    echo "========================================"
    
    if [[ ! -d "$traefik_dir" ]]; then
        echo "Warning: Traefik directory does not exist, skipping..."
        return 0
    fi
    
    cd "$traefik_dir"
    
    if [[ -f "docker-compose.yml" ]]; then
        if [[ "$DRY_RUN" == "true" ]]; then
            echo "[DRY RUN] Would execute: docker compose down"
        else
            echo "Running: docker compose down"
            docker compose down
        fi
        
        if [[ "$DRY_RUN" == "true" ]]; then
            echo "[DRY RUN] Traefik would be stopped successfully!"
        else
            echo "Traefik stopped successfully!"
        fi
    else
        echo "Warning: No docker-compose file found for traefik, skipping..."
    fi
    
    cd "$SCRIPT_DIR"
    echo ""
}

# Function to stop all services
stop_all_services() {
    echo "========================================"
    echo "  Stopping All Services                "
    echo "========================================"
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "Dry Run: ENABLED (no commands will be executed)"
    fi
    echo ""
    
    # Stop services in reverse order (geonode, cdi, app, then traefik)
    for service in geonode cdi app; do
        stop_service "$service"
    done
    
    # Stop traefik if it's running (check if container exists)
    if docker ps -a --format "table {{.Names}}" | grep -q "traefik" 2>/dev/null || [[ "$DRY_RUN" == "true" ]]; then
        stop_traefik
    else
        echo "Traefik container not found, skipping..."
    fi
}

# Main execution
if [[ "$DOWN_MODE" == "true" ]]; then
    echo "========================================"
    echo "  Drought Map Hub - Service Stopper    "
    echo "========================================"
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "Dry Run: ENABLED (no commands will be executed)"
    fi
    echo ""
    
    # Check if Docker is available (skip in dry-run mode)
    if [[ "$DRY_RUN" != "true" ]]; then
        check_docker
    fi

    # Create network if it doesn't exist (in case it was removed)
    create_network
    
    stop_all_services
    
    echo "========================================"
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "  Dry Run Complete - No services stopped "
    else
        echo "  All services stopped successfully!     "
    fi
    echo "========================================"
else
    echo "========================================"
    echo "  Drought Map Hub - Service Runner     "
    echo "========================================"
    echo "Mode: $MODE"
    echo "Service: $SERVICE"
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "Dry Run: ENABLED (no commands will be executed)"
    fi
    echo ""

    # Check if Docker is available (skip in dry-run mode)
    if [[ "$DRY_RUN" != "true" ]]; then
        check_docker
    fi

    # Create network if it doesn't exist
    create_network

    # Start traefik only in production mode
    if [[ "$MODE" == "prod" ]]; then
        run_traefik "$MODE"
    fi

    # Build frontend for production mode if app service is being started
    if [[ "$MODE" == "prod" && ("$SERVICE" == "app" || "$SERVICE" == "all") ]]; then
        build_frontend
    fi

    # Run services based on the service parameter
    if [[ "$SERVICE" == "all" ]]; then
        # Copy geonode settings to app and cdi
        copy_geonode_settings "$MODE"

        # Run all services
        for service in app cdi geonode; do
            run_service "$service" "$MODE"
        done

        # Connect app network to geonode network in development mode
        if [[ "$MODE" == "dev" ]]; then
            echo "========================================"
            echo "Connecting app network to geonode network..."
            echo "========================================"
            
            if [[ "$DRY_RUN" == "true" ]]; then
                echo "[DRY RUN] Would execute: docker network connect drought_map_hub_default app-mainnetwork-1"
            else
                # Check if container exists before connecting
                if docker ps --format "table {{.Names}}" | grep -q "app-mainnetwork-1"; then
                    # Check if already connected to avoid error
                    if ! docker network inspect drought_map_hub_default --format '{{range .Containers}}{{.Name}}{{"\n"}}{{end}}' | grep -q "app-mainnetwork-1"; then
                        echo "Connecting app-mainnetwork-1 to drought_map_hub_default network..."
                        docker network connect drought_map_hub_default app-mainnetwork-1
                        echo "Network connection established successfully!"
                    else
                        echo "app-mainnetwork-1 is already connected to drought_map_hub_default network."
                    fi
                else
                    echo "Warning: app-mainnetwork-1 container not found, skipping network connection..."
                fi
            fi
            echo ""
        fi
    else
        # Run specific service
        run_service "$SERVICE" "$MODE"
    fi

    echo "========================================"
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "  Dry Run Complete - No services started "
    else
        echo "  All requested services started!      "
    fi
    echo "========================================"
    echo ""
    if [[ "$DRY_RUN" != "true" ]]; then
        echo "To check running containers:"
        echo "  docker ps"
        echo ""
        echo "To stop services:"
        echo "  $0 down"
        echo ""
        echo "To view logs:"
        echo "  docker compose logs -f (in each service directory)"
    fi
fi