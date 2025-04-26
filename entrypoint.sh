#!/bin/bash

set -e

DB_PATH="instance/calendar.db"   # <<== YOUR actual database file here
BACKUP_PATH="instance/calendar_$(date +%F_%H-%M-%S).db"

if [ -f "$DB_PATH" ]; then
    echo "🗄️  Backing up database..."
    cp "$DB_PATH" "$BACKUP_PATH"
else
    echo "⚠️  No database found to backup. Skipping backup."
fi

echo "🔧 Running Alembic migrations..."
alembic upgrade head

echo "🚀 Starting app..."
exec python app.py
