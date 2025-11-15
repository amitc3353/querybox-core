#!/bin/bash

#=============================================================================
# QueryBox - Clean Restart Script
# Restarts all services: Backend (port 8000) and Frontend (port 3000)
#=============================================================================

set -e  # Exit on error

PROJECT_ROOT="/Users/amitchandel/Documents/workspace/build5M/querybox-core"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

echo "=========================================="
echo "🔄 QueryBox Service Restart"
echo "=========================================="
echo ""

#=============================================================================
# Step 1: Stop All Running Services
#=============================================================================

echo "🔴 Stopping all services..."
echo ""

# Kill backend (uvicorn)
echo "  → Stopping backend (uvicorn)..."
pkill -f "uvicorn app.main:app" 2>/dev/null || echo "    (Backend not running)"

# Kill frontend (Next.js)
echo "  → Stopping frontend (Next.js)..."
pkill -9 -f "next dev" 2>/dev/null || echo "    (Frontend not running)"
pkill -9 -f "next-server" 2>/dev/null || echo "    (Next.js server not running)"

# Kill any stuck curl processes
pkill -f "curl.*localhost:3000" 2>/dev/null || true

echo "  ✅ All services stopped"
echo ""

# Wait for ports to be released
sleep 3

#=============================================================================
# Step 2: Verify Ports are Free
#=============================================================================

echo "🔍 Checking ports..."
echo ""

PORT_8000=$(lsof -i :8000 -sTCP:LISTEN -t 2>/dev/null || echo "")
PORT_3000=$(lsof -i :3000 -sTCP:LISTEN -t 2>/dev/null || echo "")

if [ -n "$PORT_8000" ]; then
    echo "  ⚠️  Port 8000 still in use (PID: $PORT_8000), killing..."
    kill -9 $PORT_8000
    sleep 2
fi

if [ -n "$PORT_3000" ]; then
    echo "  ⚠️  Port 3000 still in use (PID: $PORT_3000), killing..."
    kill -9 $PORT_3000
    sleep 2
fi

echo "  ✅ Ports 8000 and 3000 are free"
echo ""

#=============================================================================
# Step 3: Clean Build Artifacts
#=============================================================================

echo "🧹 Cleaning build artifacts..."
echo ""

# Clean frontend Next.js cache
if [ -d "$FRONTEND_DIR/.next" ]; then
    echo "  → Removing frontend .next cache..."
    rm -rf "$FRONTEND_DIR/.next"
    echo "    ✅ Frontend cache cleared"
fi

# Clean backend __pycache__
if [ -d "$BACKEND_DIR/__pycache__" ]; then
    echo "  → Removing backend __pycache__..."
    find "$BACKEND_DIR" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    echo "    ✅ Backend cache cleared"
fi

echo ""

#=============================================================================
# Step 4: Start Backend
#=============================================================================

echo "🟢 Starting backend (port 8000)..."
echo ""

cd "$BACKEND_DIR"

# Start uvicorn in background with auto-reload
nohup uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 > /tmp/uvicorn.log 2>&1 &
BACKEND_PID=$!

echo "  Backend started (PID: $BACKEND_PID)"
echo "  Logs: tail -f /tmp/uvicorn.log"
echo ""

# Wait for backend to be ready
echo "  Waiting for backend to be ready..."
for i in {1..15}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "  ✅ Backend is healthy!"
        break
    fi
    if [ $i -eq 15 ]; then
        echo "  ⚠️  Backend health check timeout (check logs)"
    fi
    sleep 1
done
echo ""

#=============================================================================
# Step 5: Start Frontend
#=============================================================================

echo "🟢 Starting frontend (port 3000)..."
echo ""

cd "$FRONTEND_DIR"

# Start Next.js dev server in background
nohup npm run dev > /tmp/nextjs.log 2>&1 &
FRONTEND_PID=$!

echo "  Frontend started (PID: $FRONTEND_PID)"
echo "  Logs: tail -f /tmp/nextjs.log"
echo ""

# Wait for frontend to be ready
echo "  Waiting for frontend to be ready..."
for i in {1..30}; do
    if curl -s -m 2 -I http://localhost:3000 > /dev/null 2>&1; then
        echo "  ✅ Frontend is ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "  ⚠️  Frontend startup timeout (check logs: tail -f /tmp/nextjs.log)"
    fi
    sleep 1
done
echo ""

#=============================================================================
# Step 6: Verify Services
#=============================================================================

echo "=========================================="
echo "✅ Service Status"
echo "=========================================="
echo ""

# Check backend
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✅ Backend: Running on http://localhost:8000"
    echo "   Health: http://localhost:8000/health"
    echo "   API Docs: http://localhost:8000/docs"
else
    echo "❌ Backend: Not responding"
    echo "   Check logs: tail -f /tmp/uvicorn.log"
fi

echo ""

# Check frontend
if curl -s -m 2 -I http://localhost:3000 > /dev/null 2>&1; then
    echo "✅ Frontend: Running on http://localhost:3000"
    echo "   App: http://localhost:3000/documents"
else
    echo "❌ Frontend: Not responding"
    echo "   Check logs: tail -f /tmp/nextjs.log"
fi

echo ""
echo "=========================================="
echo "📝 Process Information"
echo "=========================================="
echo ""
echo "Backend PID: $BACKEND_PID (logs: /tmp/uvicorn.log)"
echo "Frontend PID: $FRONTEND_PID (logs: /tmp/nextjs.log)"
echo ""
echo "To view logs:"
echo "  Backend:  tail -f /tmp/uvicorn.log"
echo "  Frontend: tail -f /tmp/nextjs.log"
echo ""
echo "To stop services:"
echo "  pkill -f 'uvicorn app.main:app'"
echo "  pkill -f 'next dev'"
echo ""
echo "=========================================="
echo "🚀 All services restarted!"
echo "=========================================="
