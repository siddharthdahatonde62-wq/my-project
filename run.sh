#!/usr/bin/env bash
cd "$(dirname "$0")/backend"
source venv/bin/activate
echo "Open http://127.0.0.1:8000"
uvicorn app:app --port 8000
