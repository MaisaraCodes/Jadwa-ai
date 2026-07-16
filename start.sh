#!/usr/bin/env bash
set -e

# Start the FastAPI backend in the background
cd backend
pip install -r requirements.txt -q
uvicorn main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# Start the Vite frontend on port 5000
cd frontend
npm install --silent
npm run dev

# If frontend exits, clean up backend
kill $BACKEND_PID 2>/dev/null || true
