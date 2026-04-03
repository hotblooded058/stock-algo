#!/bin/bash
# Start both backend and frontend for development
# Accessible from any device on same WiFi

# Kill any existing processes on our ports
lsof -ti:8000 2>/dev/null | xargs kill -9 2>/dev/null
lsof -ti:3000 2>/dev/null | xargs kill -9 2>/dev/null
sleep 1

LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "localhost")

echo "Starting Trading Engine..."
echo "========================="
echo ""

# Start FastAPI backend (bind to 0.0.0.0 = all interfaces)
python3 -m uvicorn backend.app:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Start Next.js frontend (bind to 0.0.0.0)
cd frontend && npm run dev -- --hostname 0.0.0.0 &
FRONTEND_PID=$!

echo ""
echo "=========================================="
echo "  Trading Engine Running!"
echo "=========================================="
echo ""
echo "  On this Mac:"
echo "    Frontend:  http://localhost:3000"
echo "    API docs:  http://localhost:8000/docs"
echo ""
echo "  From phone/other devices (same WiFi):"
echo "    Frontend:  http://$LOCAL_IP:3000"
echo "    API docs:  http://$LOCAL_IP:8000/docs"
echo ""
echo "  Press Ctrl+C to stop"
echo "=========================================="
echo ""

# Wait and cleanup
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
