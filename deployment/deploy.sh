#!/bin/bash
# ============================================================
# Trading Engine — Docker Deployment Script
# ============================================================
# Usage:
#   ./deployment/deploy.sh local     # Local development
#   ./deployment/deploy.sh prod      # Production deployment
#   ./deployment/deploy.sh stop      # Stop all containers
#   ./deployment/deploy.sh logs      # View logs
#   ./deployment/deploy.sh rebuild   # Rebuild and restart
# ============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

case "${1:-local}" in

  local)
    echo "Starting Trading Engine (local development)..."
    echo "================================================"
    docker compose -f deployment/docker-compose.yml up --build -d
    echo ""
    echo "Backend API:  http://localhost:8000/docs"
    echo "Frontend UI:  http://localhost:3000"
    echo ""
    echo "View logs: ./deployment/deploy.sh logs"
    echo "Stop:      ./deployment/deploy.sh stop"
    ;;

  prod)
    echo "Starting Trading Engine (production)..."
    echo "================================================"

    # Check secrets exist
    if [ ! -f config/secrets.py ]; then
      echo "ERROR: config/secrets.py not found!"
      echo "Create it with your AngelOne credentials."
      exit 1
    fi

    docker compose -f deployment/docker-compose.prod.yml up --build -d
    echo ""
    echo "Production started!"
    echo "Backend:  http://$(hostname -I | awk '{print $1}'):8000"
    echo "Frontend: http://$(hostname -I | awk '{print $1}'):3000"
    ;;

  stop)
    echo "Stopping Trading Engine..."
    docker compose -f deployment/docker-compose.yml down 2>/dev/null || true
    docker compose -f deployment/docker-compose.prod.yml down 2>/dev/null || true
    echo "Stopped."
    ;;

  logs)
    docker compose -f deployment/docker-compose.yml logs -f --tail=50
    ;;

  rebuild)
    echo "Rebuilding and restarting..."
    docker compose -f deployment/docker-compose.yml down 2>/dev/null || true
    docker compose -f deployment/docker-compose.yml up --build -d
    echo "Rebuilt and started."
    ;;

  status)
    echo "Container Status:"
    docker compose -f deployment/docker-compose.yml ps 2>/dev/null || \
    docker compose -f deployment/docker-compose.prod.yml ps 2>/dev/null
    ;;

  *)
    echo "Usage: $0 {local|prod|stop|logs|rebuild|status}"
    exit 1
    ;;

esac
