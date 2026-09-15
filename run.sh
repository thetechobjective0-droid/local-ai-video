#!/usr/bin/env bash

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$PROJECT_DIR"

echo "========================================"
echo " Local AI Video"
echo "========================================"
echo

echo "→ Checking required tools..."

command -v uv >/dev/null 2>&1 || { echo "ERROR: uv is not installed."; exit 1; }
command -v ollama >/dev/null 2>&1 || { echo "ERROR: Ollama is not installed."; exit 1; }
command -v ffmpeg >/dev/null 2>&1 || { echo "ERROR: ffmpeg is not installed."; exit 1; }
command -v ffprobe >/dev/null 2>&1 || { echo "ERROR: ffprobe is not installed."; exit 1; }
command -v say >/dev/null 2>&1 || { echo "ERROR: macOS 'say' command is not available."; exit 1; }
command -v git >/dev/null 2>&1 || { echo "ERROR: git is not installed."; exit 1; }
command -v curl >/dev/null 2>&1 || { echo "ERROR: curl is not installed."; exit 1; }

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "ERROR: Local AI Video currently requires macOS / Apple Silicon for the production MLX video path."
    exit 1
fi

ARCH="$(uname -m)"
if [[ "$ARCH" != "arm64" ]]; then
    echo "ERROR: The production MLX video path requires Apple Silicon (arm64)."
    exit 1
fi

echo "✓ uv      : $(uv --version)"
echo "✓ ollama  : $(ollama --version | head -n 1)"
echo "✓ ffmpeg  : available"
echo "✓ ffprobe : available"
echo "✓ say     : available"
echo "✓ git     : $(git --version)"
echo "✓ curl    : available"
echo "✓ platform: macOS arm64"

echo
echo "→ Syncing application dependencies..."
uv sync --extra dev --extra image

LTX_RUNTIME_DIR="${LTX_RUNTIME_DIR:-$PROJECT_DIR/data/runtime/ltx-2-mlx}"
LTX_RUNTIME_REPO="${LTX_RUNTIME_REPO:-https://github.com/dgrauet/ltx-2-mlx.git}"
LTX_MODEL_DIR="${LTX_MODEL_DIR:-$PROJECT_DIR/data/models/ltx-2.3-mlx-q8}"
LTX_MODEL_REPO="${LTX_MODEL_REPO:-dgrauet/ltx-2.3-mlx-q8}"
LTX_AUTO_DOWNLOAD_MODEL="${LTX_AUTO_DOWNLOAD_MODEL:-ask}"

mkdir -p "$(dirname "$LTX_RUNTIME_DIR")" "$(dirname "$LTX_MODEL_DIR")"

echo
echo "→ Preparing local LTX-2.3 MLX runtime..."
if [[ ! -d "$LTX_RUNTIME_DIR/.git" ]]; then
    if [[ -d "$LTX_RUNTIME_DIR" ]] && [[ -n "$(find "$LTX_RUNTIME_DIR" -mindepth 1 -maxdepth 1 -print -quit 2>/dev/null)" ]]; then
        echo "ERROR: LTX runtime directory exists but is not a Git checkout: $LTX_RUNTIME_DIR"
        echo "Remove it or set LTX_RUNTIME_DIR to a valid checkout."
        exit 1
    fi
    echo "→ Cloning $LTX_RUNTIME_REPO"
    git clone "$LTX_RUNTIME_REPO" "$LTX_RUNTIME_DIR"
fi

if [[ ! -f "$LTX_RUNTIME_DIR/pyproject.toml" ]]; then
    echo "ERROR: LTX-2.3 MLX runtime is missing pyproject.toml: $LTX_RUNTIME_DIR"
    exit 1
fi

echo "→ Syncing LTX-2.3 MLX runtime dependencies..."
uv --directory "$LTX_RUNTIME_DIR" sync --all-extras
if ! uv --directory "$LTX_RUNTIME_DIR" run --offline ltx-2-mlx --help >/dev/null 2>&1; then
    echo "ERROR: LTX-2.3 MLX runtime does not expose the expected local generation entry point."
    echo "Runtime: $LTX_RUNTIME_DIR"
    exit 1
fi

echo "✓ LTX runtime: $LTX_RUNTIME_DIR"

if [[ ! -e "$LTX_MODEL_DIR" ]]; then
    echo
echo "LTX-2.3 q8 model pack is missing."
    echo "Expected: $LTX_MODEL_DIR"
    echo "Model:    $LTX_MODEL_REPO"
    echo "The q8 pack is a large local download; Hugging Face currently lists it at roughly 72 GB."
    echo

    case "$LTX_AUTO_DOWNLOAD_MODEL" in
        yes|true|1)
            download_model=yes
            ;;
        no|false|0)
            download_model=no
            ;;
        ask)
            read -r -p "Download the LTX-2.3 q8 model pack now? [y/N] " answer
            case "${answer:-N}" in
                y|Y|yes|YES)
                    download_model=yes
                    ;;
                *)
                    download_model=no
                    ;;
            esac
            ;;
        *)
            echo "ERROR: LTX_AUTO_DOWNLOAD_MODEL must be ask, yes, or no."
            exit 1
            ;;
    esac

    if [[ "$download_model" != "yes" ]]; then
        echo "Model download skipped."
        echo "Prepare the model locally and rerun ./run.sh."
        exit 1
    fi

    echo "→ Preparing Hugging Face download tooling..."
    uv tool run --from "huggingface_hub[hf_xet]" huggingface-cli download \
        "$LTX_MODEL_REPO" \
        --local-dir "$LTX_MODEL_DIR"
fi

if [[ ! -d "$LTX_MODEL_DIR" ]]; then
    echo "ERROR: LTX model download did not produce a directory: $LTX_MODEL_DIR"
    exit 1
fi

echo "✓ LTX model : $LTX_MODEL_DIR"

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
echo "Open: http://127.0.0.1:8765"
echo "Press Ctrl+C to stop."
echo
echo "Real temporal AI video: LTX-2.3 MLX"
echo "Deterministic FFmpeg motion: explicit fallback only"
echo

export LTX_RUNTIME_DIR
export LTX_MODEL_DIR

exec uv run video-agent-web
