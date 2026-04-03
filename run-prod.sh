#!/bin/bash
# Start Trading Engine in PRODUCTION mode
# Works from phone/other devices on same WiFi
# (Dev mode WebSocket doesn't work over network)

# Kill any existing processes
lsof -ti:8000 2>/dev/null | xargs kill -9 2>/dev/null
lsof -ti:3000 2>/dev/null | xargs kill -9 2>/dev/null
sleep 1

LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "localhost")

echo "Building frontend for production..."
cd frontend && npm run build 2>&1 | tail -5
cd ..

echo ""
echo "Starting Trading Engine (Production Mode)..."
echo "============================================="

# Start backend
python3 -m uvicorn backend.app:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Start frontend in production mode
cd frontend && npm run start -- --hostname 0.0.0.0 --port 3000 &
FRONTEND_PID=$!

sleep 3
echo ""
echo "============================================="
echo "  Trading Engine Running (Production)"
echo "============================================="
echo ""
echo "  On this Mac:"
echo "    http://localhost:3000"
echo ""
echo "  From phone/other devices:"
echo "    http://$LOCAL_IP:3000"
echo ""
echo "  API docs:"
echo "    http://$LOCAL_IP:8000/docs"
echo ""
echo "  Press Ctrl+C to stop"
echo "============================================="

trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
