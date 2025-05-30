#!/bin/bash

# Start local backend with Supabase integration (for logging only)
# Force SQLite for main database, Supabase only for analytics/logging

echo "🚀 Starting local backend with Supabase integration..."

# Check if SUPABASE_SERVICE_KEY is set
if [ -z "$SUPABASE_SERVICE_KEY" ]; then
    echo "❌ SUPABASE_SERVICE_KEY not set!"
    echo "Please run: export SUPABASE_SERVICE_KEY='your_service_key_here'"
    echo "Get it from Supabase Dashboard > Settings > API > service_role key"
    exit 1
fi

# Set environment variables
export SUPABASE_URL="https://mobzemfxlxydpocscpwz.supabase.co"
export GOOGLE_API_KEY="your_google_key_if_needed"

# Force SQLite for main database (override any PostgreSQL settings)
export DATABASE_URL="sqlite:///./timesheet_magic_local.db"

# Clear any PostgreSQL-related environment variables that might interfere
unset SUPABASE_DB_URL
unset DB_HOST
unset DB_PORT
unset DB_NAME
unset DB_USER
unset DB_PASSWORD

echo "✅ Environment variables set"
echo "DATABASE_URL: $DATABASE_URL (SQLite for local testing)"
echo "SUPABASE_URL: $SUPABASE_URL (for logging only)"
echo "SUPABASE_SERVICE_KEY: SET (${SUPABASE_SERVICE_KEY:0:20}...)"

# Start the server
cd backend
echo "🔄 Starting uvicorn server on port 8001..."
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload 