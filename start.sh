#!/bin/bash
# IndiaPix Metadata Automation System — Quick Start Script
# Starts both the backend (FastAPI) and frontend (Next.js) servers.
# Usage: ./start.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
BACKEND_PORT=8000
FRONTEND_PORT=3000

echo "=============================================="
echo "  IndiaPix Metadata Automation System"
echo "  Starting servers..."
echo "=============================================="
echo ""

# ── Check FFmpeg ──────────────────────────────────────────────────────────
if ! command -v ffmpeg &> /dev/null; then
    echo "[WARNING] FFmpeg not found. Please install it:"
    echo "  macOS: brew install ffmpeg"
    echo "  Windows: https://ffmpeg.org/download.html"
    echo "  Linux: sudo apt install ffmpeg"
    echo ""
fi

# ── Check .env ────────────────────────────────────────────────────────────
if [ ! -f "$BACKEND_DIR/.env" ]; then
    echo "[SETUP] Creating .env file from .env.example..."
    cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
    echo "[INFO] Please edit backend/.env to set your ANTHROPIC_API_KEY"
    echo ""
fi

# ── Backend ────────────────────────────────────────────────────────────────
echo "[BACKEND] Setting up Python virtual environment..."
cd "$BACKEND_DIR"
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate
pip install -q -r requirements.txt

echo "[BACKEND] Starting FastAPI server on port $BACKEND_PORT..."
cd "$BACKEND_DIR"
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port $BACKEND_PORT --reload &
BACKEND_PID=$!
cd "$SCRIPT_DIR"

# ── Frontend ───────────────────────────────────────────────────────────────
echo "[FRONTEND] Installing dependencies..."
cd "$FRONTEND_DIR"
if [ ! -d "node_modules" ]; then
    npm install --silent 2>/dev/null
fi

echo "[FRONTEND] Starting Next.js dev server on port $FRONTEND_PORT..."
npx next dev --port $FRONTEND_PORT &
FRONTEND_PID=$!
cd "$SCRIPT_DIR"

echo ""
echo "=============================================="
echo "  Servers starting up..."
echo "  Backend API:  http://localhost:$BACKEND_PORT"
echo "  API Docs:     http://localhost:$BACKEND_PORT/docs"
echo "  Frontend:     http://localhost:$FRONTEND_PORT"
echo "=============================================="
echo ""
echo "Press Ctrl+C to stop both servers."

# ── Cleanup on exit ──────────────────────────────────────────────────────
cleanup() {
    echo ""
    echo "Shutting down..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    wait $BACKEND_PID 2>/dev/null
    wait $FRONTEND_PID 2>/dev/null
    echo "Done."
}
trap cleanup EXIT INT TERM

# Wait for either process
wait