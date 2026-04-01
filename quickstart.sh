#!/bin/bash

# Quick-start script for RADIUS Server on Astra Linux
# Usage: ./quickstart.sh [setup|run|test|clean]

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$PROJECT_DIR/venv"
CONFIG_DIR="/etc/radius-server"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[*]${NC} $1"
}

print_error() {
    echo -e "${RED}[!]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Check if Python 3 is installed
check_python() {
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is not installed. Please install it first:"
        echo "  sudo apt install -y python3 python3-pip python3-venv"
        exit 1
    fi
    print_status "Python 3 found: $(python3 --version)"
}

# Setup virtual environment and install dependencies
setup() {
    print_status "Setting up RADIUS Server..."
    
    check_python
    
    # Create virtual environment
    if [ ! -d "$VENV_DIR" ]; then
        print_status "Creating virtual environment..."
        python3 -m venv "$VENV_DIR"
    else
        print_status "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    source "$VENV_DIR/bin/activate"
    
    # Upgrade pip
    print_status "Upgrading pip..."
    pip install --upgrade pip
    
    # Install dependencies
    print_status "Installing dependencies..."
    pip install -r "$PROJECT_DIR/requirements.txt"
    
    # Create config directory
    print_status "Creating configuration directory..."
    sudo mkdir -p "$CONFIG_DIR"
    sudo chown $USER:$USER "$CONFIG_DIR"
    
    print_status "Setup complete!"
    echo ""
    echo "To activate the virtual environment, run:"
    echo "  source $VENV_DIR/bin/activate"
    echo ""
    echo "To start the server, run:"
    echo "  ./quickstart.sh run"
}

# Run the server
run() {
    print_status "Starting RADIUS Server..."
    
    if [ ! -d "$VENV_DIR" ]; then
        print_error "Virtual environment not found. Run './quickstart.sh setup' first"
        exit 1
    fi
    
    source "$VENV_DIR/bin/activate"
    
    print_status "RADIUS Server starting on UDP 1812 and HTTP 5000"
    print_warning "Note: UDP 1812 requires elevated privileges. Running with sudo..."
    echo ""
    
    cd "$PROJECT_DIR"
    sudo -E "$VENV_DIR/bin/python3" -m src.main
}

# Run tests
test() {
    print_status "Running tests..."
    
    if [ ! -d "$VENV_DIR" ]; then
        print_error "Virtual environment not found. Run './quickstart.sh setup' first"
        exit 1
    fi
    
    source "$VENV_DIR/bin/activate"
    
    cd "$PROJECT_DIR"
    pytest tests/ -v --tb=short
}

# Clean up
clean() {
    print_status "Cleaning up..."
    
    if [ -d "$VENV_DIR" ]; then
        print_status "Removing virtual environment..."
        rm -rf "$VENV_DIR"
    fi
    
    print_status "Removing Python cache files..."
    find "$PROJECT_DIR" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    find "$PROJECT_DIR" -type f -name "*.pyc" -delete
    
    print_status "Clean complete!"
}

# Stop the server
stop() {
    print_status "Stopping RADIUS Server..."
    
    sudo pkill -f "src.main"
    
    if [ $? -eq 0 ]; then
        print_status "Server stopped"
    else
        print_warning "Server not running or already stopped"
    fi
}

# Show help
show_help() {
    echo "RADIUS Server Quick-Start Script"
    echo ""
    echo "Usage: ./quickstart.sh [command]"
    echo ""
    echo "Commands:"
    echo "  setup    - Set up virtual environment and install dependencies"
    echo "  run      - Start the RADIUS server"
    echo "  stop     - Stop the RADIUS server"
    echo "  test     - Run the test suite"
    echo "  clean    - Remove virtual environment and cache files"
    echo "  help     - Show this help message"
    echo ""
    echo "Examples:"
    echo "  ./quickstart.sh setup"
    echo "  ./quickstart.sh run"
    echo "  ./quickstart.sh stop"
    echo "  ./quickstart.sh test"
}

# Main
case "${1:-help}" in
    setup)
        setup
        ;;
    run)
        run
        ;;
    stop)
        stop
        ;;
    test)
        test
        ;;
    clean)
        clean
        ;;
    help)
        show_help
        ;;
    *)
        print_error "Unknown command: $1"
        show_help
        exit 1
        ;;
esac
