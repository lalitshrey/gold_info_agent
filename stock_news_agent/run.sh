#!/bin/bash

# Stock News Agent Runner Script
# This script activates the virtual environment and runs the application

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Creating one..."
    python3 -m venv .venv
    echo "📦 Installing dependencies..."
    source .venv/bin/activate
    pip install -r requirements.txt
    echo "✅ Virtual environment created and dependencies installed"
fi

# Activate virtual environment
source .venv/bin/activate

# Check if MySQL is running
if ! pgrep -x "mysqld" > /dev/null; then
    echo "⚠️  Warning: MySQL doesn't appear to be running"
    echo "   Please start MySQL before running the application"
    echo "   On Ubuntu: sudo systemctl start mysql"
    echo "   On macOS: brew services start mysql"
fi

# Run the application with provided arguments
echo "🚀 Starting Stock News Agent..."
python3 app.py "$@"

