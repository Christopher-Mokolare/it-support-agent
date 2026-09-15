#!/usr/bin/env bash
# One-shot setup for the IT support agent.
# Run: bash bootstrap.sh

set -euo pipefail

echo "==> Checking Homebrew..."
if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew not found. Install from https://brew.sh first."
  exit 1
fi

echo "==> Installing Ollama..."
brew list ollama >/dev/null 2>&1 || brew install ollama

echo "==> Starting Ollama service..."
brew services start ollama || true
sleep 3

echo "==> Pulling model (this may take a few minutes)..."
ollama pull "${OLLAMA_MODEL:-qwen2.5-coder:7b}"

echo "==> Setting up Python venv..."
if [ ! -d venv ]; then
  python3 -m venv venv
fi
# shellcheck disable=SC1091
source venv/bin/activate

echo "==> Installing Python deps..."
pip install --upgrade pip
pip install -r requirements.txt
pip install openai boto3 python-dotenv

echo "==> Checking .env..."
if [ ! -f .env ]; then
  cp .env.example .env
  echo "  Created .env from .env.example. Edit it and add any keys you need."
fi

echo "==> Ensuring runbooks directory exists..."
mkdir -p runbooks

echo ""
echo "Done. Activate the venv and run:"
echo "  source venv/bin/activate"
echo "  python agent.py \"scan DFY-FE and tell me what's broken\""
