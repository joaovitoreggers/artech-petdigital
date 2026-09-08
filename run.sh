#!/usr/bin/env bash
# Starts PET Digital locally: brings up PostgreSQL (Homebrew, port 5433),
# applies pending migrations, and runs the Django dev server.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

if [ ! -d venv ]; then
  echo "Creating virtualenv..."
  python3 -m venv venv
fi

source venv/bin/activate
pip install -q -r requirements.txt

if [ ! -f .env ]; then
  echo ".env not found — copy .env.example to .env and fill in real values first." >&2
  exit 1
fi

if ! brew services list | grep -q "postgresql@16.*started"; then
  echo "Starting PostgreSQL (postgresql@16)..."
  brew services start postgresql@16
  sleep 2
fi

python manage.py migrate

HOST="${1:-127.0.0.1:8000}"
echo "Starting PET Digital at http://${HOST}/"
python manage.py runserver "$HOST"
