#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/backend"
command -v ollama >/dev/null || { echo "Install Ollama from https://ollama.com/download first"; exit 1; }
PY=$(command -v python3.12 || command -v python3.11 || command -v python3)
[ -d venv ] || "$PY" -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
ollama pull qwen2.5:3b
ollama pull nomic-embed-text
echo "Setup complete. Run ./run.sh"
