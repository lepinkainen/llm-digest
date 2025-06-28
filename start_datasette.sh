#!/bin/bash
# Datasette startup script for LLM Digest

# Default database path
DB_PATH=${1:-"llm_digest.db"}

# Check if database exists
if [ ! -f "$DB_PATH" ]; then
    echo "Database file not found: $DB_PATH"
    echo "Make sure to run the web application first to create the database."
    exit 1
fi

# Start Datasette with configuration
echo "Starting Datasette for LLM Digest..."
echo "Database: $DB_PATH"
echo "Datasette will be available at: http://localhost:8001"

datasette serve llm_digest.db \
    --metadata datasette_metadata.json \
    --host 0.0.0.0 \
    --port 8001 \
    --reload \
    --setting sql_time_limit_ms 10000 \
    --setting max_returned_rows 5000 \
    --setting facet_time_limit_ms 1000 \
    --setting allow_download on \
    --setting allow_facet on \
    --setting default_page_size 100
