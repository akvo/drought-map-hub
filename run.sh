#!/bin/bash

# Drought Map Hub Runner Script
# Usage: ./run.sh mode=<dev|prod> service=<all|geonode|app|cdi> [--dry-run]

set -e

# Default values
MODE=""
SERVICE=""
DRY_RUN=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Function to display usage
usage() {
    echo "Usage: $0 mode=<dev|prod> service=<all|geonode|app|cdi> [--dry-run]"
    echo ""
    echo "Parameters:"
    echo "  mode=dev|prod    - Development or production mode"
    echo "  service=all|geonode|app|cdi - Which service to run"
    echo "  --dry-run        - Show what would be executed without running"
    echo ""
    echo "Examples:"
    echo "  $0 mode=dev service=all"
    echo "  $0 mode=prod service=app --dry-run"
    echo "  $0 mode=dev service=cdi"
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
if [[ -z "$MODE" || -z "$SERVICE" ]]; then
    echo "Error: Both mode and service parameters are required."
    echo ""
    usage
fi

if [[ "$MODE" != "dev" && "$MODE" != "prod" ]]; then
    echo "Error: mode must be either 'dev' or 'prod'"
    usage
fi

if [[ "$SERVICE" != "all" && "$SERVICE" != "geonode" && "$SERVICE" != "app" && "$SERVICE" != "cdi" ]]; then
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
    
    local compose_file
    if compose_file=$(check_compose_file "$traefik_dir" "$mode"); then
        echo "Found compose file: $compose_file"
        
        if [[ "$mode" == "dev" ]]; then
            if [[ "$DRY_RUN" == "true" ]]; then
                echo "[DRY RUN] Would execute: docker compose -f docker-compose.dev.yml up -d"
            else
                echo "Running: docker compose -f docker-compose.dev.yml up -d"
                docker compose -f docker-compose.dev.yml up -d
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
            echo "[DRY RUN] Traefik would be started successfully!"
        else
            echo "Traefik started successfully!"
        fi
    else
        echo "Warning: No docker-compose file found for traefik in $mode mode, skipping..."
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

# Main execution
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

# Always start traefik first (if it exists)
run_traefik "$MODE"

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
    echo "  docker compose down (in each service directory)"
    echo ""
    echo "To view logs:"
    echo "  docker compose logs -f (in each service directory)"
fi