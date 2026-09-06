#!/bin/zsh
# Starts the TEAF Reference App against the local TEAF framework checkout.
# This script installs packages only into this repository's .venv directory.

set -euo pipefail

APP_DIR="${0:A:h}"
TEAF_DIR="/Users/jesuscampa/Documents/GitHub/torus-enterprise-framework"

cd "$APP_DIR"

if [[ ! -d "$TEAF_DIR" ]]; then
  print -u2 "TEAF framework not found at: $TEAF_DIR"
  print -u2 "Update TEAF_DIR in this script if the framework was moved."
  exit 1
fi

rm -rf .venv
if [[ ! -d ".venv" ]]; then
  print "Creating .venv..."
  python3 -m venv .venv
fi

source .venv/bin/activate

print "Installing the local TEAF framework..."
python -m pip install -e "$TEAF_DIR"

print "Installing Reference App development dependencies..."
python -m pip install -e ".[dev]"

print "Checking TEAF public API..."
python -c 'import teaf; from teaf import Application; print("TEAF:", getattr(teaf, "__version__", "0.10.3-alpha")); print("Application:", Application)'

print ""
print "Starting TEAF Reference App at http://localhost:8000/"
print "Stop it with Control+C."
exec python -m uvicorn app.main:app --reload
