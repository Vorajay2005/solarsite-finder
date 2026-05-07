#!/usr/bin/env bash
set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV="$PROJECT_ROOT/.venv"
SCRIPTS="$PROJECT_ROOT/scripts"
FRONTEND="$PROJECT_ROOT/frontend"
DB="$PROJECT_ROOT/database/solar_site_finder.db"

# ── 1. Create Python virtual environment if missing ───────────────────────────
if [ ! -f "$VENV/bin/python" ]; then
  echo "==> Creating Python virtual environment..."
  python3 -m venv "$VENV"
fi
PYTHON="$VENV/bin/python"
PIP="$VENV/bin/pip"

# ── 2. Install Python dependencies ───────────────────────────────────────────
echo "==> Installing Python dependencies..."
"$PIP" install --quiet -r "$PROJECT_ROOT/backend/requirements.txt"

# ── 3. Install frontend dependencies ─────────────────────────────────────────
echo "==> Installing frontend dependencies..."
cd "$FRONTEND"
npm install --silent
cd "$PROJECT_ROOT"

# ── 4. Run pipeline scripts (skip if DB already fully populated) ──────────────
SCORED=$("$PYTHON" -c "
import sqlite3, os
if not os.path.exists('$DB'): print(0)
else:
    try: print(sqlite3.connect('$DB').execute('SELECT COUNT(*) FROM site_scores').fetchone()[0])
    except: print(0)
" 2>/dev/null || echo 0)

if [ "$SCORED" -gt 0 ]; then
  echo "==> Database already populated ($SCORED scored sites). Skipping pipeline."
  echo "    To re-run, delete database/solar_site_finder.db and run this script again."
else
  echo "==> Running data pipeline (this may take a few minutes)..."
  "$PYTHON" "$SCRIPTS/create_database.py"
  "$PYTHON" "$SCRIPTS/load_datasets.py"
  "$PYTHON" "$SCRIPTS/generate_candidate_sites.py"
  echo "==> Training ML capacity prediction model..."
  "$PYTHON" "$SCRIPTS/train_model.py"
  "$PYTHON" "$SCRIPTS/score_sites.py"
  "$PYTHON" "$SCRIPTS/export_cleaned_data.py"
  "$PYTHON" "$SCRIPTS/export_results.py"
  echo "==> Pipeline complete."
fi

# ── 5. Start Flask backend ────────────────────────────────────────────────────
echo "==> Starting Flask backend  →  http://127.0.0.1:5001"
"$PYTHON" "$PROJECT_ROOT/backend/app.py" &
BACKEND_PID=$!
sleep 2

# ── 6. Start Vite frontend ────────────────────────────────────────────────────
echo "==> Starting frontend        →  http://localhost:5173"
cd "$FRONTEND"
npm run dev &
FRONTEND_PID=$!

echo ""
echo "    Backend:  http://127.0.0.1:5001"
echo "    Frontend: http://localhost:5173"
echo "    Press Ctrl+C to stop."

# ── Cleanup on exit ───────────────────────────────────────────────────────────
cleanup() {
  echo ""
  echo "==> Shutting down..."
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
  wait "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null
  exit 0
}
trap cleanup INT TERM

wait
