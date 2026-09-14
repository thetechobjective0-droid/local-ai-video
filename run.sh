#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$PROJECT_DIR"

echo "========================================"
echo " Local AI Video"
echo "========================================"
echo

echo "→ Syncing dependencies..."
uv sync --extra dev --extra image

echo

echo "→ Checking required tools..."

command -v uv >/dev/null 2>&1 || { echo "ERROR: uv is not installed."; exit 1; }
command -v ollama >/dev/null 2>&1 || { echo "ERROR: Ollama is not installed."; exit 1; }
command -v ffmpeg >/dev/null 2>&1 || { echo "ERROR: ffmpeg is not installed."; exit 1; }
command -v ffprobe >/dev/null 2>&1 || { echo "ERROR: ffprobe is not installed."; exit 1; }
command -v say >/dev/null 2>&1 || { echo "ERROR: macOS 'say' command is not available."; exit 1; }

echo "✓ uv      : $(uv --version)"
echo "✓ ollama  : $(ollama --version | head -n 1)"
echo "✓ ffmpeg  : available"
echo "✓ ffprobe : available"
echo "✓ say     : available"

echo

echo "→ Checking Ollama..."
if ! curl -fsS http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
    echo "ERROR: Ollama is not running."
    echo "Start it with: ollama serve"
    exit 1
fi

echo "✓ Ollama is running."
echo

echo "→ Available Ollama models:"
ollama list

echo

echo "========================================"
echo " Starting Local AI Video Web UI"
echo "========================================"
echo
echo "Open: http://127.0.0.1:8000"
echo "Press Ctrl+C to stop."
echo

exec uv run video-agent-web
