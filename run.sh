#!/bin/bash
# Start both backend and frontend for development

echo "Starting Trading Engine..."
echo "========================="

# Start FastAPI backend on port 8000
echo "Starting backend (FastAPI) on http://localhost:8000"
python3 -m uvicorn backend.app:app --reload --port 8000 &
BACKEND_PID=$!

# Start Next.js frontend on port 3000
echo "Starting frontend (Next.js) on http://localhost:3000"
cd frontend && npm run dev &
FRONTEND_PID=$!

echo ""
echo "Backend API:  http://localhost:8000/docs"
echo "Frontend UI:  http://localhost:3000"
echo ""
echo "Press Ctrl+C to stop both servers"

# Wait and cleanup
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT TERM
wait
