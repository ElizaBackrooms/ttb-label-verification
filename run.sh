#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "First-time setup required. Running setup.sh..."
  bash setup.sh
fi

# shellcheck disable=SC1091
source .venv/bin/activate

echo
echo "Starting TTB Label Verification Assistant..."
echo "Open http://localhost:8501 in your browser"
echo "Press Ctrl+C to stop."
echo

python -m streamlit run app.py --server.headless false
