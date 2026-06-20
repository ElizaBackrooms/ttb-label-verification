#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo
echo "TTB Label Verification - First-time setup"
echo "=========================================="
echo

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: Python 3 is not installed."
  echo "Install Python 3.11+ and run this script again."
  exit 1
fi

echo "[1/3] Creating virtual environment..."
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

echo "[2/3] Installing Python packages..."
# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

read -r -p "Install Option B packages (Azure/OpenAI)? [y/N] " option_b_choice
if [[ "${option_b_choice,,}" == "y" ]]; then
  pip install -r requirements-option-b.txt
  echo "Option B installed. Copy .env.example to .env and add keys (see README)."
fi

echo "[3/3] Checking Tesseract OCR..."
if command -v tesseract >/dev/null 2>&1; then
  tesseract --version | head -n 1
else
  echo
  echo "Tesseract is NOT installed yet."
  echo "Mac:   brew install tesseract"
  echo "Linux: sudo apt install tesseract-ocr"
  echo
fi

echo
echo "Setup complete."
echo "Next: ./run.sh"
echo
