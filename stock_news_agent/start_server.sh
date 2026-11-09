#!/bin/bash

# Stock News Agent Server Startup Script
# This script starts the FastAPI server with the virtual environment

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
    echo ""
    echo "   Continuing anyway... (database operations will fail)"
fi

# Set default values
HOST=${HOST:-"0.0.0.0"}
PORT=${PORT:-"8000"}
WORKERS=${WORKERS:-"1"}

echo "🚀 Starting Stock News Agent Server..."
echo "   Host: $HOST"
echo "   Port: $PORT"
echo "   Workers: $WORKERS"
echo ""
echo "📋 Available endpoints:"
echo "   Web UI: http://$HOST:$PORT"
echo "   API Docs: http://$HOST:$PORT/docs"
echo "   Stocks: http://$HOST:$PORT/stocks"
echo "   News: http://$HOST:$PORT/news?tickers=RELIANCE,TCS"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start the server
uvicorn app:api --host "$HOST" --port "$PORT" --workers "$WORKERS"

