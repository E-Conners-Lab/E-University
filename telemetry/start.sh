#!/bin/bash
#
# E-University Network Telemetry Stack Launcher
#
# Usage: ./start.sh [--build] [--stop] [--logs]
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Load environment variables from parent .env file
if [ -f "../.env" ]; then
    echo -e "${GREEN}Loading credentials from ../.env${NC}"
    export $(grep -v '^#' ../.env | xargs)
else
    echo -e "${RED}Warning: ../.env not found. Set DEVICE_USERNAME, DEVICE_PASSWORD, DEVICE_ENABLE_PASSWORD manually.${NC}"
fi

case "${1:-}" in
    --stop)
        echo -e "${YELLOW}Stopping telemetry stack...${NC}"
        docker compose down
        echo -e "${GREEN}Stopped.${NC}"
        ;;
    --logs)
        docker compose logs -f "${2:-}"
        ;;
    --build)
        echo -e "${YELLOW}Building and starting telemetry stack...${NC}"
        docker compose up -d --build
        echo ""
        echo -e "${GREEN}Telemetry stack is starting!${NC}"
        echo ""
        echo "Services:"
        echo "  - Grafana:  http://localhost:3001  (admin / euniv-grafana)"
        echo "  - InfluxDB: http://localhost:8086  (admin / euniv-telemetry-2024)"
        echo ""
        echo "Run './start.sh --logs collector' to watch collector output"
        ;;
    *)
        echo -e "${YELLOW}Starting telemetry stack...${NC}"
        docker compose up -d
        echo ""
        echo -e "${GREEN}Telemetry stack is starting!${NC}"
        echo ""
        echo "Services:"
        echo "  - Grafana:  http://localhost:3001  (admin / euniv-grafana)"
        echo "  - InfluxDB: http://localhost:8086  (admin / euniv-telemetry-2024)"
        echo ""
        echo "First time? Run './start.sh --build' to build the collector image."
        echo "Run './start.sh --logs collector' to watch collector output"
        ;;
esac
