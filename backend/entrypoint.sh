#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Wait for database to be ready
wait_for_db() {
    log_info "Waiting for database..."

    # Extract host and port from DATABASE_URL
    # Format: postgresql+asyncpg://user:pass@host:port/db
    DB_HOST=$(echo "$DATABASE_URL" | sed -n 's/.*@\([^:]*\):.*/\1/p')
    DB_PORT=$(echo "$DATABASE_URL" | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')

    # Default values if extraction fails
    DB_HOST=${DB_HOST:-db}
    DB_PORT=${DB_PORT:-5432}

    local retries=30
    local count=0

    while ! nc -z "$DB_HOST" "$DB_PORT" 2>/dev/null; do
        count=$((count + 1))
        if [ $count -ge $retries ]; then
            log_error "Database not available after $retries attempts"
            exit 1
        fi
        log_info "Waiting for $DB_HOST:$DB_PORT... ($count/$retries)"
        sleep 1
    done

    log_info "Database is ready at $DB_HOST:$DB_PORT"
}

# Run database migrations
run_migrations() {
    log_info "Running database migrations..."
    if python -m alembic upgrade head; then
        log_info "Migrations completed successfully"
    else
        log_error "Migration failed"
        exit 1
    fi
}

# Start application based on mode
start_app() {
    local mode="${1:-all}"

    case "$mode" in
        bot)
            log_info "Starting Telegram bot (polling mode)..."
            exec python -m src.main
            ;;
        api)
            log_info "Starting FastAPI server..."
            exec python -m uvicorn src.api:create_api --factory --host 0.0.0.0 --port 8000
            ;;
        worker)
            log_info "Starting background worker..."
            exec python -m src.tasks
            ;;
        all)
            log_info "Starting bot + API (combined mode)..."
            # Start API in background
            python -m uvicorn src.api:create_api --factory --host 0.0.0.0 --port 8000 &
            API_PID=$!

            # Give API time to start
            sleep 2

            # Start bot in foreground
            python -m src.main &
            BOT_PID=$!

            # Wait for either process to exit
            wait -n $API_PID $BOT_PID

            # If one exits, kill the other
            kill $API_PID $BOT_PID 2>/dev/null || true
            ;;
        migrate)
            log_info "Running migrations only..."
            run_migrations
            exit 0
            ;;
        shell)
            log_info "Starting shell..."
            exec /bin/bash
            ;;
        *)
            log_error "Unknown mode: $mode"
            echo "Available modes: bot, api, worker, all, migrate, shell"
            exit 1
            ;;
    esac
}

# Main entrypoint
main() {
    log_info "=== HHHelper Starting ==="
    log_info "Mode: ${1:-all}"

    # Skip wait and migrations for shell mode
    if [ "$1" != "shell" ]; then
        wait_for_db
        run_migrations
    fi

    start_app "$1"
}

# Handle signals for graceful shutdown
trap 'log_info "Shutting down..."; exit 0' SIGTERM SIGINT

main "$@"
