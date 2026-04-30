#!/bin/bash
# My Pay — local dev startup script
# Run from the myapp-main/ folder: bash start.sh

ROOT="$(cd "$(dirname "$0")" && pwd)"

echo ""
echo "╔══════════════════════════════════╗"
echo "║       My Pay — Dev Server        ║"
echo "╚══════════════════════════════════╝"
echo ""

# ── 0. Kill anything already on ports 8000 / 3000 ───────────────────
echo "▶ Clearing ports..."
lsof -ti :8000 | xargs kill -9 2>/dev/null && echo "  ✓ Cleared port 8000" || echo "  ✓ Port 8000 free"
lsof -ti :3000 | xargs kill -9 2>/dev/null && echo "  ✓ Cleared port 3000" || echo "  ✓ Port 3000 free"
sleep 1

# ── 1. Check MongoDB ─────────────────────────────────────────────────
echo ""
echo "▶ Checking MongoDB..."
if ! mongod --version &>/dev/null && ! brew services list 2>/dev/null | grep -q "mongodb"; then
  echo ""
  echo "  MongoDB is not installed or not in PATH."
  echo "  Install options:"
  echo "    macOS (Homebrew):  brew tap mongodb/brew && brew install mongodb-community && brew services start mongodb-community"
  echo "    Docker one-liner:  docker run -d -p 27017:27017 --name mypay-mongo mongo:7"
  echo ""
  echo "  Once MongoDB is running, re-run this script."
  exit 1
fi
echo "  ✓ MongoDB found"

# ── 2. Backend ───────────────────────────────────────────────────────
echo ""
echo "▶ Starting backend (port 8000)..."
cd "$ROOT/backend"

# Install uv if not present (one-time, takes seconds)
if ! command -v uv &>/dev/null; then
  echo "  Installing uv (first time only)..."
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
fi

# uv sync: installs exact versions from uv.lock, creates .venv automatically
# Only re-runs if uv.lock changed — otherwise instant
echo "  Syncing Python dependencies..."
uv sync --frozen --no-install-project -q
source .venv/bin/activate
echo "  ✓ Python dependencies ready"

echo "  ✓ Backend starting in background..."
uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!

# Wait for backend to be ready
echo "  Waiting for backend..."
for i in {1..10}; do
  sleep 1
  if curl -s http://localhost:8000/ &>/dev/null; then
    echo "  ✓ Backend live at http://localhost:8000"
    break
  fi
  if [ $i -eq 10 ]; then
    echo "  ⚠ Backend slow to start — continuing anyway"
  fi
done

# ── 3. Seed demo brands (idempotent) ────────────────────────────────
echo ""
echo "▶ Seeding demo brands..."
SEED=$(curl -s -X POST http://localhost:8000/api/brands/seed 2>/dev/null)
if echo "$SEED" | grep -q "seeded"; then
  echo "  ✓ Demo brands ready (Gymshark, Nykaa, boAt, Mamaearth, Sugar Cosmetics)"
else
  echo "  ℹ Brands may already exist or backend still starting"
fi

# ── 4. Frontend ──────────────────────────────────────────────────────
echo ""
echo "▶ Starting frontend (port 3000)..."
cd "$ROOT/frontend"

# Install if: node_modules missing, package.json changed, OR vite binary broken
PKG_HASH_FILE="node_modules/.pkg_hash"
CURRENT_PKG_HASH=$(md5 -q package.json 2>/dev/null || md5sum package.json 2>/dev/null | cut -d' ' -f1)
STORED_PKG_HASH=$(cat "$PKG_HASH_FILE" 2>/dev/null || echo "")
VITE_OK=false
[ -f "node_modules/.bin/vite" ] && node_modules/.bin/vite --version &>/dev/null && VITE_OK=true

if [ ! -d "node_modules" ] || [ "$CURRENT_PKG_HASH" != "$STORED_PKG_HASH" ] || [ "$VITE_OK" = "false" ]; then
  echo "  Installing frontend dependencies (clean install)..."
  rm -rf node_modules package-lock.json 2>/dev/null
  npm install
  echo "$CURRENT_PKG_HASH" > "$PKG_HASH_FILE"
  echo "  ✓ Frontend dependencies ready"
else
  echo "  ✓ Frontend dependencies already installed (skipping)"
fi

echo ""
echo "═══════════════════════════════════"
echo "  Backend:   http://localhost:8000"
echo "  Frontend:  http://localhost:3000"
echo "  API docs:  http://localhost:8000/docs"
echo "═══════════════════════════════════"
echo ""
echo "  Press Ctrl+C to stop both servers"
echo ""

trap "echo ''; echo 'Stopping servers...'; kill $BACKEND_PID 2>/dev/null; exit 0" INT TERM

npm start
