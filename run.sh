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

    # Run services based on the service parameter
    if [[ "$SERVICE" == "all" ]]; then
        # Run all services
        for service in app cdi geonode; do
            run_service "$service" "$MODE"
        done
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